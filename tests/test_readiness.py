"""Operational policy regressions: all network results are invented, not live evidence."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from pilot import policy, fixtures
from pilot.maintenance import copy_database
from pilot.normalize import articles, reference
from pilot.refresh import Coordinator
from pilot.store import Store
from pilot.transport import FetchError
from tests.test_pilot import Clock


class LivePolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.clock = Clock()
        self.path = Path(self.temp.name) / 'reader.sqlite3'
        self.store = Store(self.path, mode='live', clock=self.clock)
        self.fetch = Mock(side_effect=lambda source, conditional: (200, fixtures.feed(source, self.clock()), {'etag': '"synthetic-validator"'}))
        self.coordinator = Coordinator(self.store, self.fetch)

    def test_both_markets_repeat_reload_conditional_and_expiry(self):
        self.assertEqual(self.coordinator.refresh('open')['outcome'], 'completed')
        self.assertEqual(self.fetch.call_count, 2)
        self.assertEqual(len(Store(self.path, clock=self.clock).deals()), 2)
        self.assertTrue(all(not row['provenance']['synthetic'] for row in self.store.deals()))
        expires = [row['cacheExpiresAt'] for row in self.store.deals()]
        self.assertEqual(self.coordinator.refresh('manual')['outcome'], 'skipped')
        self.assertEqual(self.fetch.call_count, 2)
        self.clock.advance(policy.TTL)
        self.fetch.side_effect = None
        self.fetch.return_value = (304, b'', {})
        self.assertEqual(self.coordinator.refresh('foreground')['outcome'], 'completed')
        self.assertEqual(self.fetch.call_count, 4)
        self.assertEqual(self.fetch.call_args.args[1], {'If-None-Match': '"synthetic-validator"'})
        self.assertEqual(expires, [row['cacheExpiresAt'] for row in self.store.deals()])
        self.clock.advance(policy.RETENTION)
        self.assertEqual(Store(self.path, clock=self.clock).deals(), [])

    def test_daily_budget_survives_history_flood_and_restart(self):
        for _ in range(policy.LIVE_DAILY_REQUESTS):
            self.coordinator.refresh('manual')
            self.clock.advance(policy.TTL)
        self.assertEqual(self.fetch.call_count, 2 * policy.LIVE_DAILY_REQUESTS)
        for _ in range(110):
            self.assertEqual(self.coordinator.refresh('manual')['outcome'], 'skipped')
        loaded = Store(self.path, clock=self.clock)
        with loaded.tx() as db:
            self.assertLessEqual(db.execute('SELECT count(*) FROM runs').fetchone()[0], 100)
            self.assertEqual(db.execute('SELECT count(*) FROM request_attempts').fetchone()[0], 16)
        fetch = Mock()
        result = Coordinator(loaded, fetch).refresh('manual')
        self.assertTrue(all(row['reason'] == 'daily-budget' for row in result['sources'].values()))
        fetch.assert_not_called()
        self.clock.advance(86400)
        self.coordinator.refresh('manual')
        self.assertEqual(self.fetch.call_count, 18)

    def test_budget_claim_is_atomic_under_concurrent_opens(self):
        with self.store.tx() as db:
            for source in policy.SOURCES:
                db.executemany('INSERT INTO request_attempts VALUES(?,?)', [(source, self.clock())] * 7)
        def claim(number):
            return self.store.claim('brickset-ca', 'open', f'synthetic-claim-{number}')
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(claim, range(8)))
        self.assertEqual(sum('token' in result for result in results), 1)
        with self.store.tx() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM request_attempts WHERE source_id='brickset-ca'").fetchone()[0], 8)

    def test_failure_backoff_retains_only_original_lifetime(self):
        self.coordinator.refresh('manual')
        old = self.store.deals()
        self.clock.advance(policy.TTL)
        self.fetch.side_effect = FetchError('http-429', self.clock() + 10000)
        self.assertEqual(self.coordinator.refresh('manual')['outcome'], 'failed')
        self.assertEqual(self.store.deals(), old)
        self.assertTrue(all(row['nextEligibleAt'] == reference.stamp(self.clock() + 10000) for row in self.store.sources()))
        self.clock.advance(policy.RETENTION)
        self.assertEqual(self.store.deals(), [])

    def test_policy_revocation_blocks_injected_transport_and_writer(self):
        with patch('pilot.policy.live_allowed', return_value=False):
            self.assertEqual(self.coordinator.refresh('manual')['outcome'], 'failed')
        self.fetch.assert_not_called()
        self.clock.advance(policy.TTL)
        claim = self.store.claim('brickset-us', 'manual', 'synthetic-revoked-claim')
        rows = articles(fixtures.feed('brickset-us', self.clock()), 'brickset-us', reference.stamp(self.clock()), synthetic=False)[0]
        with patch('pilot.policy.live_allowed', return_value=False), self.assertRaisesRegex(ValueError, 'persistent-live-denied'):
            self.store.complete('brickset-us', claim, rows)
        self.assertEqual(self.store.deals(), [])

    def test_live_backup_and_restore_refused_without_creating_destination(self):
        self.coordinator.refresh('manual')
        for restore in (False, True):
            destination = Path(self.temp.name) / f'denied-{restore}.sqlite3'
            with self.assertRaisesRegex(ValueError, 'live-reader-backup-denied'):
                copy_database(self.path, destination, restore=restore)
            self.assertFalse(destination.exists())

    def test_new_policy_fences_old_worker_and_discards_validators(self):
        claim = self.store.claim('brickset-ca', 'open', 'synthetic-old-config')
        with self.store.tx() as db:
            db.execute("UPDATE source_state SET config_rev=?,validators=? WHERE source_id='brickset-ca'", (policy.CONFIG_REVISION - 1, '{"etag":"old"}'))
            db.execute("UPDATE runs SET config_rev=? WHERE run_id=?", (policy.CONFIG_REVISION - 1, claim['runId']))
        loaded = Store(self.path, clock=self.clock)
        state = next(row for row in loaded.sources() if row['sourceId'] == 'brickset-ca')
        self.assertEqual(state['configRevision'], policy.CONFIG_REVISION)
        self.assertFalse(state['inFlight'])
        self.assertEqual(state['outcome'], 'failed')
        self.assertEqual(state['error'], 'config-revised')
        self.assertEqual(state['nextEligibleAt'], reference.stamp(self.clock() + policy.TTL))
        with loaded.tx() as db:
            run = db.execute('SELECT outcome,error FROM runs WHERE run_id=?', (claim['runId'],)).fetchone()
            self.assertEqual(tuple(run), ('failed', 'config-revised'))
        self.assertEqual(state['validators'], {})
        self.assertEqual(loaded.complete('brickset-ca', claim, [])['reason'], 'superseded')

    def test_mode_opt_in_and_no_synthetic_live_mixing(self):
        with self.assertRaisesRegex(ValueError, 'mode-mismatch'):
            Store(self.path, mode='synthetic')
        claim = self.store.claim('brickset-us', 'manual', 'synthetic-mixed-mode')
        rows = articles(fixtures.feed('brickset-us', self.clock()), 'brickset-us', reference.stamp(self.clock()), synthetic=True)[0]
        with self.assertRaisesRegex(ValueError, 'persistent-live-denied'):
            self.store.complete('brickset-us', claim, rows)
        self.assertEqual(self.store.deals(), [])

    def test_restrictive_source_cache_directive_discards_live_baseline(self):
        self.coordinator.refresh('manual')
        self.assertEqual(len(self.store.deals()), 2)
        self.clock.advance(policy.TTL)
        self.fetch.side_effect = lambda source, conditional: (200, fixtures.feed(source, self.clock()), {'cache-control': 'private, No-Store'})
        self.assertEqual(self.coordinator.refresh('foreground')['outcome'], 'failed')
        self.assertEqual(self.store.deals(), [])
        self.assertTrue(all(state['error'] == 'source-cache-denied' and state['validators'] == {} for state in self.store.sources()))
        self.clock.advance(policy.TTL * 2)
        self.fetch.side_effect = lambda source, conditional: (304, b'', {'cache-control': 'no-cache'})
        self.assertEqual(self.coordinator.refresh('manual')['outcome'], 'failed')
        self.assertEqual(self.store.deals(), [])


if __name__ == '__main__':
    unittest.main()

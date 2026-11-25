"""V0.1 local contract/security tests. ALL feed data is invented synthetic XML."""
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from pilot import policy, fixtures
from pilot.app import ReaderServer
from pilot.auth import Auth
from pilot.normalize import articles, reference, source_link
from pilot.maintenance import copy_database
from pilot.refresh import Coordinator
from pilot.store import Store, Conflict
from pilot.transport import FetchError, NetworkFetcher, PinnedHTTPS, _https_get, retry_time

EMPTY = b'<rss><channel><title>SYNTHETIC empty</title></channel></rss>'
TEST_PASSWORD = 'SYNTHETIC test-only owner passphrase!'


class Clock:
    def __init__(self):
        self.value = 1795593600.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.clock = Clock()
        self.path = Path(self.tmp.name) / 'data.sqlite3'
        self.store = Store(self.path, clock=self.clock)
        self.body = fixtures.feed('brickset-us', self.clock())
        self.fetch = Mock(return_value=(200, self.body, {}))
        self.coordinator = Coordinator(self.store, self.fetch)

    def us_only(self):
        profile = self.store.profile()
        profile['sources'] = ['brickset-us']
        self.store.update_profile(profile)

    def run_refresh(self):
        return self.coordinator.refresh('manual')

    def state(self):
        return next(row for row in self.store.sources() if row['sourceId'] == 'brickset-us')

    def test_both_markets_same_guid_keep_source_identity(self):
        self.run_refresh()
        rows = self.store.deals()
        self.assertEqual(len(rows), 2)
        self.assertEqual({row['market'] for row in rows}, {'US', 'CA'})
        self.assertEqual(len({(row['sourceId'], row['externalId']) for row in rows}), 2)
        self.assertEqual({row['recordKind'] for row in rows}, {'article'})

    def test_profile_reload_and_literal_casefold_matching(self):
        self.run_refresh()
        profile = self.store.profile()
        profile.update(name='Synthetic custom profile', markets=['US'], include=['GALACTIC'])
        self.store.update_profile(profile)
        loaded = Store(self.path, clock=self.clock)
        self.assertEqual(loaded.profile()['name'], 'Synthetic custom profile')
        self.assertEqual(len(loaded.deals()), 1)
        profile = loaded.profile()
        profile['include'] = ['.*']
        loaded.update_profile(profile)
        self.assertEqual(loaded.deals(), [])
        profile = loaded.profile()
        profile.update(include=[], exclude=['City'])
        loaded.update_profile(profile)
        self.assertEqual(loaded.deals(), [])
        self.assertEqual(self.fetch.call_count, 2)  # Profile edits never fetch.

    def test_profile_revision_and_scope_validation(self):
        profile = self.store.profile()
        self.store.update_profile(profile)
        with self.assertRaises(Conflict):
            self.store.update_profile(profile)
        for update in ({'owner': 'other'}, {'sources': ['slickdeals-us']}, {'markets': ['UK']},
                       {'lookbackDays': True}, {'include': ['']}, {'refreshPreference': 'poll'}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                self.store.update_profile({**self.store.profile(), **update})

    def test_disabled_sources_and_manual_preference(self):
        self.us_only()
        profile = self.store.profile()
        profile['refreshPreference'] = 'manual'
        self.store.update_profile(profile)
        self.assertEqual(self.coordinator.refresh('open')['outcome'], 'skipped')
        self.fetch.assert_not_called()
        self.run_refresh()
        self.assertEqual(self.fetch.call_count, 1)

    def test_ttl_idempotency_and_reload(self):
        self.us_only()
        first = self.coordinator.refresh('manual', 'synthetic-key-1')
        self.assertEqual(first['outcome'], 'completed')
        self.coordinator.refresh('manual', 'synthetic-key-1')
        self.coordinator.refresh('foreground', 'synthetic-key-2')
        self.fetch.assert_called_once()
        self.assertEqual(len(Store(self.path, clock=self.clock).deals()), 1)
        self.clock.advance(policy.TTL)
        self.run_refresh()
        self.assertEqual(self.fetch.call_count, 2)
        self.assertEqual(self.store.deals()[0]['revision'], 1)

    def test_material_change_and_rolling_snapshot(self):
        self.us_only()
        self.run_refresh()
        self.clock.advance(policy.TTL)
        self.fetch.return_value = (200, self.body.replace(b'Galactic', b'Synthetic UPDATED Galactic'), {})
        self.run_refresh()
        self.assertEqual(self.store.deals()[0]['revision'], 2)
        self.clock.advance(policy.TTL)
        self.fetch.return_value = (200, self.body.replace(b'synthetic-US-article', b'synthetic-US-replacement'), {})
        self.run_refresh()
        self.assertEqual(len(self.store.deals()), 1)
        self.assertEqual(self.store.deals()[0]['externalId'], 'synthetic-US-replacement')
        self.assertEqual(self.store.deals()[0]['availability'], 'unknown')

    def test_failure_preserves_last_good_only_within_retention(self):
        self.us_only()
        self.run_refresh()
        old = self.state()
        expires = self.store.deals()[0]['cacheExpiresAt']
        self.clock.advance(policy.TTL)
        self.fetch.side_effect = FetchError('http-429', self.clock() + 9000)
        self.run_refresh()
        state = self.state()
        self.assertEqual(state['lastSuccessAt'], old['lastSuccessAt'])
        self.assertNotEqual(state['lastAttemptAt'], old['lastAttemptAt'])
        self.assertEqual(state['outcome'], 'failed')
        self.assertEqual(self.store.deals()[0]['cacheExpiresAt'], expires)
        self.assertEqual(state['nextEligibleAt'], reference.stamp(self.clock() + 9000))
        self.clock.advance(policy.RETENTION)
        self.assertEqual(self.store.deals(), [])
        self.assertEqual(self.state()['freshness'], 'expired')

    def test_empty_is_success_not_failure(self):
        self.us_only()
        self.run_refresh()
        self.clock.advance(policy.TTL)
        self.fetch.return_value = (200, EMPTY, {})
        self.run_refresh()
        self.assertEqual(self.state()['outcome'], 'success-empty')
        self.assertEqual(self.store.deals(), [])
        self.assertEqual(self.state()['freshness'], 'fresh')

    def test_malformed_and_unsafe_feed_preserve_success(self):
        self.us_only()
        self.run_refresh()
        old = self.state()['lastSuccessAt']
        self.clock.advance(policy.TTL)
        self.fetch.return_value = (200, b'<rss><channel>', {})
        self.run_refresh()
        self.assertEqual(self.state()['lastSuccessAt'], old)
        self.assertEqual(len(self.store.deals()), 1)

    def test_304_conditional_does_not_extend_content_retention(self):
        self.us_only()
        self.fetch.return_value = (200, self.body, {'etag': '"synthetic-1"', 'last-modified': 'Wed, 25 Nov 2026 06:00:00 GMT'})
        self.run_refresh()
        expires = self.store.deals()[0]['cacheExpiresAt']
        self.clock.advance(policy.TTL)
        self.fetch.return_value = (304, b'', {})
        self.run_refresh()
        self.assertEqual(self.fetch.call_args.args[1], {'If-None-Match': '"synthetic-1"', 'If-Modified-Since': 'Wed, 25 Nov 2026 06:00:00 GMT'})
        self.assertEqual(self.state()['outcome'], 'unchanged')
        self.assertEqual(self.store.deals()[0]['cacheExpiresAt'], expires)
        self.clock.advance(policy.RETENTION)
        self.run_refresh()
        self.assertEqual(self.state()['outcome'], 'failed')
        self.assertEqual(self.store.deals(), [])

    def test_unsolicited_304_is_failure(self):
        self.us_only()
        self.fetch.return_value = (304, b'', {})
        self.run_refresh()
        self.assertEqual(self.state()['outcome'], 'failed')
        self.assertIsNone(self.state()['lastSuccessAt'])

    def test_success_and_observed_are_completion_not_attempt_time(self):
        self.us_only()
        started = self.clock()
        def slow_fixture(*_):
            self.clock.advance(7)
            return 200, self.body, {}
        self.fetch.side_effect = slow_fixture
        self.run_refresh()
        self.assertEqual(self.state()['lastAttemptAt'], reference.stamp(started))
        self.assertEqual(self.state()['lastSuccessAt'], reference.stamp(started + 7))
        self.assertEqual(self.store.deals()[0]['observedAt'], reference.stamp(started + 7))

    def test_stale_completion_cannot_overwrite_new_lease(self):
        self.us_only()
        old = self.store.claim('brickset-us', 'manual', 'old-request-key')
        self.clock.advance(policy.LEASE_SECONDS + 1)
        self.store.sources()  # Recovery records failure and a conservative retry interval.
        self.clock.advance(policy.TTL + 1)
        current = self.store.claim('brickset-us', 'manual', 'new-request-key')
        rows = articles(self.body, 'brickset-us', reference.stamp(self.clock()), True)[0]
        self.assertEqual(self.store.complete('brickset-us', old, rows)['reason'], 'superseded')
        self.assertEqual(self.store.complete('brickset-us', current, rows)['outcome'], 'changed')
        self.assertEqual(self.state()['lastSuccessAt'], reference.stamp(self.clock()))

    def test_concurrent_foreground_does_not_duplicate_work(self):
        self.us_only()
        entered, release = threading.Event(), threading.Event()
        def fetch(*_):
            entered.set()
            self.assertTrue(release.wait(3))
            return 200, self.body, {}
        self.fetch.side_effect = fetch
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.coordinator.refresh, 'open', 'request-concurrent-1')
            self.assertTrue(entered.wait(3))
            second = pool.submit(self.coordinator.refresh, 'foreground', 'request-concurrent-2')
            try:
                self.assertEqual(second.result(3)['sources']['brickset-us']['reason'], 'in-flight')
            finally:
                release.set()
            self.assertEqual(first.result(3)['outcome'], 'completed')
        self.fetch.assert_called_once()

    def test_restart_recovery_preserves_profile_and_user_files(self):
        self.run_refresh()
        unrelated = Path(self.tmp.name) / 'owner-reference.txt'
        unrelated.write_text('preserve')
        self.clock.advance(policy.RETENTION + 1)
        restored = Store(self.path, clock=self.clock)
        self.assertEqual(restored.deals(), [])
        self.assertEqual(restored.profile()['name'], 'Brickset reader')
        self.assertEqual(unrelated.read_text(), 'preserve')

    def test_abandoned_lease_recovers_as_failed_with_backoff(self):
        self.store.claim('brickset-us', 'manual', 'synthetic-abandoned')
        self.clock.advance(policy.LEASE_SECONDS + 1)
        restored = Store(self.path, clock=self.clock)
        state = next(s for s in restored.sources() if s['sourceId'] == 'brickset-us')
        self.assertFalse(state['inFlight'])
        self.assertEqual(state['error'], 'lease-expired')
        self.assertEqual(state['outcome'], 'failed')
        self.assertEqual(state['nextEligibleAt'], reference.stamp(self.clock() + policy.TTL))

    def test_backup_restore_invalidates_sessions_and_never_overwrites(self):
        auth = Auth(self.store)
        auth.setup(TEST_PASSWORD)
        token, _ = auth.login(TEST_PASSWORD)
        self.run_refresh()
        backup, restored = Path(self.tmp.name) / 'backup.sqlite3', Path(self.tmp.name) / 'restored.sqlite3'
        copy_database(self.path, backup)
        copy_database(backup, restored, restore=True)
        recovered = Store(restored)
        self.assertEqual(recovered.profile(), self.store.profile())
        self.assertIsNone(Auth(recovered).session(token))
        self.assertIsNotNone(auth.session(token))
        with self.assertRaises(ValueError):
            copy_database(self.path, backup)

    def test_corrupt_store_is_not_silently_recreated(self):
        broken = Path(self.tmp.name) / 'broken.sqlite3'
        broken.write_bytes(b'SYNTHETIC corrupt database')
        with self.assertRaises(sqlite3.DatabaseError):
            Store(broken)
        self.assertEqual(broken.read_bytes(), b'SYNTHETIC corrupt database')

    def test_live_denied_before_injected_transport_and_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            live = Store(Path(directory) / 'live.sqlite3', mode='live-blocked', clock=self.clock)
            fetch = Mock()
            self.assertEqual(Coordinator(live, fetch).refresh('manual')['outcome'], 'failed')
            fetch.assert_not_called()
            self.assertEqual(live.deals(), [])
            claim = live.claim('brickset-us', 'manual', 'different-key-1')
            self.assertNotIn('token', claim)  # Permission failure backoff cannot be bypassed.
        rows = articles(self.body, 'brickset-us', reference.stamp(self.clock()), False)[0]
        claim = self.store.claim('brickset-us', 'manual', 'different-key-2')
        with self.assertRaisesRegex(ValueError, 'persistent-live-denied'):
            self.store.complete('brickset-us', claim, rows)
        self.assertEqual(self.store.deals(), [])

    def test_schema_and_mode_mismatch_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'mode-mismatch'):
            Store(self.path, mode='live-blocked')
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('PRAGMA user_version=99')
        with self.assertRaisesRegex(ValueError, 'schema-version'):
            Store(self.path)

    def test_partial_source_failure_is_not_whole_feed_empty(self):
        def fetch(source, _):
            if source == 'brickset-ca':
                raise FetchError('http-503')
            return 200, self.body, {}
        self.fetch.side_effect = fetch
        result = self.run_refresh()
        self.assertEqual(result['outcome'], 'partial')
        self.assertEqual(result['sources']['brickset-ca']['outcome'], 'failed')
        self.assertEqual(len(self.store.deals()), 1)

    def test_snapshot_count_bound_and_bounded_run_history(self):
        body = ('<rss><channel>' + ''.join('<item><guid>synthetic-' + str(i) + '</guid><title>Fixture</title><link>https://brickset.com/article/synthetic-' + str(i) + '</link></item>' for i in range(65)) + '</channel></rss>').encode()
        self.us_only()
        self.fetch.return_value = (200, body, {})
        self.run_refresh()
        self.assertEqual(len(self.store.deals()), policy.MAX_RECORDS)
        for index in range(110):
            self.coordinator.refresh('open', 'synthetic-bounded-' + str(index))
        self.store.sources()
        with self.store.tx() as db:
            self.assertLessEqual(db.execute('SELECT count(*) FROM runs').fetchone()[0], 100)

    def test_stale_and_unknown_publication_date_policy(self):
        self.us_only()
        self.run_refresh()
        profile = self.store.profile()
        profile['lookbackDays'] = 1
        self.store.update_profile(profile)
        self.clock.advance(policy.TTL)
        old_body = fixtures.feed('brickset-us', self.clock() - 3 * 86400)
        self.fetch.return_value = (200, old_body, {})
        self.run_refresh()
        self.assertEqual(self.store.deals(), [])
        self.clock.advance(policy.TTL)
        unknown = old_body[:old_body.index(b'<pubDate>')] + old_body[old_body.index(b'</pubDate>') + len(b'</pubDate>'):]
        self.fetch.return_value = (200, unknown, {})
        self.run_refresh()
        self.assertIsNone(self.store.deals()[0]['publishedAt'])


class NormalizationTests(unittest.TestCase):
    def test_safe_article_only_and_unknown_fields(self):
        rows, rejected = articles(fixtures.feed('brickset-ca', 1795593600), 'brickset-ca', reference.stamp(), True)
        self.assertEqual(rejected, 0)
        row = rows[0]
        self.assertEqual(row['market'], 'CA')
        self.assertIsNone(row['summary'])
        for key in ('price', 'discount', 'merchant', 'expiresAt', 'productId', 'referencePrice'):
            self.assertIsNone(row[key])
        self.assertNotIn('links', row['provenance'])

    def test_article_link_constraints_and_queries(self):
        self.assertEqual(source_link('https://brickset.com/article/fixture?tag=synthetic'), 'https://brickset.com/article/fixture?tag=synthetic')
        for url in ('http://brickset.com/article/1', 'https://brickset.com.evil.test/article/1',
                    'https://brickset.com:444/article/1', 'https://127.0.0.1/article/1',
                    'javascript:alert(1)', 'https://example.com/article/1', 'https://brickset.com/buy',
                    'https://brickset.com\\evil.test/article/1'):
            self.assertIsNone(source_link(url))

    def test_missing_guid_uses_article_url_and_unsafe_feed_rejected(self):
        body = fixtures.feed('brickset-us', 1795593600).replace(b'<guid>synthetic-US-article</guid>', b'')
        row = articles(body, 'brickset-us', reference.stamp(), True)[0][0]
        self.assertEqual(row['externalId'], row['canonicalUrl'])
        for payload in (b'<!DOCTYPE rss><rss/>', b'<rss><channel>', b'x' * (policy.MAX_BYTES + 1),
                        b'<rss><channel><item><title>identity-less</title></item></channel></rss>'):
            with self.assertRaises(ValueError):
                articles(payload, 'brickset-us', reference.stamp(), True)

    def test_atom_and_markup(self):
        atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>synthetic-id</id><title>&lt;script&gt;evil()&lt;/script&gt;Synthetic article</title><link href="https://brickset.com/article/synthetic"/></entry></feed>'
        row = articles(atom, 'brickset-us', reference.stamp(), True)[0][0]
        self.assertEqual(row['title'], 'Synthetic article')
        self.assertEqual(row['externalId'], 'synthetic-id')


class AuthHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.clock = Clock()
        self.store = Store(Path(self.tmp.name) / 'auth.sqlite3', clock=self.clock)
        self.auth = Auth(self.store)
        self.auth.setup(TEST_PASSWORD)
        self.fetch = Mock(side_effect=lambda source, _: (200, fixtures.feed(source, self.clock()), {}))
        self.server = ReaderServer(self.store, port=0, coordinator=Coordinator(self.store, self.fetch))
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=0.02), daemon=True)
        self.thread.start()
        self.cookie, self.csrf = None, None

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, path, method='GET', body=None, headers=None, origin=True):
        options = {}
        if origin:
            options['Origin'] = self.server.origin
        if self.cookie:
            options['Cookie'] = self.cookie
        if self.csrf:
            options['X-CSRF-Token'] = self.csrf
        if body is not None:
            options['Content-Type'] = 'application/json'
        options.update(headers or {})
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request(method, path, body=json.dumps(body) if body is not None else None, headers=options)
        response = connection.getresponse()
        data = response.read()
        status, response_headers = response.status, dict(response.getheaders())
        connection.close()
        value = json.loads(data) if response_headers.get('Content-Type', '').startswith('application/json') else data.decode()
        return status, value, response_headers

    def login(self):
        status, value, headers = self.request('/api/login', 'POST', {'password': TEST_PASSWORD})
        self.assertEqual(status, 200)
        self.cookie, self.csrf = headers['Set-Cookie'].split(';')[0], value['csrf']
        return headers

    def test_anonymous_read_and_write_denied(self):
        for path in ('/api/deals', '/api/profile', '/api/sources', '/api/session'):
            self.assertEqual(self.request(path)[0], 401)
        self.assertEqual(self.request('/api/profile', 'PATCH', {})[0], 401)
        self.assertEqual(self.request('/api/refresh', 'POST', {'trigger': 'manual'})[0], 401)

    def test_real_password_hashed_and_sessions_not_plaintext(self):
        self.assertEqual(self.request('/api/login', 'POST', {'password': 'invented-wrong-password'})[0], 401)
        headers = self.login()
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        self.assertIn('SameSite=Strict', headers['Set-Cookie'])
        with self.store.tx() as db:
            owner = db.execute('SELECT * FROM owner').fetchone()
            self.assertNotEqual(owner['password_hash'], TEST_PASSWORD.encode())
            stored = db.execute('SELECT token_hash FROM sessions').fetchone()[0]
            self.assertNotEqual(stored, self.cookie.split('=')[1])
        self.assertEqual(self.request('/api/session')[1]['owner'], 'owner')

    def test_csrf_origin_and_host_rebinding(self):
        self.login()
        value = self.store.profile()
        self.assertEqual(self.request('/api/profile', 'PATCH', value, {'X-CSRF-Token': 'wrong'})[0], 403)
        self.assertEqual(self.request('/api/profile', 'PATCH', value, origin=False)[0], 403)
        self.assertEqual(self.request('/api/profile', 'PATCH', value, {'Origin': 'https://evil.invalid'})[0], 403)
        self.assertEqual(self.request('/api/profile', headers={'Host': 'evil.invalid'})[0], 421)

    def test_owner_scope_cannot_be_selected_by_caller(self):
        self.login()
        self.assertEqual(self.request('/api/profile', 'PATCH', {**self.store.profile(), 'owner': 'other'})[0], 400)
        self.assertEqual(self.request('/api/profile?owner=other')[0], 400)
        self.assertEqual(self.request('/api/owners/other/profile')[0], 404)

    def test_end_to_end_refresh_edit_rematch_and_reload(self):
        self.login()
        self.assertEqual(self.request('/api/deals')[1]['articles'], [])
        result = self.request('/api/refresh', 'POST', {'trigger': 'manual'}, {'Idempotency-Key': 'synthetic-http-key-1'})
        self.assertEqual(result[0], 200)
        self.assertEqual(result[1]['outcome'], 'completed')
        self.assertEqual(len(self.request('/api/deals')[1]['articles']), 2)
        profile = self.request('/api/profile')[1]
        profile.update(markets=['CA'], include=['galactic'])
        self.assertEqual(self.request('/api/profile', 'PATCH', profile)[0], 200)
        self.assertEqual(self.request('/api/profile', 'PATCH', profile)[0], 409)
        rows = self.request('/api/deals')[1]['articles']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['market'], 'CA')
        self.assertEqual(len(Store(self.store.path, clock=self.clock).deals()), 1)
        self.fetch.assert_any_call('brickset-ca', {})
        self.assertEqual(self.fetch.call_count, 2)

    def test_logout_revokes_session_and_clears_browser_storage(self):
        self.login()
        status, _, headers = self.request('/api/logout', 'POST', {})
        self.assertEqual(status, 200)
        self.assertIn('Max-Age=0', headers['Set-Cookie'])
        self.assertIn('storage', headers['Clear-Site-Data'])
        self.assertEqual(self.request('/api/deals')[0], 401)

    def test_session_expires_and_login_throttles(self):
        self.login()
        self.clock.advance(3601)
        self.assertEqual(self.request('/api/deals')[0], 401)
        self.cookie, self.csrf = None, None
        for _ in range(5):
            self.request('/api/login', 'POST', {'password': 'synthetic wrong password'})
        self.assertEqual(self.request('/api/login', 'POST', {'password': TEST_PASSWORD})[0], 401)
        self.clock.advance(400)
        self.assertEqual(self.request('/api/login', 'POST', {'password': TEST_PASSWORD})[0], 200)

    def test_private_responses_and_static_shell_have_no_owner_data(self):
        status, html, headers = self.request('/')
        self.assertEqual(status, 200)
        self.assertNotIn(TEST_PASSWORD, html)
        self.assertIn("script-src 'self'", headers['Content-Security-Policy'])
        self.assertIn('no-store', headers['Cache-Control'])
        self.assertNotIn('Access-Control-Allow-Origin', headers)
        _, js, _ = self.request('/app.js')
        self.assertNotIn('innerHTML', js)
        self.assertNotIn('localStorage', js)
        self.assertIn('textContent', js)
        self.assertEqual(self.request('/../../.local/pilot.sqlite3')[0], 404)

    def test_input_limits_invalid_trigger_and_no_fake_auth(self):
        self.assertEqual(self.request('/api/deals', headers={'X-Owner': 'owner', 'Authorization': 'Bearer synthetic-fake'})[0], 401)
        self.login()
        self.assertEqual(self.request('/api/refresh', 'POST', {'trigger': 'manual'})[0], 400)
        self.assertEqual(self.request('/api/refresh', 'POST', {'trigger': 'background'}, {'Idempotency-Key': 'synthetic-http-key-2'})[0], 400)
        self.assertEqual(self.request('/api/profile', 'PATCH', {'name': 'x' * 17000})[0], 400)


class TransportTests(unittest.TestCase):
    def test_live_permission_before_subprocess_and_dns(self):
        with patch('pilot.policy.live_allowed', return_value=False), patch('pilot.transport.subprocess.run') as run, patch('pilot.transport.socket.getaddrinfo') as dns:
            for source in ('brickset-ca', 'brickset-us', 'slickdeals-us', 'http://127.0.0.1'):
                with self.assertRaisesRegex(FetchError, 'permission-denied'):
                    NetworkFetcher()(source, {})
            run.assert_not_called()
            dns.assert_not_called()

    def test_worker_deadline_kills_owned_worker_via_subprocess_contract(self):
        with patch('pilot.policy.live_allowed', return_value=True), patch('pilot.transport.subprocess.run', side_effect=subprocess.TimeoutExpired('synthetic worker', 12)) as run:
            with self.assertRaisesRegex(FetchError, 'overall-deadline'):
                NetworkFetcher()('brickset-ca', {})
            self.assertEqual(run.call_args.kwargs['timeout'], policy.HARD_TIMEOUT)

    def test_actual_sleeping_owned_worker_is_cancelled(self):
        import sys
        actual_run, actual_popen = subprocess.run, subprocess.Popen
        workers = []
        def popen(*args, **kwargs):
            worker = actual_popen(*args, **kwargs)
            workers.append(worker)
            return worker
        def slow_worker(_command, **kwargs):
            # An actual synthetic sleeping subprocess, no network/DNS/provider.
            return actual_run([sys.executable, '-c', 'import time; time.sleep(30)'], **kwargs)
        start = time.monotonic()
        with patch('pilot.policy.live_allowed', return_value=True), patch('pilot.policy.HARD_TIMEOUT', 0.15), patch('pilot.transport.subprocess.run', side_effect=slow_worker), patch('subprocess.Popen', side_effect=popen):
            with self.assertRaisesRegex(FetchError, 'overall-deadline'):
                NetworkFetcher()('brickset-us', {})
        self.assertLess(time.monotonic() - start, 3)
        self.assertEqual(len(workers), 1)
        self.assertIsNotNone(workers[0].poll())

    def test_private_and_mixed_dns_rejected(self):
        for ips in (['127.0.0.1'], ['::1'], ['169.254.169.254'], ['8.8.8.8', '10.1.2.3']):
            records = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443)) for ip in ips]
            with patch('pilot.transport.socket.getaddrinfo', return_value=records), self.assertRaisesRegex(FetchError, 'unsafe-destination'):
                _https_get('brickset-ca', {})
        with self.assertRaisesRegex(FetchError, 'unknown-source'):
            _https_get('https://brickset.com/not-allowlisted', {})

    def response(self, status=200, body=EMPTY, **headers):
        response = Mock(status=status)
        values = {'Content-Type': 'text/xml', 'Content-Length': str(len(body)), **headers}
        response.getheader.side_effect = lambda name, default=None: values.get(name, default)
        response.getheaders.return_value = list(values.items())
        response.read.return_value = body
        return response

    def transport(self, response, conditional=None):
        connection = Mock()
        connection.getresponse.return_value = response
        with patch('pilot.transport.socket.getaddrinfo', return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))]), patch('pilot.transport.PinnedHTTPS', return_value=connection):
            return _https_get('brickset-us', conditional or {})

    def test_http_variants_and_validator_safety(self):
        self.assertEqual(self.transport(self.response())[0], 200)
        self.assertEqual(self.transport(self.response(304))[0], 304)
        for response in (self.response(302), self.response(503), self.response(**{'Content-Encoding': 'gzip'}),
                         self.response(**{'Content-Type': 'text/html'}), self.response(**{'Content-Length': '999999999'}),
                         self.response(**{'Content-Length': '9999'}), self.response(body=b'x' * (policy.MAX_BYTES + 1))):
            with self.assertRaises(FetchError):
                self.transport(response)
        with self.assertRaisesRegex(FetchError, 'invalid-validator'):
            self.transport(self.response(), {'If-None-Match': 'synthetic\r\nInjected: value'})

    def test_tls_hostname_pinning(self):
        with patch('pilot.transport.socket.create_connection') as connect, patch('pilot.transport.ssl.create_default_context') as context:
            PinnedHTTPS('brickset.com', '8.8.8.8').connect()
            connect.assert_called_once_with(('8.8.8.8', 443), timeout=5)
            context.return_value.wrap_socket.assert_called_once_with(connect.return_value, server_hostname='brickset.com')

    def test_retry_after_numeric_and_date(self):
        self.assertEqual(retry_time('7200', 1000), 8200)
        self.assertEqual(retry_time('Wed, 25 Nov 2026 06:00:00 GMT', 1000), 1795586400)
        self.assertIsNone(retry_time('invalid', 1000))


if __name__ == '__main__':
    unittest.main(verbosity=2)

"""V0.0.1 regressions: all data and transports here are explicitly synthetic."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import feedcompat as f
import brickset_reader as r

RSS = (f.ROOT / 'fixtures/rss.xml').read_bytes()


class Reader(unittest.TestCase):
    def test_default_transport_still_blocked_and_slickdeals_never_enabled(self):
        with patch.object(f, 'validate_destination') as validate:
            for source in f.SOURCES:
                with self.assertRaises(PermissionError):
                    f.retrieve(source, {})
            with self.assertRaises(PermissionError):
                f.retrieve('slickdeals-us', {}, brickset_reader=True)
            validate.assert_not_called()

    def test_xml_depth_bound(self):
        body = b'<rss><channel><item><description>' + b'<b>' * 1200 + b'x' + b'</b>' * 1200 + b'</description></item></channel></rss>'
        with self.assertRaisesRegex(ValueError, 'depth/node'):
            f.parse_feed(body, 'brickset-us', synthetic=True)

    def test_structure_and_minimum_metadata(self):
        body = RSS.replace(b'Two offers', b'<table><tr><td>A</td></tr><tr><td>B</td></tr><tr><td>C</td></tr></table>')
        rows, findings = r.inspect_records(body, 'brickset-ca', f.stamp(), synthetic=True)
        self.assertEqual(findings['samples'][0]['semantics'], 'article-aggregate')
        self.assertEqual(findings['offerRowsExtracted'], 0)
        self.assertTrue(all(row['summary'] == '' and row['price'] is None for row in rows))
        self.assertEqual(rows[0]['market'], 'CA')
        self.assertEqual(rows[0]['provenance']['links'], ['https://example.com/offer?tag=synthetic'])

    def test_metadata_bound_ten(self):
        body = ('<rss><channel>' + ''.join('<item><guid>synthetic-' + str(i) + '</guid><title>Fixture</title></item>' for i in range(20)) + '</channel></rss>').encode()
        rows, findings = r.inspect_records(body, 'brickset-us', f.stamp(), synthetic=True)
        self.assertEqual(len(rows), 10)
        self.assertEqual(findings['rawItemCount'], 20)
        self.assertEqual(findings['inspected'], 10)

    def test_session_persistence_and_one_request_budget(self):
        with tempfile.TemporaryDirectory() as root:
            budget = f.Cache(Path(root) / 'budget')
            cache = r.ReaderCache(Path(root) / 'session', time.time() + 60)
            summaries = {}
            # Test-only transport: synthetic XML is not live evidence despite exercising reader storage.
            with patch.object(f, 'retrieve', return_value=(200, RSS, {'status': 200})) as retrieve:
                self.assertEqual(r.fetch_once(cache, budget, 'brickset-ca', summaries), 'updated')
                self.assertTrue(summaries['brickset-ca']['diskReloadMatches'])
                with self.assertRaises(RuntimeError):
                    r.fetch_once(cache, budget, 'brickset-ca', summaries)
                retrieve.assert_called_once_with('brickset-ca', {}, brickset_reader=True)
            self.assertNotIn('Synthetic multi-offer', json.dumps(budget.load()))
            self.assertEqual(cache.load()['sources']['brickset-ca']['records'][0]['summary'], '')

    def test_cache_expires_without_deleting_other_user_files(self):
        with tempfile.TemporaryDirectory() as root:
            cache = r.ReaderCache(Path(root) / 'session', time.time() + 60)
            other = Path(root) / 'user.txt'
            other.write_text('preserve')
            cache.save({'sources': {'brickset-us': {'records': [], 'lastSuccessAt': None}}})
            cache.deadline_epoch = 0
            self.assertEqual(cache.load(), {'sources': {}})
            self.assertEqual(json.loads(cache.path.read_text()), {'sources': {}})
            self.assertEqual(other.read_text(), 'preserve')

    def test_mixed_data_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            cache = r.ReaderCache(root, time.time() + 60)
            rows = f.parse_feed(RSS, 'brickset-us', synthetic=True)
            with self.assertRaises(ValueError):
                cache.save({'sources': {'brickset-us': {'records': rows}}})
            with self.assertRaises(ValueError):
                cache.save({'sources': {'slickdeals-us': {'records': []}}})

    def test_failure_is_logged_without_content_and_not_retried(self):
        with tempfile.TemporaryDirectory() as root:
            budget = f.Cache(Path(root) / 'budget')
            cache = r.ReaderCache(Path(root) / 'session', time.time() + 60)
            summaries = {}
            error = f.RetrievalError(429, {'status': 429, 'retry-after': '7200'})
            with patch.object(f, 'retrieve', side_effect=error) as retrieve:
                self.assertEqual(r.fetch_once(cache, budget, 'brickset-us', summaries), 'failed')
                with self.assertRaises(RuntimeError):
                    r.fetch_once(cache, budget, 'brickset-us', summaries)
                self.assertEqual(retrieve.call_count, 1)
            self.assertEqual(summaries['brickset-us']['http']['status'], 429)
            self.assertIsNone(summaries['brickset-us']['lastSuccessAt'])

    def test_preview_status_empty_failure_stale_and_links(self):
        state = {'sources': {'brickset-ca': {'lastSuccessAt': None, 'records': [], 'error': 'HTTP 403'}}}
        body = f.render(state, brickset_reader=True).decode()
        self.assertIn('Personal reader metadata only', body)
        self.assertIn('No cached records.', body)
        self.assertIn('Retrieval failed or blocked.', body)
        self.assertIn('stale / unknown', body)
        self.assertIn('HTTP 403', body)
        self.assertIn('slickdeals-us: BLOCKED', body)


if __name__ == '__main__':
    unittest.main(verbosity=2)

"""Synthetic tests never count as live compatibility evidence."""
import http.client
import socket
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from http.server import HTTPServer

import feedcompat as f

RSS = (f.ROOT / 'fixtures/rss.xml').read_bytes()
ATOM = (f.ROOT / 'fixtures/atom.xml').read_bytes()
EMPTY = b'<rss><channel><title>empty fixture</title></channel></rss>'


class Parsing(unittest.TestCase):
    def parse(self, payload=RSS, source='brickset-us'):
        return f.parse_feed(payload, source, f.stamp(1000), synthetic=True)

    def test_rss_and_contract(self):
        rows = self.parse()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['schemaVersion'], 1)
        self.assertEqual(rows[0]['externalId'], 'synthetic-article-1')
        self.assertEqual(rows[0]['verification'], 'unverified')
        self.assertEqual(rows[0]['recordKind'], 'article-or-offer-unknown')
        self.assertTrue(rows[0]['provenance']['synthetic'])

    def test_atom(self):
        row = self.parse(ATOM, 'slickdeals-us')[0]
        self.assertEqual(row['externalId'], 'urn:synthetic:offer:1')
        self.assertEqual(row['publishedAt'], '2026-11-25T06:00:00+00:00')

    def test_missing_id_stable_fallback(self):
        row = self.parse()[1]
        self.assertTrue(row['externalId'].startswith('fallback:'))
        self.assertEqual(row['externalId'], self.parse()[1]['externalId'])
        self.assertFalse(row['provenance']['nativeIdentifier'])

    def test_url_fallback(self):
        row = self.parse(b'<rss><channel><item><link>https://example.com/x?a=1</link></item></channel></rss>')[0]
        self.assertEqual(row['externalId'], 'https://example.com/x?a=1')

    def test_malformed_truncated_and_wrong_root(self):
        for payload in (b'<rss><channel>', b'<html/>', b'<rss/>', b''):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.parse(payload)

    def test_dtd_and_entities(self):
        for payload in (b'<!DOCTYPE rss><rss/>', b'<!ENTITY e SYSTEM "file:///etc/passwd"><rss/>',
                        '<!DOCTYPE rss><rss/>'.encode('utf-16')):
            with self.subTest(payload=payload), self.assertRaises((ValueError, UnicodeError)):
                self.parse(payload)

    def test_unsafe_markup_removed(self):
        text, links = f.clean('<script>evil()</script><style>bad</style><svg>bad</svg>'
                              '<img src=x onerror=alert(1)><a href="javascript:evil()">safe text</a>')
        self.assertEqual(text, 'safe text')
        self.assertEqual(links, [])

    def test_bounded_text_and_payload(self):
        self.assertEqual(len(f.clean('a' * 2000)[0]), 500)
        with self.assertRaises(ValueError):
            self.parse(b' ' * (f.MAX_BYTES + 1))

    def test_links_and_affiliates_preserved(self):
        row = self.parse()[0]
        self.assertEqual(row['canonicalUrl'], 'https://example.com/article?affiliate=preserved')
        self.assertEqual(row['provenance']['links'], ['https://example.com/offer?tag=synthetic'])

    def test_unsafe_links(self):
        for url in ('javascript:alert(1)', 'data:text/html,x', '//example.com',
                    'https://u:p@example.com', 'https://example.com/\nx', 'https://[broken',
                    'http://127.0.0.1/', 'http://localhost/', 'http://[::1]/', 'http://169.254.169.254/'):
            self.assertIsNone(f.safe_link(url))

    def test_native_identifier_not_silently_truncated(self):
        with self.assertRaises(ValueError):
            self.parse(b'<rss><channel><item><guid>' + b'x' * 4097 + b'</guid></item></channel></rss>')

    def test_invalid_prices_and_rewards_are_not_discount(self):
        for row in self.parse() + self.parse(ATOM):
            for key in ('price', 'referencePrice', 'comparisonBasis', 'discount', 'expiresAt'):
                self.assertIsNone(row[key])
            self.assertEqual(row['availability'], 'unknown')

    def test_unknown_market(self):
        self.assertEqual(self.parse(source='unknown-fixture')[0]['market'], 'unknown')

    def test_markets_separate_same_native_id(self):
        us, ca = self.parse()[0], self.parse(source='brickset-ca')[0]
        self.assertEqual(us['externalId'], ca['externalId'])
        self.assertNotEqual((us['sourceId'], us['market']), (ca['sourceId'], ca['market']))

    def test_duplicate_native_ids(self):
        body = b'<rss><channel><item><guid>x</guid><title>A</title></item><item><guid>x</guid><title>A</title></item></channel></rss>'
        self.assertEqual(len(self.parse(body)), 1)

    def test_dates_do_not_invent_timezone(self):
        self.assertIsNone(f.date('2026-11-25T06:00:00'))
        self.assertIsNone(f.date('nonsense'))


class Persistence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = f.Cache(self.tmp.name)
        self.fetch = Mock(return_value=(200, RSS, {'etag': '"fixture-v1"', 'last-modified': 'Wed, 25 Nov 2026 06:00:00 GMT'}))

    def refresh(self, now=1000, fetch=None, source='brickset-us'):
        return self.cache.refresh(source, fetch or self.fetch, now=now, synthetic=True)

    def entry(self):
        return self.cache.load()['sources']['brickset-us']

    def test_reload(self):
        self.refresh()
        self.assertEqual(self.cache.load(), f.Cache(self.tmp.name).load())
        self.assertEqual(len(self.entry()['records']), 2)

    def test_ttl(self):
        self.refresh()
        self.assertEqual(self.refresh(2799), 'fresh')
        self.fetch.assert_called_once()
        self.assertEqual(self.refresh(2800), 'updated')
        self.assertEqual(self.fetch.call_count, 2)

    def test_unchanged_dedup_and_revision(self):
        self.refresh()
        self.refresh(2800)
        self.assertEqual(len(self.entry()['records']), 2)
        self.assertEqual(self.entry()['records'][0]['revision'], 1)
        self.assertEqual(self.entry()['lastSuccessAt'], f.stamp(2800))

    def test_material_change_same_id(self):
        self.refresh()
        before = self.entry()['records'][0]['contentHash']
        self.refresh(2800, Mock(return_value=(200, RSS.replace(b'Two offers', b'Three offers'), {})))
        self.assertEqual(self.entry()['records'][0]['revision'], 2)
        self.assertNotEqual(before, self.entry()['records'][0]['contentHash'])

    def test_conditional_304(self):
        self.refresh()
        old = self.entry()['records']
        fetch = Mock(return_value=(304, b'', {}))
        self.refresh(2800, fetch)
        self.assertEqual(self.entry()['records'], old)
        self.assertEqual(self.entry()['lastSuccessAt'], f.stamp(2800))
        self.assertEqual(fetch.call_args.args[1], {'If-None-Match': '"fixture-v1"',
                                                  'If-Modified-Since': 'Wed, 25 Nov 2026 06:00:00 GMT'})

    def test_unsolicited_304(self):
        self.assertEqual(self.refresh(fetch=Mock(return_value=(304, b'', {}))), 'failed')
        self.assertIsNone(self.entry()['lastSuccessAt'])

    def test_empty_and_disappearance_preserve_inventory_unknown(self):
        self.refresh()
        rows = self.entry()['records']
        self.refresh(2800, Mock(return_value=(200, EMPTY, {})))
        self.assertEqual(self.entry()['records'], rows)
        self.assertEqual(self.entry()['lastSuccessAt'], f.stamp(2800))

    def test_valid_empty_initial(self):
        self.refresh(fetch=Mock(return_value=(200, EMPTY, {})))
        self.assertEqual(self.entry()['records'], [])
        self.assertEqual(self.entry()['lastSuccessAt'], f.stamp(1000))

    def test_failure_preservation_and_backoff(self):
        for failure in (TimeoutError('timeout'), ValueError('HTTP 503'),
                        ValueError('truncated response')):
            with self.subTest(failure=failure):
                self.cache.path.unlink(missing_ok=True)
                self.refresh()
                old = self.entry()
                bad = Mock(side_effect=failure)
                self.assertEqual(self.refresh(2800, bad), 'failed')
                self.assertEqual(self.entry()['lastSuccessAt'], old['lastSuccessAt'])
                self.assertEqual(self.entry()['records'], old['records'])
                self.assertEqual(self.entry()['lastAttemptAt'], f.stamp(2800))
                self.assertEqual(self.refresh(2801, bad), 'backoff')
                bad.assert_called_once()

    def test_parse_failure_preserves(self):
        self.refresh()
        self.refresh(2800, Mock(return_value=(200, b'<rss><channel>', {})))
        self.assertEqual(self.entry()['lastSuccessAt'], f.stamp(1000))
        self.assertEqual(len(self.entry()['records']), 2)

    def test_cross_market_persistence(self):
        self.refresh()
        self.refresh(source='brickset-ca')
        state = self.cache.load()['sources']
        self.assertEqual(len(state['brickset-us']['records']), 2)
        self.assertEqual(len(state['brickset-ca']['records']), 2)

    def test_overlapping_retrieval_rejected(self):
        with self.cache.locked(), self.assertRaises(RuntimeError):
            self.refresh()
        self.fetch.assert_not_called()

    def test_corrupt_cache_not_overwritten(self):
        self.cache.path.write_text('broken')
        with self.assertRaises(ValueError):
            self.refresh()
        self.assertEqual(self.cache.path.read_text(), 'broken')

    def test_retry_after_source_limit(self):
        error = f.RetrievalError(429, {'retry-after': '7200'})
        self.refresh(fetch=Mock(side_effect=error))
        self.assertEqual(self.entry()['nextAttemptEpoch'], 8200)
        self.assertEqual(self.refresh(8199), 'backoff')


class Transport(unittest.TestCase):
    def test_permission_before_dns_or_http(self):
        with patch.object(f.socket, 'getaddrinfo') as dns:
            for source in f.SOURCES:
                with self.assertRaises(PermissionError):
                    f.retrieve(source, {})
            dns.assert_not_called()

    def test_arbitrary_endpoint_rejected_before_dns(self):
        for url in ('http://127.0.0.1', 'https://brickset.com/evil',
                    'https://brickset.com/feed/amazon/us?other=1'):
            with self.assertRaises(ValueError):
                f.validate_destination(url)

    def test_private_dns_and_mixed_dns_rejected(self):
        for addresses in (['127.0.0.1'], ['::1'], ['169.254.169.254'], ['10.0.0.1'], ['8.8.8.8', '192.168.1.1']):
            result = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443)) for ip in addresses]
            with patch.object(f.socket, 'getaddrinfo', return_value=result), self.assertRaises(ValueError):
                f.validate_destination(f.SOURCES['brickset-us']['url'])

    def response(self, status=200, body=EMPTY, headers=None):
        response = Mock(status=status)
        values = {'Content-Type': 'text/xml', 'Content-Length': str(len(body)), **(headers or {})}
        response.getheader.side_effect = lambda key, default=None: values.get(key, default)
        response.getheaders.return_value = list(values.items())
        response.read1.side_effect = [body, b'']
        return response

    def run_response(self, response):
        source = {**f.SOURCES['brickset-us'], 'permitted': True}
        connection = Mock()
        connection.getresponse.return_value = response
        with patch.dict(f.SOURCES, {'brickset-us': source}), patch.object(f, 'validate_destination', return_value=(f.urlsplit(source['url']), '8.8.8.8')), patch.object(f, 'PinnedHTTPS', return_value=connection):
            return f.retrieve('brickset-us', {})

    def test_http_200_and_304(self):
        self.assertEqual(self.run_response(self.response())[0], 200)
        self.assertEqual(self.run_response(self.response(304))[0], 304)

    def test_http_failure_truncation_size_compression_and_redirect(self):
        responses = [self.response(503), self.response(headers={'Content-Length': '10000'}),
                     self.response(headers={'Content-Length': str(f.MAX_BYTES + 1)}),
                     self.response(headers={'Content-Encoding': 'gzip'}),
                     self.response(headers={'Content-Type': 'text/html'}),
                     self.response(302, headers={'Location': 'http://127.0.0.1/private'}),
                     self.response(302, headers={'Location': f.SOURCES['brickset-ca']['url']})]
        for response in responses:
            with self.subTest(response=response), self.assertRaises(ValueError):
                self.run_response(response)

    def test_stream_size_without_content_length(self):
        response = self.response(body=b'x' * (f.MAX_BYTES + 1))
        original = response.getheader.side_effect
        response.getheader.side_effect = lambda key, default=None: None if key == 'Content-Length' else original(key, default)
        with self.assertRaises(ValueError):
            self.run_response(response)

    def test_total_deadline(self):
        with patch.object(f.time, 'monotonic', side_effect=[0, 21]), self.assertRaises(TimeoutError):
            self.run_response(self.response())

    def test_pinned_tls_identity(self):
        with patch.object(f.socket, 'create_connection') as connect, patch.object(f.ssl, 'create_default_context') as context:
            connection = f.PinnedHTTPS('brickset.com', '8.8.8.8')
            connection.connect()
            connect.assert_called_once_with(('8.8.8.8', 443), 10)
            context.return_value.wrap_socket.assert_called_once_with(connect.return_value, server_hostname='brickset.com')

    @unittest.skipUnless(any(s['permitted'] for s in f.SOURCES.values()),
                         'Live permissions unresolved; no fixture counts as live retrieval')
    def test_live_permitted_retrieval(self):
        for source in f.SOURCES:
            if f.SOURCES[source]['permitted']:
                status, body, _ = f.retrieve(source, {})
                self.assertEqual(status, 200)
                f.parse_feed(body, source)


class Preview(unittest.TestCase):
    def test_real_local_http_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = f.Cache(directory)
            cache.refresh('brickset-ca', lambda *_: (200, RSS, {}), synthetic=True)
            server = HTTPServer(('127.0.0.1', 0), f.handler_for(cache))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                connection = http.client.HTTPConnection('127.0.0.1', server.server_port)
                connection.request('GET', '/')
                response = connection.getresponse()
                body = response.read().decode()
                self.assertEqual(response.status, 200)
                self.assertIn('SYNTHETIC FIXTURE', body)
                self.assertIn('CA · unverified', body)
                self.assertIn('width=device-width', body)
                self.assertIn('max-width:480px', body)
                self.assertIn('Last attempt:', body)
                self.assertIn('no-store', response.getheader('Cache-Control'))
                self.assertIn("default-src 'none'", response.getheader('Content-Security-Policy'))
                connection.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_output_escaped(self):
        row = f.parse_feed(RSS, 'brickset-us', synthetic=True)[0]
        row['title'] = '<script>alert(1)</script>'
        row['canonicalUrl'] = 'javascript:alert(1)'
        body = f.render({'sources': {'test': {'records': [row]}}}).decode()
        self.assertNotIn('<script>', body)
        self.assertNotIn('href="javascript:', body)
        self.assertIn('&lt;script&gt;', body)


if __name__ == '__main__':
    unittest.main(verbosity=2)

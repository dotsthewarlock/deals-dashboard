"""Isolated V0.0 RSS reader experiment; standard library only, no scheduler."""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import email.utils
import fcntl
import hashlib
import html
from html.parser import HTMLParser
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import ipaddress
import json
from pathlib import Path
import re
import socket
import ssl
import tempfile
import time
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
TTL = 1800
MAX_BYTES = 1_000_000
SOURCES = {
    'brickset-us': {'url': 'https://brickset.com/feed/amazon/us', 'market': 'US',
                    'permitted': False, 'reason': 'RSS reading published; custom display/retention boundaries unresolved'},
    'brickset-ca': {'url': 'https://brickset.com/feed/amazon/ca', 'market': 'CA',
                    'permitted': False, 'reason': 'RSS reading published; custom display/retention boundaries unresolved'},
    'slickdeals-us': {'url': 'https://slickdeals.net/rss.php', 'market': 'US',
                      'permitted': False, 'reason': 'Express permission required; RSS exception unestablished'},
}


def stamp(epoch=None):
    return dt.datetime.fromtimestamp(time.time() if epoch is None else epoch, dt.UTC).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def safe_link(value):
    """Preserve original query/affiliate links; never execute markup or relative URLs."""
    value = (value or '').strip()
    try:
        u = urlsplit(value)
        if (u.scheme not in ('https', 'http') or not u.hostname or u.username or u.password
                or any(ord(c) < 33 for c in value) or len(value) > 4096):
            return None
        if u.hostname.lower().rstrip('.') in ('localhost', 'localhost.localdomain'):
            return None
        try:
            address = ipaddress.ip_address(u.hostname)
        except ValueError:
            pass
        else:
            if not address.is_global:
                return None
        return value
    except ValueError:
        return None


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.links, self.hidden = [], [], []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'iframe', 'object', 'svg', 'math', 'template'):
            self.hidden.append(tag)
        if not self.hidden:
            if tag == 'a':
                link = safe_link(dict(attrs).get('href'))
                if link and link not in self.links and len(self.links) < 30:
                    self.links.append(link)
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if self.hidden and tag == self.hidden[-1]:
            self.hidden.pop()
        if not self.hidden:
            self.parts.append(' ')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def clean(value, limit=500):
    p = TextOnly()
    p.feed(value or '')
    return ' '.join(''.join(p.parts).split())[:limit], p.links


def date(value):
    if not value:
        return None
    try:
        try:
            parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            parsed = email.utils.parsedate_to_datetime(value)
        return parsed.astimezone(dt.UTC).isoformat() if parsed.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None


def local(tag):
    return tag.rsplit('}', 1)[-1]


def parse_feed(payload, source_id, observed=None, synthetic=False):
    if len(payload) > MAX_BYTES:
        raise ValueError('feed size bound')
    # XML encoding must not hide declarations from the security scan.
    text = payload.decode('utf-8-sig', errors='strict')
    if re.search(r'<!\s*(DOCTYPE|ENTITY)', text, re.I) or '\x00' in text:
        raise ValueError('DTD/entities/unsupported encoding rejected')
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError('malformed or truncated XML') from exc
    pending, nodes = [(root, 1)], 0
    while pending:
        element, depth = pending.pop()
        nodes += 1
        if depth > 32 or nodes > 20000:
            raise ValueError('XML depth/node bound')
        pending.extend((child, depth + 1) for child in element)
    if root.tag == 'rss':
        channel = root.find('channel')
        if channel is None:
            raise ValueError('RSS channel missing')
        items = channel.findall('item')
    elif root.tag == '{http://www.w3.org/2005/Atom}feed':
        items = root.findall('{http://www.w3.org/2005/Atom}entry')
    else:
        raise ValueError('unsupported feed root')
    if len(items) > 1000:
        raise ValueError('item count bound')
    market = SOURCES.get(source_id, {}).get('market', 'unknown')
    result = {}
    for item in items:
        def field(*names):
            for child in item:
                if local(child.tag) in names:
                    # Include XHTML text, but do not treat tags as trusted markup.
                    return ''.join(ET.tostring(c, encoding='unicode') for c in child) if len(child) else child.text or ''
            return ''

        title, _ = clean(field('title'), 200)
        summary, links = clean(field('description', 'summary', 'content', 'encoded'))
        url = None
        for child in item:
            if local(child.tag) == 'link' and child.get('rel', 'alternate') == 'alternate':
                url = safe_link(child.get('href') or child.text)
                if url:
                    break
        native = field('guid', 'id').strip() or None
        if native and len(native) > 4096:
            raise ValueError('native identifier bound')
        published = date(field('pubDate', 'published', 'updated'))
        external = native or url or 'fallback:' + digest([title, published, summary])
        record = dict(schemaVersion=1, sourceId=source_id, externalId=external,
                      canonicalUrl=url, title=title or '(Untitled)', summary=summary,
                      market=market, merchant=None, productId=None, price=None,
                      referencePrice=None, comparisonBasis=None, discount=None,
                      promotion=None, restrictions=None, availability='unknown',
                      verification='unverified', publishedAt=published,
                      expiresAt=None, recordKind='article-or-offer-unknown',
                      provenance={'endpoint': SOURCES.get(source_id, {}).get('url'),
                                  'synthetic': synthetic, 'nativeIdentifier': native is not None,
                                  'identityBasis': 'native' if native else 'url' if url else 'content-fallback',
                                  'links': links})
        # Never interpret dollar signs, reward percentages, article tables, or titles as prices.
        record['contentHash'] = digest(record)
        record.update(observedAt=observed or stamp(), revision=1)
        result[external] = record
    return list(result.values())


def validate_destination(url):
    if url not in {s['url'] for s in SOURCES.values()}:
        raise ValueError('endpoint not allowlisted')
    u = urlsplit(url)
    addresses = sorted({a[4][0] for a in socket.getaddrinfo(u.hostname, 443, type=socket.SOCK_STREAM)})
    if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
        raise ValueError('private/non-global destination')
    return u, addresses[0]


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address):
        super().__init__(host, timeout=10, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        self.sock = socket.create_connection((self.address, 443), self.timeout)
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


class RetrievalError(ValueError):
    def __init__(self, status, metadata):
        super().__init__('HTTP ' + str(status))
        self.metadata = metadata


def retrieve(source_id, conditional, *, brickset_reader=False):
    source = SOURCES[source_id]
    reader_allowed = brickset_reader and source_id in ('brickset-us', 'brickset-ca')
    if not source['permitted'] and not reader_allowed:
        raise PermissionError(source['reason'])
    url = source['url']
    deadline = time.monotonic() + 20
    for _ in range(4):
        if time.monotonic() >= deadline:
            raise TimeoutError('total retrieval deadline')
        u, address = validate_destination(url)
        connection = PinnedHTTPS(u.hostname, address)
        try:
            headers = {'User-Agent': 'PersonalFeedCompatibility/0.0', 'Accept-Encoding': 'identity',
                       'Accept': 'application/rss+xml, application/atom+xml, text/xml', **conditional}
            connection.request('GET', u.path + ('?' + u.query if u.query else ''), headers=headers)
            response = connection.getresponse()
            metadata = {k.lower(): v for k, v in response.getheaders()
                        if k.lower() in ('etag', 'last-modified', 'content-length', 'content-type', 'content-encoding', 'retry-after')}
            metadata.update(finalUrl=url, status=response.status)
            if response.status in (301, 302, 303, 307, 308):
                target = response.getheader('Location')
                # Exact endpoint only: do not cross markets or permission policies on redirects.
                if target != source['url']:
                    raise ValueError('redirect outside approved endpoint')
                url = target
                continue
            if response.status == 304:
                return 304, b'', metadata
            if response.status != 200:
                raise RetrievalError(response.status, metadata)
            if response.getheader('Content-Encoding', 'identity') != 'identity':
                raise ValueError('compressed responses unsupported')
            mime = response.getheader('Content-Type', '').split(';')[0].strip().lower()
            if mime not in ('text/xml', 'application/xml', 'application/rss+xml', 'application/atom+xml'):
                raise ValueError('unexpected content type')
            expected = response.getheader('Content-Length')
            if expected and (int(expected) < 0 or int(expected) > MAX_BYTES):
                raise ValueError('content length bound')
            chunks, size = [], 0
            while True:
                if time.monotonic() > deadline:
                    raise TimeoutError('total retrieval deadline')
                chunk = response.read1(min(16384, MAX_BYTES + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError('body size bound')
            if time.monotonic() > deadline:
                raise TimeoutError('total retrieval deadline')
            if expected is not None and size != int(expected):
                raise ValueError('truncated response')
            metadata['receivedBytes'] = size
            return 200, b''.join(chunks), metadata
        finally:
            connection.close()
    raise ValueError('redirect limit')


class Cache:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.directory / 'cache.json'

    @contextlib.contextmanager
    def locked(self):
        with (self.directory / 'cache.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('retrieval already in progress') from None
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def load(self):
        return json.loads(self.path.read_text()) if self.path.exists() else {'sources': {}}

    def save(self, state):
        data = json.dumps(state, indent=2, ensure_ascii=True)
        if len(data) > 10_000_000:
            raise ValueError('cache capacity exceeded')
        with tempfile.NamedTemporaryFile(mode='w', dir=self.directory, delete=False) as tmp:
            tmp.write(data)
            tmp.flush()
            import os
            os.fsync(tmp.fileno())
        Path(tmp.name).replace(self.path)

    def normalize(self, body, source_id, observed, synthetic):
        return parse_feed(body, source_id, observed, synthetic)

    def refresh(self, source_id, fetch=retrieve, now=None, synthetic=False):
        now = time.time() if now is None else now
        with self.locked():
            state = self.load()
            entry = state['sources'].setdefault(source_id, {'records': [], 'lastSuccessAt': None,
                                                          'lastAttemptAt': None, 'failures': 0})
            if now < entry.get('nextAttemptEpoch', 0):
                return 'backoff'
            if entry['lastSuccessAt'] and now - dt.datetime.fromisoformat(entry['lastSuccessAt']).timestamp() < TTL:
                return 'fresh'
            entry['lastAttemptAt'] = stamp(now)
            conditional = {}
            for header, key in [('If-None-Match', 'etag'), ('If-Modified-Since', 'last-modified')]:
                if entry.get(key):
                    conditional[header] = entry[key]
            try:
                status, body, metadata = fetch(source_id, conditional)
                if status == 304:
                    if not entry['lastSuccessAt'] or not conditional:
                        raise ValueError('unsolicited 304')
                    records = entry['records']
                elif status == 200:
                    incoming = self.normalize(body, source_id, stamp(now), synthetic)
                    old = {r['externalId']: r for r in entry['records']}
                    for record in incoming:
                        previous = old.get(record['externalId'])
                        if previous:
                            record['revision'] = previous['revision'] + (record['contentHash'] != previous['contentHash'])
                        old[record['externalId']] = record
                    records = list(old.values())
                    if len(records) > 5000:
                        raise ValueError('record capacity exceeded')
                else:
                    raise ValueError('unexpected response status')
                entry.update(records=records, lastSuccessAt=stamp(now), failures=0, error=None,
                             nextAttemptEpoch=0, httpStatus=status, httpMetadata=metadata)
                # 200 replaces validators; 304 can omit them.
                for key in ('etag', 'last-modified'):
                    entry[key] = metadata.get(key, entry.get(key) if status == 304 else None)
                outcome = 'updated'
            except Exception as exc:
                entry['failures'] += 1
                entry['error'] = str(exc)[:200]
                entry['nextAttemptEpoch'] = now + min(86400, 1800 * 2 ** min(entry['failures'] - 1, 6))
                retry = getattr(exc, 'metadata', {}).get('retry-after')
                if retry:
                    parsed = date(retry)
                    retry_epoch = now + int(retry) if retry.isdigit() and len(retry) < 10 else dt.datetime.fromisoformat(parsed).timestamp() if parsed else now
                    entry['nextAttemptEpoch'] = max(entry['nextAttemptEpoch'], retry_epoch)
                outcome = 'failed'
            self.save(state)
            return outcome


def render(state, *, brickset_reader=False):
    esc = lambda value: html.escape(str(value), quote=True)
    cards = []
    for source_id, entry in state['sources'].items():
        success = entry.get('lastSuccessAt')
        fresh = bool(success and time.time() - dt.datetime.fromisoformat(success).timestamp() < TTL)
        cards.append('<section><h2>' + esc(source_id) + '</h2><p>Freshness: ' + ('fresh' if fresh else 'stale / unknown')
                     + ' · Last success: ' + esc(success or 'never') + ' · Last attempt: '
                     + esc(entry.get('lastAttemptAt') or 'never') + '</p><p>' + esc(entry.get('error') or '') + '</p>')
        if not entry['records']:
            cards.append('<p>No cached records. ' + ('Retrieval failed or blocked.' if entry.get('error') else 'Valid empty feed or no successful retrieval yet.') + '</p>')
        for record in entry['records']:
            link = safe_link(record['canonicalUrl'])
            title = esc(record['title'])
            heading = '<a rel="noreferrer noopener" href="' + esc(link) + '">' + title + '</a>' if link else title
            cards.append('<article><h3>' + heading + '</h3><p>' + esc(record['market']) + ' · '
                         + esc(record['verification']) + ' · Availability: ' + esc(record['availability'])
                         + ' · ' + ('SYNTHETIC FIXTURE' if record['provenance']['synthetic'] else 'LIVE SOURCE')
                         + '</p><p>' + esc(record['summary']) + '</p><p>Published: '
                         + esc(record['publishedAt'] or 'unknown') + ' · Observed: ' + esc(record['observedAt'])
                         + '</p><p>Price / expiry: unknown · Revision ' + esc(record['revision']) + '</p></article>')
        cards.append('</section>')
    policy = ''.join('<li>' + esc(key) + (': Personal reader metadata only (temporary session).' if brickset_reader and key.startswith('brickset-') else ': BLOCKED — ' + esc(value['reason'])) + '</li>' for key, value in SOURCES.items())
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>V0.0 Feed compatibility</title><style>body{font:16px system-ui;margin:0;background:#f4f6f8;color:#142334}'
            'main{max-width:960px;margin:auto;padding:20px}article,section{background:white;padding:16px;margin:12px 0;'
            'border:1px solid #ccd4dd;border-radius:10px}h1{font-size:1.7rem}h3{font-size:1.1rem}'
            'p,a,li{overflow-wrap:anywhere}a{color:#164a87;display:inline-block;padding:10px 0;min-height:24px}li{margin:10px 0}@media(max-width:480px){main{padding:10px}section{padding:10px}}'
            '</style><main><h1>Feed compatibility · V0.0</h1><p>Local experiment · HOLD · No scheduled retrieval.</p>'
            '<ul>' + policy + '</ul>' + ''.join(cards) + '</main></html>').encode()


def handler_for(cache, *, brickset_reader=False):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != '/':
                self.send_error(404)
                return
            body = render(cache.load(), brickset_reader=brickset_reader)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['demo', 'live', 'serve'])
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    cache = Cache(ROOT / 'runtime' / ('live' if args.command == 'live' else 'synthetic'))
    if args.command == 'demo':
        for source in SOURCES:
            fixture = ROOT / 'fixtures' / ('atom.xml' if source == 'slickdeals-us' else 'rss.xml')
            print(source, cache.refresh(source, lambda *_: (200, fixture.read_bytes(), {}), synthetic=True))
    elif args.command == 'live':
        # No CLI permission override. Policy changes require a new documented permission review.
        for source in SOURCES:
            print(source, cache.refresh(source))
        raise SystemExit(2 if any(not s['permitted'] for s in SOURCES.values()) else 0)
    else:
        server = HTTPServer(('127.0.0.1', args.port), handler_for(cache))
        print(f'Local synthetic preview: http://127.0.0.1:{args.port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == '__main__':
    main()

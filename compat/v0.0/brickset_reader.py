"""V0.0.1: one private RSS-reader request per Brickset market; no raw archive.

Scope reviewed 2026-11-25 against Brickset's RSS invitation and robots guidance.
Default feedcompat policies remain disabled. No Slickdeals access, polling or API.
"""
import argparse
import copy
import json
import signal
import tempfile
import time
from html.parser import HTMLParser
from http.server import HTTPServer

import feedcompat as f

MARKETS = ('brickset-us', 'brickset-ca')


class Structure(HTMLParser):
    """Inspect structure in memory; never retain descriptions, tables or images."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = 0
        self.product_links = set()
        self.merchant_links = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.rows += 1
        if tag == 'a':
            href = f.safe_link(dict(attrs).get('href'))
            if href:
                u = f.urlsplit(href)
                if u.hostname == 'brickset.com' and u.path.startswith('/sets/'):
                    self.product_links.add(u.path)
                if u.hostname in ('amazon.com', 'www.amazon.com', 'amazon.ca', 'www.amazon.ca'):
                    self.merchant_links += 1


def inspect_records(body, source_id, observed, synthetic=False):
    # parse_feed validates XML before the structural inspection below.
    records = f.parse_feed(body, source_id, observed, synthetic)
    root = f.ET.fromstring(body.decode('utf-8-sig'))
    items = root.findall('./channel/item')
    samples = []
    for index, item in enumerate(items[:10], 1):
        description = item.findtext('description') or ''
        structure = Structure()
        structure.feed(description)
        samples.append({'sample': index, 'nativeIdPresent': bool(item.findtext('guid')),
                        'titlePresent': bool(item.findtext('title')),
                        'articleLinkPresent': bool(f.safe_link(item.findtext('link'))),
                        'publishedDateValid': f.date(item.findtext('pubDate')) is not None,
                        'tableRows': structure.rows, 'distinctProductLinks': len(structure.product_links),
                        'directMerchantLinks': structure.merchant_links,
                        'semantics': 'article-aggregate' if structure.rows > 2 or len(structure.product_links) > 1 else 'article-or-offer-unknown'})
    limited = copy.deepcopy(records[:10])
    # Retain minimum reader metadata; no summaries or price history.
    for row in limited:
        row['summary'] = ''
        row['verification'] = 'reported' if not synthetic else 'unverified'
        row['recordKind'] = 'article-or-offer-unknown'
        row['contentHash'] = f.digest({k: v for k, v in row.items()
                                       if k not in ('contentHash', 'observedAt', 'revision')})
    return limited, {'rawItemCount': len(items), 'normalizedItemCount': len(records),
                     'inspected': len(samples), 'cached': len(limited), 'samples': samples,
                     'offerRowsExtracted': 0, 'normalization': 'article-level; offer fields unknown'}


class ReaderCache(f.Cache):
    def __init__(self, directory, deadline_epoch):
        super().__init__(directory)
        self.deadline_epoch = deadline_epoch
        self.findings = {}

    def normalize(self, body, source_id, observed, synthetic):
        if source_id not in MARKETS or synthetic:
            raise ValueError('reader cache only accepts live Brickset metadata')
        rows, self.findings[source_id] = inspect_records(body, source_id, observed)
        return rows

    def load(self):
        state = super().load()
        if time.time() >= self.deadline_epoch:
            # Clear only this session's owned cache; no user cache is touched.
            empty = {'sources': {}}
            if state != empty:
                self.save(empty)
            return empty
        return state

    def save(self, state):
        for source, entry in state['sources'].items():
            if source not in MARKETS or len(entry['records']) > 10:
                raise ValueError('reader store boundary')
            for row in entry['records']:
                if row['provenance']['synthetic'] or row['summary'] or row['sourceId'] != source:
                    raise ValueError('mixed or excessive reader content')
        super().save(state)


def fetch_once(cache, budget, source, summaries):
    ledger = budget.load()
    if source in ledger['sources']:
        raise RuntimeError('Initial request already reserved for this handoff; no automatic refetch')
    ledger['sources'][source] = {'attemptAt': f.stamp(), 'endpoint': f.SOURCES[source]['url']}
    budget.save(ledger)  # Reserve before network; applies across runs/processes.

    def fetch(source_id, conditional):
        try:
            status, body, metadata = f.retrieve(source_id, conditional, brickset_reader=True)
        except Exception as exc:
            summaries[source_id] = {'checkedAt': f.stamp(), 'outcome': 'failed',
                                    'errorCategory': type(exc).__name__,
                                    'http': getattr(exc, 'metadata', {})}
            raise
        summaries[source_id] = {'checkedAt': f.stamp(), 'outcome': 'received', 'http': metadata,
                                'xmlEncoding': 'utf-8' if body.startswith(b'<?xml') and b'utf-8' in body[:120].lower() else 'not declared/other'}
        return status, body, metadata

    outcome = cache.refresh(source, fetch)
    summaries.setdefault(source, {'checkedAt': f.stamp(), 'outcome': outcome})
    summaries[source]['cacheOutcome'] = outcome
    summaries[source]['lastSuccessAt'] = cache.load()['sources'][source]['lastSuccessAt']
    if outcome == 'failed' and 'errorCategory' not in summaries[source]:
        summaries[source]['errorCategory'] = 'NormalizationError'
    if source in cache.findings:
        summaries[source]['findings'] = cache.findings[source]
    if outcome == 'updated':
        # Actual disk reload using a separate instance, no extra HTTP request.
        summaries[source]['diskReloadMatches'] = ReaderCache(cache.directory, cache.deadline_epoch).load() == cache.load()
    ledger['sources'][source]['result'] = summaries[source]
    budget.save(ledger)  # Structural counts/HTTP metadata only; no live titles or URLs beyond endpoints.
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serve', action='store_true', help='Preview only this temporary reader session')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--seconds', type=int, default=1800, help='Session lifetime, at most 1800 seconds')
    args = parser.parse_args()
    if not 1 <= args.seconds <= f.TTL:
        parser.error('session must be between 1 and 1800 seconds')
    runtime = f.ROOT / 'runtime'
    runtime.mkdir(exist_ok=True)
    budget = f.Cache(runtime / 'v001-request-budget')
    # Preserve any existing listener. Bind before reserving requests or fetching.
    server = HTTPServer(('127.0.0.1', args.port), f.BaseHTTPRequestHandler) if args.serve else None
    try:
        with budget.locked(), tempfile.TemporaryDirectory(prefix='v001-reader-', dir=runtime) as directory:
            deadline = time.time() + args.seconds
            cache = ReaderCache(directory, deadline)
            summaries = {}
            for source in MARKETS:
                fetch_once(cache, budget, source, summaries)
            print(json.dumps(summaries, indent=2), flush=True)
            if server:
                server.RequestHandlerClass = f.handler_for(cache, brickset_reader=True)
                server.timeout = 0.5
                print('Private loopback reader ready; no further source requests; automatic session cleanup.', flush=True)
                while time.time() < deadline:
                    server.handle_request()
    finally:
        if server:
            server.server_close()


if __name__ == '__main__':
    def stop(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        main()
    except KeyboardInterrupt:
        pass

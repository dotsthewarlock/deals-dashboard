"""Foreground-only coordinator. SQLite leases fence concurrent/stale completions."""
import json
import re
import uuid

from . import fixtures
from .normalize import articles, reference
from .transport import FetchError, NetworkFetcher


class Coordinator:
    def __init__(self, store, fetch=None):
        self.store = store
        self.fetch = fetch or (self.synthetic_fetch if store.mode == 'synthetic' else NetworkFetcher())

    def synthetic_fetch(self, source, conditional):
        return 200, fixtures.feed(source, self.store.clock()), {}

    def refresh(self, trigger, key=None):
        key = key or uuid.uuid4().hex
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}', key):
            raise ValueError('invalid-idempotency-key')
        profile = self.store.profile()
        if trigger not in ('open', 'foreground', 'manual'):
            raise ValueError('invalid-trigger')
        if trigger != 'manual' and profile['refreshPreference'] == 'manual':
            return {'outcome': 'skipped', 'reason': 'manual-only', 'sources': {}}
        from . import policy
        results = {}
        for source, config in policy.SOURCES.items():
            if source not in profile['sources'] or config['market'] not in profile['markets']:
                continue
            claim = self.store.claim(source, trigger, key)
            if 'token' not in claim:
                results[source] = claim
                continue
            validators = json.loads(claim['state']['validators'])
            conditional = {header: validators[field] for header, field in [('If-None-Match', 'etag'), ('If-Modified-Since', 'last-modified')] if field in validators}
            try:
                if self.store.mode != 'synthetic' and (self.store.mode != 'live' or not policy.live_allowed()):
                    raise FetchError('permission-denied')
                status, body, metadata = self.fetch(source, conditional)
                if status not in (200, 304):
                    raise FetchError('unexpected-status')
                directives = {part.strip().split('=', 1)[0].lower() for part in metadata.get('cache-control', '').split(',')}
                if self.store.mode == 'live' and directives & {'no-store', 'no-cache'}:
                    raise FetchError('source-cache-denied')
                rows = None if status == 304 else articles(body, source, reference.stamp(self.store.clock()), synthetic=self.store.mode == 'synthetic')[0]
                results[source] = self.store.complete(source, claim, rows, status, metadata)
            except FetchError as exc:
                results[source] = self.store.complete(source, claim, error=exc.category, retry_at=exc.retry_at)
            except Exception:
                results[source] = self.store.complete(source, claim, error='invalid-feed-or-store')
        outcomes = {row['outcome'] for row in results.values()}
        outcome = 'partial' if 'failed' in outcomes and len(outcomes) > 1 else 'failed' if 'failed' in outcomes else 'skipped' if not outcomes or outcomes <= {'skipped', 'in-flight'} else 'completed'
        return {'schemaVersion': 1, 'outcome': outcome, 'sources': results}

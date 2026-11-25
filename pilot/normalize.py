"""Reuse the pinned, bounded RSS/Atom parser as an unchanged reference."""
import hashlib
import importlib.util
import json
from pathlib import Path
from urllib.parse import urlsplit

from . import policy

spec = importlib.util.spec_from_file_location('_compat_reference', Path(__file__).resolve().parents[1] / 'compat/v0.0/feedcompat.py')
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


def source_link(value):
    """Display only HTTPS Brickset article links. Never fetch these links."""
    if not reference.safe_link(value) or '\\' in value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or parsed.netloc != 'brickset.com' or not parsed.path.startswith('/article/'):
        return None
    return value  # Preserve original query / affiliate parameters without rewriting.


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def articles(body, source_id, observed_at, synthetic):
    if source_id not in policy.SOURCES:
        raise ValueError('unknown-source')
    rows = reference.parse_feed(body, source_id, observed_at, synthetic)
    result, rejected = [], 0
    for row in rows:
        url = source_link(row['canonicalUrl'])
        native = row['provenance']['nativeIdentifier']
        if not url or (not native and row['externalId'].startswith('fallback:')):
            rejected += 1
            continue
        value = dict(schemaVersion=1, sourceId=source_id,
                     externalId=row['externalId'] if native else url, canonicalUrl=url,
                     title=row['title'], summary=None, market=policy.SOURCES[source_id]['market'],
                     recordKind='article', verification='unverified' if synthetic else 'reported',
                     availability='unknown', publishedAt=row['publishedAt'],
                     price=None, referencePrice=None, comparisonBasis=None, discount=None,
                     expiresAt=None, merchant=None, productId=None, promotion=None, restrictions=None,
                     provenance={'endpoint': policy.SOURCES[source_id]['url'], 'synthetic': synthetic,
                                 'identityBasis': 'native' if native else 'canonicalUrl'})
        value['contentHash'] = fingerprint(value)
        value.update(observedAt=observed_at, revision=1)
        result.append(value)
    # A nonempty unrecognizable feed must not replace last-good data as "empty".
    if rows and not result:
        raise ValueError('no-safe-article-records')
    return result[:policy.MAX_RECORDS], rejected + max(0, len(result) - policy.MAX_RECORDS)

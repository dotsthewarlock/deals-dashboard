"""Fixed source and retention policy. No runtime URL or permission overrides."""
from types import MappingProxyType

SOURCES = MappingProxyType({
    'brickset-ca': MappingProxyType({'market': 'CA', 'url': 'https://brickset.com/feed/amazon/ca'}),
    'brickset-us': MappingProxyType({'market': 'US', 'url': 'https://brickset.com/feed/amazon/us'}),
})
CONFIG_REVISION = 2
TTL = 1800
RETENTION = 7200  # Bounded private-reader rolling snapshot; no history or archive.
LIVE_DAILY_REQUESTS = 8  # Per source, rolling 24h; manual requests cannot bypass.
MAX_RECORDS = 50
MAX_BYTES = 1_000_000
HARD_TIMEOUT = 12
LEASE_SECONDS = 45
LIVE_READER_ALLOWED = True  # Narrow RSS reader interpretation; see docs/V0.1.1_SOURCE_POLICY.md.
LIVE_PERSISTENCE_ALLOWED = True  # Temporary minimal metadata only, not a general data licence.


def live_allowed():
    return LIVE_READER_ALLOWED and LIVE_PERSISTENCE_ALLOWED

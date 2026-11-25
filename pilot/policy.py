"""Fixed source and retention policy. No runtime URL or permission overrides."""
from types import MappingProxyType

SOURCES = MappingProxyType({
    'brickset-ca': MappingProxyType({'market': 'CA', 'url': 'https://brickset.com/feed/amazon/ca'}),
    'brickset-us': MappingProxyType({'market': 'US', 'url': 'https://brickset.com/feed/amazon/us'}),
})
CONFIG_REVISION = 1
TTL = 1800
RETENTION = 7200  # Synthetic rolling snapshot only; NOT a source retention license.
MAX_RECORDS = 50
MAX_BYTES = 1_000_000
HARD_TIMEOUT = 12
LEASE_SECONDS = 45
LIVE_READER_ALLOWED = False  # Recurring V0.1 retrieval rights not established.
LIVE_PERSISTENCE_ALLOWED = False


def live_allowed():
    return LIVE_READER_ALLOWED and LIVE_PERSISTENCE_ALLOWED

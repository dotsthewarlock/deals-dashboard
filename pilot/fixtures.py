"""Invented article metadata; these payloads never came from a real feed."""
from datetime import datetime, timezone

from . import policy


def feed(source_id, now):
    market = policy.SOURCES[source_id]['market']
    published = datetime.fromtimestamp(now, timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
    return (f'<rss version="2.0"><channel><title>SYNTHETIC {market}</title><item>'
            f'<guid>synthetic-{market}-article</guid><title>SYNTHETIC {market}: Galactic and City article roundup</title>'
            f'<link>https://brickset.com/article/synthetic-{market.lower()}?fixture=1</link>'
            f'<pubDate>{published}</pubDate><description>Invented multi-offer article. '
            'No price, stock or checkout claim.</description></item></channel></rss>').encode()

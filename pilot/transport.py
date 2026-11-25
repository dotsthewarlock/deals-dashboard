"""Denied-by-default live transport with a killable overall request boundary."""
import base64
import datetime as dt
import email.utils
import http.client
import ipaddress
import json
import socket
import ssl
import subprocess
import sys

from . import policy


class FetchError(Exception):
    def __init__(self, category, retry_at=None):
        super().__init__(category)
        self.category, self.retry_at = category, retry_at


def retry_time(value, now):
    try:
        if value.isdigit() and len(value) < 12:
            return now + int(value)
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo:
            return max(now, parsed.timestamp())
    except (ValueError, TypeError, OverflowError, AttributeError):
        pass
    return None


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address):
        super().__init__(host, timeout=5, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, 443), timeout=5)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def _https_get(source_id, conditional):
    """Worker-only implementation: source IDs only, no arbitrary URLs or proxies."""
    source = policy.SOURCES.get(source_id)
    if not source:
        raise FetchError('unknown-source')
    addresses = sorted({item[4][0] for item in socket.getaddrinfo('brickset.com', 443, type=socket.SOCK_STREAM)})
    if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
        raise FetchError('unsafe-destination')
    connection = PinnedHTTPS('brickset.com', addresses[0])
    try:
        headers = {'User-Agent': 'BricksetPrivatePilot/0.1', 'Accept-Encoding': 'identity',
                   'Accept': 'application/rss+xml, application/atom+xml, text/xml'}
        for name, value in conditional.items():
            if name not in ('If-None-Match', 'If-Modified-Since') or len(value) > 512 or '\r' in value or '\n' in value:
                raise FetchError('invalid-validator')
            headers[name] = value
        connection.request('GET', source['url'].removeprefix('https://brickset.com'), headers=headers)
        response = connection.getresponse()
        metadata = {key.lower(): value[:512] for key, value in response.getheaders()
                    if key.lower() in ('etag', 'last-modified', 'retry-after') and '\r' not in value and '\n' not in value}
        if 300 <= response.status < 400 and response.status != 304:
            raise FetchError('redirect-denied')  # Do not follow even same-host redirects.
        if response.status == 304:
            return 304, b'', metadata
        if response.status != 200:
            raise FetchError('http-' + str(response.status), retry_time(metadata.get('retry-after'), dt.datetime.now(dt.UTC).timestamp()))
        if response.getheader('Content-Encoding', 'identity') != 'identity':
            raise FetchError('encoding-denied')
        mime = response.getheader('Content-Type', '').split(';')[0].lower().strip()
        if mime not in ('application/rss+xml', 'application/atom+xml', 'text/xml', 'application/xml'):
            raise FetchError('invalid-content-type')
        length = response.getheader('Content-Length')
        if length is not None and (not length.isdigit() or int(length) > policy.MAX_BYTES):
            raise FetchError('size-bound')
        body = response.read(policy.MAX_BYTES + 1)
        if len(body) > policy.MAX_BYTES:
            raise FetchError('size-bound')
        if length is not None and len(body) != int(length):
            raise FetchError('truncated-body')
        return 200, body, metadata
    finally:
        connection.close()


class NetworkFetcher:
    def __call__(self, source_id, conditional):
        if source_id not in policy.SOURCES or not policy.live_allowed():
            raise FetchError('permission-denied')  # Before DNS / child process / HTTP.
        try:
            result = subprocess.run([sys.executable, '-m', 'pilot.transport', source_id],
                                    input=json.dumps(conditional), capture_output=True, text=True,
                                    timeout=policy.HARD_TIMEOUT, check=False)
        except subprocess.TimeoutExpired:
            # subprocess.run kills and waits for the owned worker on timeout.
            raise FetchError('overall-deadline') from None
        if result.returncode:
            raise FetchError('transport-failed')
        try:
            payload = json.loads(result.stdout)
            if 'error' in payload:
                raise FetchError(payload['error'], payload.get('retryAt'))
            body = base64.b64decode(payload['body'], validate=True)
            if len(body) > policy.MAX_BYTES:
                raise ValueError()
            return payload['status'], body, payload['metadata']
        except (ValueError, KeyError):
            raise FetchError('invalid-worker-result') from None


if __name__ == '__main__':
    # No CLI switch can enable the worker's permission policy.
    try:
        if not policy.live_allowed():
            raise FetchError('permission-denied')
        status, body, metadata = _https_get(sys.argv[1], json.loads(sys.stdin.read(2048)))
        print(json.dumps({'status': status, 'body': base64.b64encode(body).decode(), 'metadata': metadata}))
    except FetchError as exc:
        print(json.dumps({'error': exc.category, 'retryAt': exc.retry_at}))
    except Exception:
        print(json.dumps({'error': 'transport-failed'}))

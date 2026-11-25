"""Loopback-only authenticated development backend. No deployment mode."""
import argparse
import getpass
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import urlsplit

from .auth import Auth
from .refresh import Coordinator
from .store import Store, Conflict

STATIC = Path(__file__).resolve().parent / 'static'
CSP = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; manifest-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'"


class ReaderServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, store, port=8766, origin=None, coordinator=None):
        super().__init__(('127.0.0.1', port), Handler)
        self.store, self.auth = store, Auth(store)
        self.coordinator = coordinator or Coordinator(store)
        self.origin = origin or f'http://127.0.0.1:{self.server_port}'
        parsed = urlsplit(self.origin)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password
                or parsed.path or parsed.query or parsed.fragment
                or (parsed.scheme == 'http' and parsed.hostname not in ('127.0.0.1', 'localhost'))):
            self.server_close()
            raise ValueError('invalid-origin')
        self.hosts = {parsed.netloc, f'127.0.0.1:{self.server_port}', f'localhost:{self.server_port}'}
        self.secure = parsed.scheme == 'https'
        self.cookie = '__Host-pilot_session' if self.secure else 'pilot_session'


class Handler(BaseHTTPRequestHandler):
    server_version = 'PrivateReader'

    def log_message(self, *_):
        pass  # No passwords, cookies, owner data, private URLs or request bodies in logs.

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def reply(self, status, value, mime='application/json', cookie=None, clear=False):
        body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=True).encode()
        self.send_response(status)
        self.send_header('Content-Type', mime + ('; charset=utf-8' if mime != 'image/svg+xml' else ''))
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'private, no-store')
        self.send_header('Content-Security-Policy', CSP)
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        if clear:
            self.send_header('Clear-Site-Data', '"cache", "storage"')
        self.end_headers()
        self.wfile.write(body)

    def cookie_header(self, token='', age=3600):
        return f'{self.server.cookie}={token}; Path=/; Max-Age={age}; HttpOnly; SameSite=Strict' + ('; Secure' if self.server.secure else '')

    def token(self):
        value = self.headers.get('Cookie', '')
        if len(value) > 4096:
            return ''
        try:
            cookies = SimpleCookie(value)
            return cookies[self.server.cookie].value if self.server.cookie in cookies else ''
        except CookieError:
            return ''

    def body(self):
        length = self.headers.get('Content-Length', '')
        if (not length.isdigit() or not 0 < int(length) <= 16384 or self.headers.get('Transfer-Encoding')
                or self.headers.get('Content-Type', '').split(';')[0] != 'application/json'):
            raise ValueError('invalid-body')
        value = json.loads(self.rfile.read(int(length)))
        if not isinstance(value, dict):
            raise ValueError('object-body-required')
        return value

    def handle_request(self):
        try:
            if self.headers.get('Host') not in self.server.hosts:
                return self.reply(421, {'error': 'host-denied'})
            parsed = urlsplit(self.path)
            if parsed.query or parsed.scheme or parsed.netloc:
                return self.reply(400, {'error': 'query-scope-denied'})
            path, method = parsed.path, self.command
            assets = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
                      '/style.css': ('style.css', 'text/css'), '/manifest.webmanifest': ('manifest.webmanifest', 'application/manifest+json'),
                      '/icon.svg': ('icon.svg', 'image/svg+xml')}
            if method == 'GET' and path in assets:
                filename, mime = assets[path]
                return self.reply(200, (STATIC / filename).read_bytes(), mime)
            if not path.startswith('/api/'):
                return self.reply(404, {'error': 'not-found'})
            if method != 'GET' and self.headers.get('Origin') != self.server.origin:
                return self.reply(403, {'error': 'origin-denied'})
            if method == 'POST' and path == '/api/login':
                value = self.body()
                if set(value) != {'password'}:
                    raise ValueError('invalid-login')
                login = self.server.auth.login(value['password'])
                if login is None:
                    return self.reply(401, {'error': 'authentication-failed'})
                token, csrf = login
                return self.reply(200, {'owner': 'owner', 'csrf': csrf}, cookie=self.cookie_header(token))
            token = self.token()
            session = self.server.auth.session(token)
            if not session:
                return self.reply(401, {'error': 'authentication-required'})
            if method != 'GET':
                csrf = self.headers.get('X-CSRF-Token', '')
                if not csrf.isascii() or not secrets.compare_digest(csrf, session['csrf']):
                    return self.reply(403, {'error': 'csrf-denied'})
            if method == 'GET' and path == '/api/session':
                return self.reply(200, session)
            if method == 'GET' and path == '/api/profile':
                return self.reply(200, self.server.store.profile())
            if method == 'GET' and path == '/api/sources':
                return self.reply(200, {'schemaVersion': 1, 'sources': self.server.store.sources()})
            if method == 'GET' and path == '/api/deals':
                return self.reply(200, {'schemaVersion': 1, 'mode': self.server.store.mode,
                                        'articles': self.server.store.deals()})
            if method == 'PATCH' and path == '/api/profile':
                return self.reply(200, self.server.store.update_profile(self.body()))
            if method == 'POST' and path == '/api/refresh':
                value = self.body()
                if set(value) != {'trigger'}:
                    raise ValueError('invalid-refresh')
                key = self.headers.get('Idempotency-Key')
                if key is None:
                    raise ValueError('idempotency-key-required')
                return self.reply(200, self.server.coordinator.refresh(value['trigger'], key))
            if method == 'POST' and path == '/api/logout':
                self.body()
                self.server.auth.logout(token)
                return self.reply(200, {'loggedOut': True}, cookie=self.cookie_header('', 0), clear=True)
            return self.reply(404, {'error': 'not-found'})
        except Conflict:
            self.reply(409, {'error': 'profile-revision-conflict'})
        except (ValueError, TypeError, KeyError, OverflowError):
            self.reply(400, {'error': 'invalid-request'})
        except Exception:
            self.reply(500, {'error': 'internal-error'})
        finally:
            self.close_connection = True

    do_GET = handle_request
    do_POST = handle_request
    do_PATCH = handle_request
    do_PUT = handle_request
    do_DELETE = handle_request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'serve'))
    parser.add_argument('--data', type=Path, default=Path('.local/pilot.sqlite3'))
    parser.add_argument('--mode', choices=('synthetic', 'live-blocked'))
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--origin', help='Exact private HTTPS browser origin, or default loopback origin')
    args = parser.parse_args()
    store = Store(args.data, mode=args.mode)
    auth = Auth(store)
    if args.command == 'init':
        password = getpass.getpass('Choose local owner password (14+ characters): ')
        confirmation = getpass.getpass('Confirm password: ')
        if password != confirmation:
            parser.error('passwords-do-not-match')
        auth.setup(password)
        print('Local owner initialized. No external account was configured.')
    else:
        if not auth.configured():
            parser.error('initialize the local owner with the init command first')
        server = ReaderServer(store, args.port, args.origin)
        print(f'Local authenticated reader on loopback port {server.server_port}. Mode: {store.mode}. No polling.', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == '__main__':
    main()

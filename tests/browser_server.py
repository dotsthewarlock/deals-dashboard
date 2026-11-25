"""Disposable SYNTHETIC-only browser test server; never an owner setup tool."""
from pathlib import Path
import argparse
import signal
import ssl
import subprocess
import tempfile
from pilot.app import ReaderServer
from pilot.auth import Auth
from pilot.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--https', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='pilot-browser-synthetic-') as directory:
        store = Store(Path(directory) / 'test.sqlite3', mode='synthetic')
        Auth(store).setup('SYNTHETIC browser-only passphrase!')
        server = ReaderServer(store, port=0)
        if args.https:
            # Ephemeral self-signed local test TLS; no real origin/account setup.
            cert, key = Path(directory) / 'cert.pem', Path(directory) / 'key.pem'
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                            '-keyout', str(key), '-out', str(cert), '-days', '1',
                            '-subj', '/CN=localhost', '-addext', 'subjectAltName=IP:127.0.0.1'],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert, key)
            server.socket = context.wrap_socket(server.socket, server_side=True)
            server.origin = f'https://127.0.0.1:{server.server_port}'
            server.secure, server.cookie = True, '__Host-pilot_session'
        def stop(*_):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, stop)
        print(server.server_port, flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == '__main__':
    main()

"""Real local single-owner password authentication, hashed sessions and CSRF."""
import hashlib
import secrets


def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)


class Auth:
    def __init__(self, store):
        self.store = store

    def configured(self):
        with self.store.tx() as db:
            return bool(db.execute("SELECT id FROM owner WHERE id='owner'").fetchone())

    def setup(self, password):
        if not isinstance(password, str) or not 14 <= len(password) <= 1024:
            raise ValueError('password-must-be-14-to-1024-characters')
        salt = secrets.token_bytes(32)
        hashed = password_hash(password, salt)
        with self.store.tx() as db:
            if db.execute('SELECT id FROM owner').fetchone():
                raise ValueError('owner-already-configured')
            db.execute("INSERT INTO owner VALUES('owner',?,?)", (salt, hashed))

    def login(self, password):
        now = self.store.clock()
        with self.store.tx() as db:
            self.store.purge(db, now)
            guard = db.execute('SELECT * FROM login_guard WHERE id=1').fetchone()
            if guard['locked_until'] > now:
                return None
            owner = db.execute("SELECT * FROM owner WHERE id='owner'").fetchone()
            valid = (owner is not None and isinstance(password, str) and len(password) <= 1024
                     and secrets.compare_digest(owner['password_hash'], password_hash(password, owner['salt'])))
            if not valid:
                failures = guard['failures'] + 1
                lock = now + min(300, 2 ** min(failures, 9)) if failures >= 5 else 0
                db.execute('UPDATE login_guard SET failures=?,locked_until=? WHERE id=1', (failures, lock))
                return None
            db.execute('UPDATE login_guard SET failures=0,locked_until=0 WHERE id=1')
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            db.execute('INSERT INTO sessions VALUES(?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), csrf, now + 3600))
            db.execute('DELETE FROM sessions WHERE token_hash NOT IN (SELECT token_hash FROM sessions ORDER BY expires DESC,rowid DESC LIMIT 8)')
            return token, csrf

    def session(self, token):
        if not isinstance(token, str) or len(token) != 43 or not token.isascii():
            return None
        with self.store.tx() as db:
            self.store.purge(db, self.store.clock())
            row = db.execute('SELECT csrf FROM sessions WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            return {'owner': 'owner', 'csrf': row['csrf']} if row else None

    def logout(self, token):
        with self.store.tx() as db:
            db.execute('DELETE FROM sessions WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),))

"""One local SQLite store: owner state is separate from expiring source snapshots."""
from contextlib import closing, contextmanager
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from . import policy
from .normalize import reference

DEFAULT_PROFILE = {'schemaVersion': 1, 'name': 'Brickset reader', 'markets': ['CA', 'US'],
                   'sources': list(policy.SOURCES), 'include': [], 'exclude': [],
                   'lookbackDays': 7, 'refreshPreference': 'foreground', 'revision': 1}


class Conflict(Exception):
    pass


def validate_profile(value):
    if not isinstance(value, dict) or set(value) != set(DEFAULT_PROFILE):
        raise ValueError('invalid-profile-fields')
    if type(value['schemaVersion']) is not int or value['schemaVersion'] != 1 or type(value['revision']) is not int:
        raise ValueError('invalid-profile-version')
    if not isinstance(value['name'], str) or not 1 <= len(value['name'].strip()) <= 100:
        raise ValueError('invalid-profile-name')
    for key, allowed in [('markets', ('CA', 'US')), ('sources', policy.SOURCES)]:
        items = value[key]
        if not isinstance(items, list) or not all(isinstance(x, str) and x in allowed for x in items) or len(set(items)) != len(items):
            raise ValueError('invalid-profile-scope')
    for key in ('include', 'exclude'):
        if not isinstance(value[key], list) or len(value[key]) > 20 or not all(isinstance(x, str) and 1 <= len(x.strip()) <= 120 for x in value[key]):
            raise ValueError('invalid-keywords')
    if type(value['lookbackDays']) is not int or not 1 <= value['lookbackDays'] <= 90:
        raise ValueError('invalid-lookback')
    if value['refreshPreference'] not in ('manual', 'foreground'):
        raise ValueError('invalid-refresh-preference')
    return {**value, 'name': value['name'].strip()}


class Store:
    def __init__(self, path, mode=None, clock=time.time):
        self.path, self.clock = Path(path), clock
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with closing(self.connect()) as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1):
                raise ValueError('unsupported-schema-version')
            db.executescript('''
                PRAGMA journal_mode=WAL;
                PRAGMA secure_delete=ON;
                CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS owner(id TEXT PRIMARY KEY CHECK(id='owner'),salt BLOB NOT NULL,password_hash BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS profile(id TEXT PRIMARY KEY CHECK(id='owner'),data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,csrf TEXT NOT NULL,expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS login_guard(id INTEGER PRIMARY KEY CHECK(id=1),failures INTEGER NOT NULL,locked_until REAL NOT NULL);
                INSERT OR IGNORE INTO login_guard VALUES(1,0,0);
                CREATE TABLE IF NOT EXISTS source_state(
                    source_id TEXT PRIMARY KEY,config_rev INTEGER NOT NULL,
                    last_attempt REAL,last_success REAL,outcome TEXT NOT NULL DEFAULT 'never',
                    next_eligible REAL NOT NULL DEFAULT 0,failures INTEGER NOT NULL DEFAULT 0,
                    validators TEXT NOT NULL DEFAULT '{}',lease TEXT,lease_until REAL NOT NULL DEFAULT 0,
                    last_count INTEGER NOT NULL DEFAULT 0,last_error TEXT);
                CREATE TABLE IF NOT EXISTS articles(
                    source_id TEXT NOT NULL,article_id TEXT NOT NULL,data TEXT NOT NULL,
                    expires REAL NOT NULL,PRIMARY KEY(source_id,article_id));
                CREATE INDEX IF NOT EXISTS article_expiry ON articles(expires);
                CREATE TABLE IF NOT EXISTS runs(
                    run_id TEXT PRIMARY KEY,source_id TEXT NOT NULL,request_key TEXT NOT NULL,
                    trigger TEXT NOT NULL,config_rev INTEGER NOT NULL,started REAL NOT NULL,
                    ended REAL,outcome TEXT NOT NULL,error TEXT,count INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(source_id,request_key));
                PRAGMA user_version=1;
            ''')
            row = db.execute("SELECT value FROM meta WHERE key='mode'").fetchone()
            self.mode = row[0] if row else mode or 'synthetic'
            if self.mode not in ('synthetic', 'live-blocked') or (mode is not None and mode != self.mode):
                raise ValueError('store-mode-mismatch')
            db.execute("INSERT OR IGNORE INTO meta VALUES('mode',?)", (self.mode,))
            db.execute("INSERT OR IGNORE INTO profile VALUES('owner',?)", (json.dumps(DEFAULT_PROFILE),))
            for source in policy.SOURCES:
                db.execute('INSERT OR IGNORE INTO source_state(source_id,config_rev) VALUES(?,?)', (source, policy.CONFIG_REVISION))
        os.chmod(self.path, 0o600)
        # Recovery changes only this application's expired cache / expired leases.
        with self.tx() as db:
            self.purge(db, self.clock())

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA secure_delete=ON')
        return db

    @contextmanager
    def tx(self):
        db = self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def purge(self, db, now):
        db.execute('DELETE FROM articles WHERE expires<=?', (now,))
        db.execute('DELETE FROM sessions WHERE expires<=?', (now,))
        db.execute("UPDATE runs SET outcome='failed',error='lease-expired',ended=? WHERE outcome='in-flight' AND started<=?", (now, now - policy.LEASE_SECONDS))
        db.execute("UPDATE source_state SET outcome='failed',last_error='lease-expired',next_eligible=MAX(next_eligible,?) WHERE lease IS NOT NULL AND lease_until<=?", (now + policy.TTL, now))
        db.execute('UPDATE source_state SET lease=NULL,lease_until=0 WHERE lease_until<=?', (now,))
        db.execute('DELETE FROM runs WHERE ended IS NOT NULL AND run_id NOT IN (SELECT run_id FROM runs ORDER BY started DESC,rowid DESC LIMIT 100)')

    def profile(self):
        with self.tx() as db:
            return json.loads(db.execute("SELECT data FROM profile WHERE id='owner'").fetchone()[0])

    def update_profile(self, value):
        value = validate_profile(value)
        with self.tx() as db:
            current = json.loads(db.execute("SELECT data FROM profile WHERE id='owner'").fetchone()[0])
            if value['revision'] != current['revision']:
                raise Conflict('profile-revision-conflict')
            value = {**value, 'revision': current['revision'] + 1}
            db.execute("UPDATE profile SET data=? WHERE id='owner'", (json.dumps(value),))
        return value

    def sources(self):
        profile = self.profile()
        with self.tx() as db:
            now = self.clock()
            self.purge(db, now)
            result = []
            for state in db.execute('SELECT * FROM source_state ORDER BY source_id'):
                source = state['source_id']
                count = db.execute('SELECT count(*) FROM articles WHERE source_id=?', (source,)).fetchone()[0]
                expired = state['last_count'] > 0 and count == 0
                freshness = 'expired' if expired else 'unknown' if state['last_success'] is None else 'fresh' if now - state['last_success'] < policy.TTL else 'stale'
                result.append({'schemaVersion': 1, 'sourceId': source, **dict(policy.SOURCES[source]),
                               'mode': self.mode, 'permissionScope': 'synthetic-only; live recurring persistence blocked',
                               'enabled': source in profile['sources'] and policy.SOURCES[source]['market'] in profile['markets'],
                               'livePermitted': False, 'error': state['last_error'],
                               'configRevision': state['config_rev'], 'effectiveTtlSeconds': policy.TTL,
                               'retentionSeconds': policy.RETENTION, 'maxRecords': policy.MAX_RECORDS,
                               'lastAttemptAt': reference.stamp(state['last_attempt']) if state['last_attempt'] is not None else None,
                               'lastSuccessAt': reference.stamp(state['last_success']) if state['last_success'] is not None else None,
                               'nextEligibleAt': reference.stamp(state['next_eligible']) if state['next_eligible'] else None,
                               'outcome': state['outcome'], 'freshness': freshness, 'count': count,
                               'inFlight': bool(state['lease']), 'validators': json.loads(state['validators'])})
            return result

    def deals(self):
        profile = self.profile()
        now = self.clock()
        with self.tx() as db:
            self.purge(db, now)
            records = [json.loads(row[0]) for row in db.execute('SELECT data FROM articles ORDER BY source_id,article_id')]
        result = []
        for row in records:
            if row['sourceId'] not in profile['sources'] or row['market'] not in profile['markets']:
                continue
            title = row['title'].casefold()
            if profile['include'] and not any(term.casefold() in title for term in profile['include']):
                continue
            if any(term.casefold() in title for term in profile['exclude']):
                continue
            published = reference.date(row['publishedAt'])
            if published:
                from datetime import datetime
                if datetime.fromisoformat(published).timestamp() < now - profile['lookbackDays'] * 86400:
                    continue
            result.append(row)
        return result

    def claim(self, source, trigger, key):
        if source not in policy.SOURCES or trigger not in ('open', 'foreground', 'manual'):
            raise ValueError('invalid-refresh-scope')
        now, token, run_id = self.clock(), uuid.uuid4().hex, uuid.uuid4().hex
        with self.tx() as db:
            self.purge(db, now)
            prior = db.execute('SELECT * FROM runs WHERE source_id=? AND request_key=?', (source, key)).fetchone()
            if prior:
                return {'outcome': prior['outcome'], 'runId': prior['run_id'], 'reason': 'idempotent-replay'}
            state = db.execute('SELECT * FROM source_state WHERE source_id=?', (source,)).fetchone()
            reason = 'in-flight' if state['lease'] else 'not-eligible' if state['next_eligible'] > now else None
            if reason:
                db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?)', (run_id, source, key, trigger, state['config_rev'], now, now, 'skipped', reason, 0))
                return {'outcome': 'skipped', 'reason': reason, 'runId': run_id}
            db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,NULL,'in-flight',NULL,0)", (run_id, source, key, trigger, state['config_rev'], now))
            db.execute("UPDATE source_state SET lease=?,lease_until=?,last_attempt=?,outcome='in-flight',last_error=NULL WHERE source_id=?", (token, now + policy.LEASE_SECONDS, now, source))
            return {'token': token, 'runId': run_id, 'state': dict(state)}

    def complete(self, source, claim, rows=None, status=200, metadata=None, error=None, retry_at=None):
        now, metadata = self.clock(), metadata or {}
        with self.tx() as db:
            self.purge(db, now)
            state = db.execute('SELECT * FROM source_state WHERE source_id=?', (source,)).fetchone()
            if state['lease'] != claim['token'] or state['config_rev'] != claim['state']['config_rev']:
                return {'outcome': 'skipped', 'reason': 'superseded', 'runId': claim['runId']}
            old = {row['article_id']: json.loads(row['data']) for row in db.execute('SELECT * FROM articles WHERE source_id=?', (source,))}
            if status == 304 and not error:
                if not state['validators'] or state['validators'] == '{}' or (state['last_count'] and not old):
                    error = 'missing-304-baseline'
            if error:
                failures = state['failures'] + 1
                eligible = max(now + min(86400, policy.TTL * 2 ** min(failures - 1, 6)), retry_at or now)
                db.execute("UPDATE source_state SET lease=NULL,lease_until=0,failures=?,outcome='failed',next_eligible=?,last_error=? WHERE source_id=?", (failures, eligible, error, source))
                outcome, count = 'failed', len(old)
            else:
                if status == 304:
                    outcome, count = 'unchanged', len(old)
                else:
                    if self.mode != 'synthetic' or any(not row['provenance']['synthetic'] for row in rows):
                        raise ValueError('persistent-live-denied')
                    if len(rows) > policy.MAX_RECORDS:
                        raise ValueError('snapshot-bound')
                    changed = {key: row['contentHash'] for key, row in old.items()} != {row['externalId']: row['contentHash'] for row in rows}
                    outcome = 'success-empty' if not rows else 'changed' if changed else 'unchanged'
                    db.execute('DELETE FROM articles WHERE source_id=?', (source,))
                    for row in rows:
                        previous = old.get(row['externalId'])
                        row = {**row, 'revision': previous['revision'] + int(previous['contentHash'] != row['contentHash']) if previous else 1,
                               'firstSeenAt': previous['firstSeenAt'] if previous else reference.stamp(now),
                               'lastSeenAt': reference.stamp(now), 'observedAt': reference.stamp(now),
                               'cacheExpiresAt': reference.stamp(now + policy.RETENTION)}
                        db.execute('INSERT INTO articles VALUES(?,?,?,?)', (source, row['externalId'], json.dumps(row), now + policy.RETENTION))
                    count = len(rows)
                validators = json.loads(state['validators']) if status == 304 else {}
                validators.update({k: v for k, v in metadata.items() if k in ('etag', 'last-modified') and isinstance(v, str) and len(v) <= 512 and '\r' not in v and '\n' not in v})
                db.execute('UPDATE source_state SET lease=NULL,lease_until=0,failures=0,last_success=?,outcome=?,next_eligible=?,validators=?,last_count=?,last_error=NULL WHERE source_id=?',
                           (now, outcome, now + policy.TTL, json.dumps(validators), count, source))
            db.execute('UPDATE runs SET ended=?,outcome=?,error=?,count=? WHERE run_id=?', (now, outcome, error, count, claim['runId']))
            return {'outcome': outcome, 'error': error, 'count': count, 'runId': claim['runId']}

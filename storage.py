"""
Profile storage backed by SQLite.

Replaces the old one-JSON-file-per-profile layout (profiles/<id>.json), which
had no locking (two concurrent saves could clobber each other) and no
atomicity. SQLite gives us a single file with real transactions. On first
run, any pre-existing profiles/*.json files are imported automatically so
nobody loses data upgrading from the old format.
"""
import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime

BASE_DIR = os.path.dirname(__file__)
# Overridable so tests (and anyone running multiple instances) can point at
# an isolated database instead of the user's real profiles.db.
DB_PATH = os.environ.get('CVWIZARD_DB_PATH') or os.path.join(BASE_DIR, 'profiles.db')
LEGACY_PROFILES_DIR = os.path.join(BASE_DIR, 'profiles')

PROFILE_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,64}$')


def valid_profile_id(profile_id):
    return bool(profile_id) and bool(PROFILE_ID_RE.match(profile_id))


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                cv_name TEXT,
                template TEXT,
                updated TEXT,
                data TEXT NOT NULL
            )
        ''')
    _migrate_legacy_json()


def _migrate_legacy_json():
    """One-time import of profiles/*.json from the pre-SQLite storage format."""
    if not os.path.isdir(LEGACY_PROFILES_DIR):
        return
    with _conn() as conn:
        existing = {row['id'] for row in conn.execute('SELECT id FROM profiles')}
        for fname in sorted(os.listdir(LEGACY_PROFILES_DIR)):
            if not fname.endswith('.json'):
                continue
            profile_id = fname[:-5]
            if profile_id in existing or not valid_profile_id(profile_id):
                continue
            path = os.path.join(LEGACY_PROFILES_DIR, fname)
            try:
                with open(path, encoding='utf-8') as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            meta = data.get('_meta', {})
            conn.execute(
                'INSERT INTO profiles (id, name, cv_name, template, updated, data) VALUES (?,?,?,?,?,?)',
                (profile_id, meta.get('profile_name', 'Sin nombre'),
                 data.get('personal', {}).get('name', ''),
                 data.get('template', 'clasica_azul'),
                 meta.get('updated', ''), json.dumps(data, ensure_ascii=False)))
            try:
                os.rename(path, path + '.imported')
            except OSError:
                pass


def list_profiles():
    with _conn() as conn:
        rows = conn.execute(
            'SELECT id, name, cv_name, template, updated FROM profiles ORDER BY updated DESC'
        ).fetchall()
    return [dict(r) for r in rows]


def get_profile(profile_id):
    if not valid_profile_id(profile_id):
        return None
    with _conn() as conn:
        row = conn.execute('SELECT data FROM profiles WHERE id = ?', (profile_id,)).fetchone()
    return json.loads(row['data']) if row else None


def save_profile(data, profile_id=None, profile_name='Mi CV'):
    profile_id = profile_id if valid_profile_id(profile_id) else str(uuid.uuid4())[:8]
    updated = datetime.now().strftime('%d/%m/%Y %H:%M')
    data = dict(data)
    data['_meta'] = {'profile_name': profile_name, 'updated': updated}
    with _conn() as conn:
        conn.execute('''
            INSERT INTO profiles (id, name, cv_name, template, updated, data)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, cv_name=excluded.cv_name,
                template=excluded.template, updated=excluded.updated, data=excluded.data
        ''', (profile_id, profile_name, data.get('personal', {}).get('name', ''),
              data.get('template', 'clasica_azul'), updated, json.dumps(data, ensure_ascii=False)))
    return profile_id, profile_name


def delete_profile(profile_id):
    if not valid_profile_id(profile_id):
        return
    with _conn() as conn:
        conn.execute('DELETE FROM profiles WHERE id = ?', (profile_id,))

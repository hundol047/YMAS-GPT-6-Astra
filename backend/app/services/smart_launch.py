"""SMART App Launch (EHR launch) scaffold: GET /smart/launch?iss=...&launch=... is the URL an EMR
opens SynexAgent with, carrying the FHIR server base (iss) and an opaque launch token the EMR
expects back during token exchange so it can hand over patient context.

This builds a spec-shaped authorization redirect with PKCE (code_verifier/code_challenge, state)
and a callback that exchanges the code for a token. It has NOT been exercised against a real EMR's
SMART launcher or a real FHIR authorization server -- there isn't one reachable here. Verified here
only via unit tests that the redirect URL and PKCE parameters are constructed correctly
(backend/tests/test_cds_hooks.py); the actual authorization round-trip is unverified.

State is kept in one of two backends, chosen at import time:

- SYNEX_REDIS_URL set: `_RedisLaunchStore`, backed by a real Redis instance (a launch's state is
  shared by every worker process/replica that points at the same Redis, and each entry expires on
  its own after LAUNCH_TTL_SECONDS -- no cleanup job needed). This is the one a real multi-worker
  deployment should use; verified here against a real `redis-server` process
  (backend/tests/test_smart_launch_redis.py), not just a mock.
- otherwise: `_LaunchStore`, a local SQLite file (default backend/data/smart_launch.sqlite3,
  override with SYNEX_SMART_LAUNCH_PATH). Fine for a single-instance demo deployment and survives a
  process restart there, but does NOT survive across multiple worker processes/replicas sharing no
  filesystem -- this is the one real limitation left once SYNEX_REDIS_URL is set: without it, a
  multi-worker deployment still needs Redis (or a real shared DB) to keep an in-flight SMART launch
  visible to whichever worker handles the callback.
"""
import base64, contextvars, hashlib, json, os, secrets, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import httpx

# Set by main.py's smart_session_context middleware from the synex_session HttpOnly cookie, for
# the lifetime of one request -- lets emr_adapter.SmartSessionTokenProvider find "this request's
# SMART session" without threading a session_id through every adapter.get(pid) call site. Never
# holds a token itself, only an opaque session_id (same thing the browser cookie carries).
CURRENT_SESSION_ID: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('current_smart_session_id', default=None)

_DEFAULT_LAUNCH_DB = Path(__file__).resolve().parents[2] / 'data' / 'smart_launch.sqlite3'
LAUNCH_TTL_SECONDS = 600  # generous for a browser auth redirect round-trip; not a security boundary


class _LaunchStore:
    def __init__(self, path=None):
        self.path = str(path or os.getenv('SYNEX_SMART_LAUNCH_PATH', _DEFAULT_LAUNCH_DB))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS launches (state TEXT PRIMARY KEY, code_verifier TEXT NOT NULL, '
                       'iss TEXT NOT NULL, launch TEXT NOT NULL, redirect_uri TEXT NOT NULL, created_at TEXT NOT NULL)')

    def _connect(self):
        return sqlite3.connect(self.path, timeout=15)

    def put(self, state, data):
        with self._connect() as db:
            db.execute('INSERT OR REPLACE INTO launches VALUES (?,?,?,?,?,?)',
                       (state, data['code_verifier'], data['iss'], data['launch'], data['redirect_uri'],
                        datetime.now(timezone.utc).isoformat()))
            # Opportunistic TTL cleanup -- no background job, just sweep expired rows on every write.
            db.execute("DELETE FROM launches WHERE created_at < datetime('now', ?)", (f'-{LAUNCH_TTL_SECONDS} seconds',))

    def pop(self, state):
        with self._connect() as db:
            row = db.execute('SELECT code_verifier, iss, launch, redirect_uri FROM launches WHERE state=?', (state,)).fetchone()
            if row:
                db.execute('DELETE FROM launches WHERE state=?', (state,))
        return {'code_verifier': row[0], 'iss': row[1], 'launch': row[2], 'redirect_uri': row[3]} if row else None


class _RedisLaunchStore:
    """Real multi-worker-safe launch state: every worker/replica pointed at the same Redis sees the
    same in-flight launches, so a SMART callback handled by a different process than the one that
    started the launch still finds its PKCE code_verifier. Verified against a real local
    `redis-server`, not a mock (backend/tests/test_smart_launch_redis.py)."""
    def __init__(self, url):
        import redis
        self._r = redis.Redis.from_url(url, decode_responses=True)

    def _key(self, state):
        return f'synex:smart_launch:{state}'

    def put(self, state, data):
        self._r.set(self._key(state), json.dumps(data), ex=LAUNCH_TTL_SECONDS)

    def pop(self, state):
        key = self._key(state)
        pipe = self._r.pipeline()
        pipe.get(key)
        pipe.delete(key)
        raw, _ = pipe.execute()
        return json.loads(raw) if raw else None


def _build_launch_store():
    redis_url = os.getenv('SYNEX_REDIS_URL')
    return _RedisLaunchStore(redis_url) if redis_url else _LaunchStore()


_LAUNCHES = _build_launch_store()


def _pkce_pair():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    return verifier, challenge


def discover_authorize_endpoint(iss: str, transport=None) -> str:
    try:
        r = httpx.Client(transport=transport, timeout=10).get(f'{iss.rstrip("/")}/.well-known/smart-configuration')
        r.raise_for_status()
        return r.json()['authorization_endpoint']
    except Exception:
        return f'{iss.rstrip("/")}/oauth2/authorize'  # conservative fallback; real deployments should verify


def build_authorize_redirect(iss: str, launch: str, client_id: str, redirect_uri: str, scope: str, transport=None) -> str:
    state = secrets.token_urlsafe(16)
    verifier, challenge = _pkce_pair()
    _LAUNCHES.put(state, {'code_verifier': verifier, 'iss': iss, 'launch': launch, 'redirect_uri': redirect_uri})
    authorize_endpoint = discover_authorize_endpoint(iss, transport=transport)
    params = {
        'response_type': 'code', 'client_id': client_id, 'redirect_uri': redirect_uri,
        'launch': launch, 'scope': scope, 'state': state, 'aud': iss,
        'code_challenge': challenge, 'code_challenge_method': 'S256',
    }
    return f'{authorize_endpoint}?{httpx.QueryParams(params)}'


def exchange_code(state: str, code: str, client_id: str, transport=None) -> dict:
    launch = _LAUNCHES.pop(state)
    if not launch:
        raise KeyError('Unknown or expired launch state')
    token_endpoint = discover_authorize_endpoint(launch['iss'], transport=transport).replace('/authorize', '/token')
    r = httpx.Client(transport=transport, timeout=10).post(token_endpoint, data={
        'grant_type': 'authorization_code', 'code': code, 'redirect_uri': launch['redirect_uri'],
        'client_id': client_id, 'code_verifier': launch['code_verifier'],
    })
    r.raise_for_status()
    # 'iss' is not part of the token response itself, but main.py's /smart/callback needs it (to
    # build a SessionStore entry) and it only ever lived in the now-popped launch state -- add it
    # rather than making the caller look it up separately. Real token responses don't use this key
    # (SMART/OAuth2 token responses are access_token/token_type/expires_in/patient/scope/...), so
    # this can't collide with a real field.
    return {**r.json(), 'iss': launch['iss']}


# --- Post-launch session: what /smart/callback creates so the SPA can know "which patient is this
# browser's SMART context" WITHOUT the access token ever reaching the browser or a log line. ------
SESSION_TTL_SECONDS = 8 * 3600  # a clinical shift; not a security boundary, just a sane expiry


class _SessionStore:
    """SQLite-backed by default (same single-instance-demo caveat as _LaunchStore above); set
    SYNEX_REDIS_URL to share sessions across workers, same as launch state.

    SECURITY BOUNDARY: `access_token` is written here and nowhere else. `context()` -- the only
    method main.py's /session/context endpoint or any audit.record() call may use -- returns
    ONLY {patient_id, iss}, never the token. `token_for()` is deliberately separate and prefixed
    for internal use, reserved for a future authenticated FHIR client call from inside this
    service; no current endpoint handler calls it, and none should ever serialize its result into
    an HTTP response, a log message, or an audit detail dict. This class is intentionally the ONLY
    place a token touches storage, so swapping it for a real secret manager / KMS-backed session
    store later (a real deployment should) means changing this one class, not call sites.

    EXPIRY: a session older than SESSION_TTL_SECONDS is never returned by context() or token_for()
    -- both check the row's age on every read (not just opportunistically on the next put(), which
    used to mean an old session already in the table stayed readable until the next unrelated
    write happened to sweep it). An expired row is deleted the moment it's read, not left behind
    for the next put()'s sweep. Age is tracked as a Unix timestamp (REAL), not an ISO string, so
    expiry is a plain numeric comparison rather than parsing/relying on SQLite's date functions.

    Note for local dev: this changed the table's `created_at` TEXT column to `created_at_ts` REAL.
    A pre-existing smart_session.sqlite3 from before this change has the old schema and won't be
    migrated automatically (CREATE TABLE IF NOT EXISTS is a no-op against it) -- delete the file
    (or point SYNEX_SESSION_PATH at a fresh path) rather than run against a stale schema.
    """
    def __init__(self, path=None):
        self.path = str(path or os.getenv('SYNEX_SESSION_PATH', Path(__file__).resolve().parents[2] / 'data' / 'smart_session.sqlite3'))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, '
                       'iss TEXT NOT NULL, access_token TEXT NOT NULL, created_at_ts REAL NOT NULL)')

    def _connect(self):
        return sqlite3.connect(self.path, timeout=15)

    def put(self, session_id, *, patient_id, iss, access_token):
        with self._connect() as db:
            db.execute('INSERT OR REPLACE INTO sessions VALUES (?,?,?,?,?)',
                       (session_id, patient_id, iss, access_token, time.time()))
            db.execute('DELETE FROM sessions WHERE created_at_ts < ?', (time.time() - SESSION_TTL_SECONDS,))

    def _read_if_not_expired(self, db, session_id, columns):
        row = db.execute(f'SELECT {columns}, created_at_ts FROM sessions WHERE session_id=?', (session_id,)).fetchone()
        if row is None:
            return None
        *values, created_at_ts = row
        if time.time() - created_at_ts >= SESSION_TTL_SECONDS:
            db.execute('DELETE FROM sessions WHERE session_id=?', (session_id,))
            return None
        return values

    def context(self, session_id):
        with self._connect() as db:
            values = self._read_if_not_expired(db, session_id, 'patient_id, iss')
        return {'patient_id': values[0], 'iss': values[1]} if values else None

    def token_for(self, session_id):  # internal use only -- see class docstring
        with self._connect() as db:
            values = self._read_if_not_expired(db, session_id, 'access_token')
        return values[0] if values else None


class _RedisSessionStore:
    """Same SESSION_TTL_SECONDS auto-expiry and token-access-boundary contract as _SessionStore,
    backed by Redis so every worker/replica sees the same session. Not yet covered by a real
    redis-server test the way _RedisLaunchStore is (see test_smart_launch_redis.py) -- add one
    there if this path is put into real use."""
    def __init__(self, url):
        import redis
        self._r = redis.Redis.from_url(url, decode_responses=True)

    def _key(self, session_id):
        return f'synex:smart_session:{session_id}'

    def put(self, session_id, *, patient_id, iss, access_token):
        self._r.set(self._key(session_id), json.dumps({'patient_id': patient_id, 'iss': iss, 'access_token': access_token}),
                     ex=SESSION_TTL_SECONDS)

    def context(self, session_id):
        raw = self._r.get(self._key(session_id))
        if not raw:
            return None
        d = json.loads(raw)
        return {'patient_id': d['patient_id'], 'iss': d['iss']}

    def token_for(self, session_id):  # internal use only -- see _SessionStore's class docstring
        raw = self._r.get(self._key(session_id))
        return json.loads(raw)['access_token'] if raw else None


def _build_session_store():
    redis_url = os.getenv('SYNEX_REDIS_URL')
    return _RedisSessionStore(redis_url) if redis_url else _SessionStore()


SESSIONS = _build_session_store()


def create_session(*, patient_id, iss, access_token) -> str:
    session_id = secrets.token_urlsafe(24)
    SESSIONS.put(session_id, patient_id=patient_id, iss=iss, access_token=access_token)
    return session_id

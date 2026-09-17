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
import base64, contextvars, hashlib, ipaddress, json, os, secrets, socket, sqlite3, time
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit
import httpx

# Set by main.py's smart_session_context middleware from the synex_session HttpOnly cookie, for
# the lifetime of one request -- lets emr_adapter.SmartSessionTokenProvider find "this request's
# SMART session" without threading a session_id through every adapter.get(pid) call site. Never
# holds a token itself, only an opaque session_id (same thing the browser cookie carries).
CURRENT_SESSION_ID: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('current_smart_session_id', default=None)

_DEFAULT_LAUNCH_DB = Path(__file__).resolve().parents[2] / 'data' / 'smart_launch.sqlite3'
# Generous for a browser auth redirect round-trip, but short enough that a stolen/logged `state`
# value stops being useful quickly -- see Phase 2 of the round-4 spec. Configurable because a real
# deployment may want this shorter; not itself a substitute for TLS/short-lived codes.
LAUNCH_TTL_SECONDS = int(os.getenv('SMART_LAUNCH_STATE_TTL_SECONDS', '600'))


class _LaunchStore:
    """SQLite-backed by default (see module docstring for the Redis alternative).

    EXPIRY: mirrors _SessionStore below -- created_at_ts is a Unix timestamp (REAL), and pop()
    checks the row's age on every read, not just opportunistically on the next put()'s sweep. An
    expired state is deleted the moment it's read and NEVER returned, so it can never be used for
    token exchange even if the row was still physically present in the table when pop() was called.

    Note for local dev: this changed the table's `created_at` TEXT column to `created_at_ts` REAL
    and added a `token_endpoint` column (see discover_smart_configuration() below) -- a pre-existing
    smart_launch.sqlite3 from before this change has the old schema and won't be migrated
    automatically (CREATE TABLE IF NOT EXISTS is a no-op against it); delete the file (or point
    SYNEX_SMART_LAUNCH_PATH at a fresh path) rather than run against a stale schema.
    """
    def __init__(self, path=None):
        self.path = str(path or os.getenv('SYNEX_SMART_LAUNCH_PATH', _DEFAULT_LAUNCH_DB))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS launches (state TEXT PRIMARY KEY, code_verifier TEXT NOT NULL, '
                       'iss TEXT NOT NULL, launch TEXT NOT NULL, redirect_uri TEXT NOT NULL, '
                       'token_endpoint TEXT NOT NULL, created_at_ts REAL NOT NULL)')

    def _connect(self):
        return sqlite3.connect(self.path, timeout=15)

    def put(self, state, data):
        with self._connect() as db:
            db.execute('INSERT OR REPLACE INTO launches VALUES (?,?,?,?,?,?,?)',
                       (state, data['code_verifier'], data['iss'], data['launch'], data['redirect_uri'],
                        data['token_endpoint'], time.time()))
            # Opportunistic extra cleanup -- pop() is what actually enforces TTL on every read; this
            # just keeps abandoned (never-completed) launches from accumulating in the table forever.
            db.execute('DELETE FROM launches WHERE created_at_ts < ?', (time.time() - LAUNCH_TTL_SECONDS,))

    def pop(self, state):
        with self._connect() as db:
            row = db.execute('SELECT code_verifier, iss, launch, redirect_uri, token_endpoint, created_at_ts '
                              'FROM launches WHERE state=?', (state,)).fetchone()
            if row is None:
                return None
            db.execute('DELETE FROM launches WHERE state=?', (state,))  # single-use regardless of TTL outcome
        *values, created_at_ts = row
        if time.time() - created_at_ts >= LAUNCH_TTL_SECONDS:
            return None  # expired -- never usable for token exchange, even though it was just deleted above
        return {'code_verifier': values[0], 'iss': values[1], 'launch': values[2],
                'redirect_uri': values[3], 'token_endpoint': values[4]}


class _RedisLaunchStore:
    """Real multi-worker-safe launch state: every worker/replica pointed at the same Redis sees the
    same in-flight launches, so a SMART callback handled by a different process than the one that
    started the launch still finds its PKCE code_verifier. Verified against a real local
    `redis-server`, not a mock (backend/tests/test_smart_launch_redis.py). Expiry is Redis's own
    `ex=` TTL -- a get past that point returns nothing, so there's no separate age check to write
    (unlike the SQLite backend above, which has to track and check created_at_ts itself)."""
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


# --- Issuer validation / SSRF defense --------------------------------------------------------
# /smart/launch?iss=<...> is fully attacker-controlled (any EMR-shaped link can point it anywhere),
# and until this check ran the old code made an outbound `.well-known` request to that URL with
# zero validation -- a textbook SSRF: an attacker-supplied iss could point at an internal service
# (http://169.254.169.254/, http://10.x.x.x/, a coworker's laptop on the hospital LAN) and this
# server would dutifully fetch it. validate_smart_issuer() MUST run, and MUST pass, before any
# HTTP request touches an iss-derived URL -- see discover_smart_configuration() below.
def _normalize_issuer(iss: str) -> str:
    parts = urlsplit(iss.strip())
    host = (parts.hostname or '').lower()
    port = f':{parts.port}' if parts.port else ''
    path = parts.path.rstrip('/')
    return f'{parts.scheme.lower()}://{host}{port}{path}'  # fragment/query intentionally dropped


def _resolve_ips(hostname: str) -> list:
    """Best-effort DNS-rebinding defense: resolve `hostname` once and let the caller reject any
    private/internal result. This closes the common case (a public-looking hostname that resolves
    straight to an internal address) but -- documented honestly, not claimed as airtight -- it does
    NOT pin the resolved IP for the actual request that follows, so a narrow TOCTOU window remains
    between this check and httpx's own connect-time resolution (closing that fully would need a
    custom transport that connects to the checked IP directly with the original Host/SNI, which
    this prototype does not implement). Resolution failure (unknown host, no network) is treated as
    "nothing to check" rather than blocked -- the discovery request that follows will simply fail to
    connect on its own in that case."""
    try:
        return list({info[4][0] for info in socket.getaddrinfo(hostname, None)})
    except (socket.gaierror, OSError, UnicodeError):
        return []


def _is_private_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified


def validate_smart_issuer(iss: str) -> None:
    """Raises ValueError (never makes any network call itself) if `iss` must not be used for SMART
    discovery. Baseline for production SMART mode (Phase 4 of the round-4 spec):
      1. https only (SYNEX_SMART_ALLOW_INSECURE_LOCALHOST=true carves out an explicit localhost
         escape hatch for local dev against a fake/test IdP -- production deployments leave it unset).
      2. must be in SYNEX_SMART_TRUSTED_ISSUERS (comma-separated) when that env var is set; an unset
         allowlist is permissive (demo-mode default) but every other check below still applies.
      3. no embedded username/password.
      4. the host itself, and (best-effort) what it resolves to, must not be a private/loopback/
         link-local/reserved address -- see _resolve_ips()'s docstring for this check's real scope.
    """
    parts = urlsplit((iss or '').strip())
    if parts.username or parts.password:
        raise ValueError('SMART issuer URL must not embed credentials')
    hostname = (parts.hostname or '').lower()
    if not hostname:
        raise ValueError('SMART issuer URL must include a host')
    allow_insecure_localhost = os.getenv('SYNEX_SMART_ALLOW_INSECURE_LOCALHOST', 'false').lower() == 'true'
    is_localhost = hostname in ('localhost', '127.0.0.1', '::1') or hostname.endswith('.localhost')
    if is_localhost and allow_insecure_localhost:
        return  # explicit local-dev escape hatch only -- never the default
    if parts.scheme.lower() != 'https':
        raise ValueError(f'SMART issuer must use https (got scheme {parts.scheme!r})')
    trusted = {_normalize_issuer(u) for u in os.getenv('SYNEX_SMART_TRUSTED_ISSUERS', '').split(',') if u.strip()}
    if trusted and _normalize_issuer(iss) not in trusted:
        raise ValueError(f'SMART issuer {iss!r} is not present in SYNEX_SMART_TRUSTED_ISSUERS')
    try:
        candidate_ips = [str(ipaddress.ip_address(hostname))]  # iss host is itself a literal IP
    except ValueError:
        candidate_ips = _resolve_ips(hostname)
    for ip_str in candidate_ips:
        if _is_private_ip(ip_str):
            raise ValueError(f'SMART issuer host {hostname!r} resolves to a private/internal address ({ip_str})')


def discover_smart_configuration(iss: str, transport=None) -> dict:
    """Standard SMART discovery: GET {iss}/.well-known/smart-configuration, reading
    authorization_endpoint and token_endpoint INDEPENDENTLY -- see Phase 3 of the round-4 spec. The
    old discover_authorize_endpoint() derived a token endpoint via
    `authorization_endpoint.replace('/authorize', '/token')`, which is not part of the SMART spec
    and silently breaks against any real EHR whose two endpoints don't share that exact URL shape
    (e.g. 'https://ehr.example/oauth/a' + 'https://auth.example/token-exchange'). Both fields are
    now required straight from the discovery document; missing either is a hard failure, not a
    guessed fallback.

    validate_smart_issuer() runs FIRST, before this makes any outbound request -- see its docstring."""
    validate_smart_issuer(iss)
    r = httpx.Client(transport=transport, timeout=10).get(f'{iss.rstrip("/")}/.well-known/smart-configuration')
    r.raise_for_status()
    doc = r.json()
    authorization_endpoint, token_endpoint = doc.get('authorization_endpoint'), doc.get('token_endpoint')
    if not authorization_endpoint or not token_endpoint:
        raise ValueError('SMART discovery document is missing authorization_endpoint and/or token_endpoint')
    return {'authorization_endpoint': authorization_endpoint, 'token_endpoint': token_endpoint,
            'capabilities': doc.get('capabilities', []), 'scopes_supported': doc.get('scopes_supported', [])}


def build_authorize_redirect(iss: str, launch: str, client_id: str, redirect_uri: str, scope: str, transport=None) -> str:
    config = discover_smart_configuration(iss, transport=transport)  # validated + discovered BEFORE any state is stored
    state = secrets.token_urlsafe(16)
    verifier, challenge = _pkce_pair()
    # token_endpoint is captured HERE, once, and stored with the launch -- exchange_code() below
    # reads it back rather than re-deriving or re-discovering it, so the callback always uses the
    # exact endpoint this authorize request was actually built against.
    _LAUNCHES.put(state, {'code_verifier': verifier, 'iss': iss, 'launch': launch, 'redirect_uri': redirect_uri,
                           'token_endpoint': config['token_endpoint']})
    params = {
        'response_type': 'code', 'client_id': client_id, 'redirect_uri': redirect_uri,
        'launch': launch, 'scope': scope, 'state': state, 'aud': iss,
        'code_challenge': challenge, 'code_challenge_method': 'S256',
    }
    return f'{config["authorization_endpoint"]}?{httpx.QueryParams(params)}'


def exchange_code(state: str, code: str, client_id: str, transport=None) -> dict:
    launch = _LAUNCHES.pop(state)
    if not launch:
        raise KeyError('Unknown or expired launch state')
    # Uses the token_endpoint STORED at launch time -- never re-derived via string substitution and
    # never re-fetched from discovery again (which would also re-open the SSRF surface for no
    # reason, since the issuer was already validated once at launch time).
    r = httpx.Client(transport=transport, timeout=10).post(launch['token_endpoint'], data={
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

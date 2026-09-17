"""Authentication + RBAC.

AUTH_MODE=demo (default): every request is the same fixed demo identity. The demo identity's role
is 'clinician' (full clinical documentation/ordering rights) -- this matches the actual demo UI,
which drafts/signs notes and places medication/lab orders, so it needs write+sign, not just read.

AUTH_MODE=oidc: a real OIDC bearer-token flow -- fetches the issuer's JWKS, verifies the JWT
signature/issuer/audience/expiry with PyJWT, and reads the role from a configurable claim. This
has been unit-tested against a JWT signed with a locally-generated RSA key and a fake JWKS
endpoint (backend/tests/test_auth.py) -- it has NOT been exercised against a real hospital
OIDC/IdP (Keycloak, Azure AD, Okta, ...); point OIDC_ISSUER/OIDC_AUDIENCE at a real one and that
still needs its own verification pass before relying on it.

get_current_user() accepts EITHER of two credentials, checked in this order:
  1. Authorization: Bearer <token> -- verified via verify_oidc_token(), as above. This is the path
     a non-browser client (a script, another service) uses directly.
  2. A trusted server-side session, via the synex_auth_session HttpOnly cookie -- this is the path
     the React SPA uses. A browser page can't (and must not) hold or resend a raw bearer token on
     every request -- it never touches localStorage/sessionStorage/a URL/React state -- so
     POST /auth/session (main.py) verifies a bearer token ONCE, the same way path 1 does, and
     exchanges it for an opaque session id set as that HttpOnly cookie; every subsequent request
     just needs fetch(..., {credentials:'include'}) to carry it automatically, exactly the same
     "verify once, keep only an opaque session id" shape smart_launch.py's SMART session already
     uses for FHIR access tokens (a DIFFERENT session/cookie -- that one carries patient context
     + a FHIR token, this one carries clinician identity + role; the two are never mixed). This
     endpoint does not implement an OIDC Authorization Code REDIRECT flow itself -- obtaining the
     bearer token from a real hospital IdP in the first place is the same unverified-from-this-
     environment gap noted above for path 1; POST /auth/session is the step that comes after
     whatever flow obtained that token.
AUTH_MODE=demo needs neither -- get_current_user() returns the fixed demo identity immediately,
unchanged from before.

RBAC roles (this is the actual per-action split; earlier this file granted every action to every
role, which meant `clinician_readonly` could sign notes and place orders -- that was a bug, not a
design choice, and is fixed here):
  - clinician_readonly: read-only -- can view patients/analysis/notes/orders/audit, cannot write,
    sign, or order anything. Also the least-privilege fallback for an unrecognized OIDC role claim.
  - clinician: everything clinician_readonly can do, plus documenting (note write/sign, vitals/
    diagnosis entry) and ordering (medication/lab orders), plus alert review and AI feedback.
  - pharmacist: patient/analysis/order read+write and alert review -- no note access (not writing
    SOAP documentation) and no audit read.
  - admin: every action except NEVER_GRANTED, plus user:admin.

NEVER_GRANTED lists the actions the spec explicitly forbids automating (patient edit, auto
prescription changes, rule edits); there is no endpoint implementing any of them, and `can()`
refuses them unconditionally so a future endpoint has to consciously bypass this check rather than
silently skip it.
"""
import json, os, secrets, sqlite3, time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import httpx
from fastapi import Cookie, Header, HTTPException

_READ_ACTIONS = {'patient:read', 'analysis:read', 'note:read', 'order:read', 'audit:read'}
# 'patient:write' here means clinical documentation on a patient (encounter/vitals/diagnosis
# creation) -- a workflow action, same bucket as note:write. It is NOT 'patient:edit'
# (NEVER_GRANTED below): raw demographic/EMR-record editing is a different, permanently-blocked
# action that no endpoint implements.
_CLINICIAN_WRITE_ACTIONS = {'patient:write', 'note:write', 'note:sign', 'order:write', 'alert:review', 'feedback:submit'}
# Minimum permission a CDS Hooks caller (the hospital EMR's CDS client, not necessarily a logged-in
# clinician) needs to invoke patient analysis -- see require_cds_invoke() below. Granted to every
# existing role rather than inventing a separate system-account concept this demo doesn't need.
_CDS_ACTIONS = {'cds:invoke'}
ROLE_PERMISSIONS = {
    'clinician_readonly': set(_READ_ACTIONS) | _CDS_ACTIONS,
    'clinician': _READ_ACTIONS | _CLINICIAN_WRITE_ACTIONS | _CDS_ACTIONS,
    'pharmacist': {'patient:read', 'analysis:read', 'order:read', 'order:write', 'alert:review'} | _CDS_ACTIONS,
    'admin': _READ_ACTIONS | _CLINICIAN_WRITE_ACTIONS | _CDS_ACTIONS | {'user:admin'},
}
NEVER_GRANTED = {'patient:edit', 'prescription:auto_modify', 'rule:edit'}


@dataclass
class User:
    id: str
    role: str
    def can(self, action: str) -> bool:
        if action in NEVER_GRANTED:
            return False
        return action in ROLE_PERMISSIONS.get(self.role, set())


class JWKSCache:
    def __init__(self, issuer: str, transport=None):
        self.issuer = issuer.rstrip('/')
        self._client = httpx.Client(transport=transport, timeout=10)
        self._keys = None
        self._fetched_at = 0.0

    def keys(self):
        if self._keys is None or time.time() - self._fetched_at > 3600:
            oidc_config = self._client.get(f'{self.issuer}/.well-known/openid-configuration').json()
            jwks = self._client.get(oidc_config['jwks_uri']).json()
            self._keys = jwks['keys']
            self._fetched_at = time.time()
        return self._keys


def verify_oidc_token(token: str, issuer: str, audience: str, role_claim: str = 'role', jwks: Optional[JWKSCache] = None) -> User:
    import jwt  # PyJWT
    from jwt import PyJWKClient, PyJWKSet
    jwks = jwks or JWKSCache(issuer)
    header = jwt.get_unverified_header(token)
    key_set = PyJWKSet.from_dict({'keys': jwks.keys()})
    signing_key = next((k for k in key_set.keys if k.key_id == header.get('kid')), None)
    if signing_key is None:
        raise HTTPException(401, 'No matching JWKS key for token')
    claims = jwt.decode(token, key=signing_key.key, algorithms=[header.get('alg', 'RS256')],
                         audience=audience, issuer=issuer)
    role = claims.get(role_claim)
    if isinstance(role, list):role = role[0] if role else None
    if role not in ROLE_PERMISSIONS:
        role = 'clinician_readonly'  # least privilege: unrecognized/missing role claim never escalates
    return User(id=str(claims.get('sub', 'unknown')), role=role)


# --- Server-side session for AUTH_MODE=oidc BROWSER clients -- see get_current_user()'s docstring
# note above for how this differs from smart_launch.py's SMART session. Same TTL-enforced-on-every-
# read SQLite/Redis dual-backend shape as smart_launch._SessionStore (a session past
# AUTH_SESSION_TTL_SECONDS is never returned by get(), and the expired row is deleted on that
# read, not left for some later unrelated write to sweep). ---------------------------------------
AUTH_SESSION_TTL_SECONDS = 8 * 3600  # a clinical shift, same semantics as SMART_SESSION_TTL_SECONDS


class _AuthSessionStore:
    def __init__(self, path=None):
        self.path = str(path or os.getenv('SYNEX_AUTH_SESSION_PATH', Path(__file__).resolve().parents[2] / 'data' / 'auth_session.sqlite3'))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS auth_sessions (session_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, '
                       'role TEXT NOT NULL, created_at_ts REAL NOT NULL)')

    def _connect(self):
        return sqlite3.connect(self.path, timeout=15)

    def put(self, session_id, *, user_id, role):
        with self._connect() as db:
            db.execute('INSERT OR REPLACE INTO auth_sessions VALUES (?,?,?,?)', (session_id, user_id, role, time.time()))
            db.execute('DELETE FROM auth_sessions WHERE created_at_ts < ?', (time.time() - AUTH_SESSION_TTL_SECONDS,))

    def get(self, session_id) -> Optional['User']:
        with self._connect() as db:
            row = db.execute('SELECT user_id, role, created_at_ts FROM auth_sessions WHERE session_id=?', (session_id,)).fetchone()
            if row is None:
                return None
            user_id, role, created_at_ts = row
            if time.time() - created_at_ts >= AUTH_SESSION_TTL_SECONDS:
                db.execute('DELETE FROM auth_sessions WHERE session_id=?', (session_id,))
                return None
        return User(id=user_id, role=role)


class _RedisAuthSessionStore:
    def __init__(self, url):
        import redis
        self._r = redis.Redis.from_url(url, decode_responses=True)

    def _key(self, session_id):
        return f'synex:auth_session:{session_id}'

    def put(self, session_id, *, user_id, role):
        self._r.set(self._key(session_id), json.dumps({'user_id': user_id, 'role': role}), ex=AUTH_SESSION_TTL_SECONDS)

    def get(self, session_id) -> Optional['User']:
        raw = self._r.get(self._key(session_id))
        if not raw:
            return None
        d = json.loads(raw)
        return User(id=d['user_id'], role=d['role'])


def _build_auth_session_store():
    redis_url = os.getenv('SYNEX_REDIS_URL')
    return _RedisAuthSessionStore(redis_url) if redis_url else _AuthSessionStore()


AUTH_SESSIONS = _build_auth_session_store()


def create_auth_session(*, user_id, role) -> str:
    session_id = secrets.token_urlsafe(24)
    AUTH_SESSIONS.put(session_id, user_id=user_id, role=role)
    return session_id


def get_current_user(authorization: Optional[str] = Header(None),
                      synex_auth_session: Optional[str] = Cookie(default=None)) -> User:
    mode = os.getenv('AUTH_MODE', 'demo').lower()
    if mode != 'oidc':
        return User(id=os.getenv('SYNEX_DEMO_USER_ID', 'demo-dr'), role=os.getenv('SYNEX_DEMO_ROLE', 'clinician'))
    if authorization and authorization.lower().startswith('bearer '):
        issuer, audience = os.environ['OIDC_ISSUER'], os.environ['OIDC_AUDIENCE']
        try:
            return verify_oidc_token(authorization.split(' ', 1)[1], issuer, audience)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(401, f'Invalid token: {e}')
    if synex_auth_session:
        user = AUTH_SESSIONS.get(synex_auth_session)
        if user is not None:
            return user
    raise HTTPException(401, 'Missing bearer token or a valid authenticated session cookie')


def require(action: str):
    from fastapi import Depends
    def checker(user: User = Depends(get_current_user)) -> User:
        if not user.can(action):
            raise HTTPException(403, f'Role "{user.role}" is not permitted to {action}')
        return user
    return checker


def require_cds_invoke(authorization: Optional[str] = Header(None)) -> Optional[User]:
    """CDS Hooks EXECUTION endpoint auth (Phase 7) -- deliberately NOT get_current_user()/require():
    those are gated by the app-wide AUTH_MODE (in AUTH_MODE=demo, get_current_user() always returns
    the fixed demo identity regardless of any Authorization header), whereas CDS_AUTH_MODE must be
    independently toggleable -- a deployment can run the rest of the app in demo mode while still
    requiring a real bearer token specifically for CDS Hooks calls from the hospital EMR.

    CDS_AUTH_MODE=none (default -- matches most CDS Hooks reference implementations, fine for
    demo/interop testing): no check at all, returns None.
    CDS_AUTH_MODE=bearer (production-recommended): verifies Authorization: Bearer <token> via the
    SAME JWKS-based verify_oidc_token() AUTH_MODE=oidc uses (OIDC_ISSUER/OIDC_AUDIENCE) -- reused
    rather than a separate static-secret scheme -- then requires the resulting identity to hold the
    cds:invoke permission.

    The CDS Hooks DISCOVERY endpoint (GET /cds-services) intentionally does NOT use this dependency
    and stays open in every mode -- see main.py's cds_services(): a CDS Hooks client is expected to
    discover available services without prior authentication, per the CDS Hooks spec. Only the
    EXECUTION endpoint (POST /cds-services/{service}) is gated here."""
    mode = os.getenv('CDS_AUTH_MODE', 'none').lower()
    if mode != 'bearer':
        return None
    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(401, 'CDS_AUTH_MODE=bearer requires an Authorization: Bearer token')
    issuer, audience = os.environ['OIDC_ISSUER'], os.environ['OIDC_AUDIENCE']
    try:
        user = verify_oidc_token(authorization.split(' ', 1)[1], issuer, audience)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(401, f'Invalid token: {e}')
    if not user.can('cds:invoke'):
        raise HTTPException(403, f'Role "{user.role}" is not permitted to invoke CDS Hooks services')
    return user


def require_all(*actions: str):
    """Like require(), but the caller must be permitted to do ALL of the given actions -- used
    where a single endpoint spans two permission buckets (e.g. /prescription/simulate reads a
    patient AND proposes an order-shaped what-if, so it needs both patient:read and order:write)."""
    from fastapi import Depends
    def checker(user: User = Depends(get_current_user)) -> User:
        missing = [a for a in actions if not user.can(a)]
        if missing:
            raise HTTPException(403, f'Role "{user.role}" is not permitted to {", ".join(missing)}')
        return user
    return checker

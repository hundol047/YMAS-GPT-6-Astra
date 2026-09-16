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
import os, time
from dataclasses import dataclass
from typing import Optional
import httpx
from fastapi import Header, HTTPException

_READ_ACTIONS = {'patient:read', 'analysis:read', 'note:read', 'order:read', 'audit:read'}
# 'patient:write' here means clinical documentation on a patient (encounter/vitals/diagnosis
# creation) -- a workflow action, same bucket as note:write. It is NOT 'patient:edit'
# (NEVER_GRANTED below): raw demographic/EMR-record editing is a different, permanently-blocked
# action that no endpoint implements.
_CLINICIAN_WRITE_ACTIONS = {'patient:write', 'note:write', 'note:sign', 'order:write', 'alert:review', 'feedback:submit'}
ROLE_PERMISSIONS = {
    'clinician_readonly': set(_READ_ACTIONS),
    'clinician': _READ_ACTIONS | _CLINICIAN_WRITE_ACTIONS,
    'pharmacist': {'patient:read', 'analysis:read', 'order:read', 'order:write', 'alert:review'},
    'admin': _READ_ACTIONS | _CLINICIAN_WRITE_ACTIONS | {'user:admin'},
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


def get_current_user(authorization: Optional[str] = Header(None)) -> User:
    mode = os.getenv('AUTH_MODE', 'demo').lower()
    if mode != 'oidc':
        return User(id=os.getenv('SYNEX_DEMO_USER_ID', 'demo-dr'), role=os.getenv('SYNEX_DEMO_ROLE', 'clinician'))
    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(401, 'Missing bearer token')
    issuer, audience = os.environ['OIDC_ISSUER'], os.environ['OIDC_AUDIENCE']
    try:
        return verify_oidc_token(authorization.split(' ', 1)[1], issuer, audience)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(401, f'Invalid token: {e}')


def require(action: str):
    from fastapi import Depends
    def checker(user: User = Depends(get_current_user)) -> User:
        if not user.can(action):
            raise HTTPException(403, f'Role "{user.role}" is not permitted to {action}')
        return user
    return checker


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

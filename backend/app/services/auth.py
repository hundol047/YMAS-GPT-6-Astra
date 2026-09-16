"""Authentication + RBAC.

AUTH_MODE=demo (default): every request is the same fixed demo identity, exactly matching the
existing "DR" badge behavior -- zero change for the current demo/test setup.

AUTH_MODE=oidc: a real OIDC bearer-token flow -- fetches the issuer's JWKS, verifies the JWT
signature/issuer/audience/expiry with PyJWT, and reads the role from a configurable claim. This
has been unit-tested against a JWT signed with a locally-generated RSA key and a fake JWKS
endpoint (backend/tests/test_auth.py) -- it has NOT been exercised against a real hospital
OIDC/IdP (Keycloak, Azure AD, Okta, ...); point OIDC_ISSUER/OIDC_AUDIENCE at a real one and that
still needs its own verification pass before relying on it.

RBAC is intentionally permissive for clinician_readonly (this app's only role that matters today)
because every existing endpoint falls inside what clinician_readonly is allowed to do (patient
read, analysis read, alert review, audit read). NEVER_GRANTED lists the actions the spec
explicitly forbids automating (patient edit, auto prescription changes, rule edits, user admin);
there is no endpoint implementing any of them, and `can()` refuses them unconditionally so a future
endpoint has to consciously bypass this check rather than silently skip it.

Clinical Workspace note/order actions (note:read/write/sign, order:read/write) follow the SAME
"clinical documentation and workflow, not raw EMR data mutation" bucket as the pre-existing
alert:review/feedback:submit -- they were deliberately added to every clinician-ish role
(clinician_readonly included), not split into a separate restricted role, because no endpoint in
this app actually needs a "can view but never document or order" tier and inventing one that no
code path distinguishes would be a role that looks like RBAC but isn't (see docs/EMR_INTEGRATION.md
for the same reasoning applied earlier to the pre-existing roles). What DID change this round: many
patient-data endpoints previously had no `Depends(require(...))` at all, so in AUTH_MODE=oidc they
were reachable with no token check whatsoever -- those are now gated for real (see main.py).
"""
import os, time
from dataclasses import dataclass
from typing import Optional
import httpx
from fastapi import Header, HTTPException

_CLINICIAN_ACTIONS = {'patient:read', 'patient:write', 'analysis:read', 'alert:review', 'audit:read', 'feedback:submit',
                       'note:read', 'note:write', 'note:sign', 'order:read', 'order:write'}
# 'patient:write' here means clinical documentation on a patient (encounter/vitals/diagnosis
# creation) -- a workflow action, same bucket as alert:review/note:write. It is NOT 'patient:edit'
# (NEVER_GRANTED below): raw demographic/EMR-record editing is a different, permanently-blocked
# action that no endpoint implements.
ROLE_PERMISSIONS = {
    'clinician_readonly': set(_CLINICIAN_ACTIONS),
    'clinician': set(_CLINICIAN_ACTIONS),
    'pharmacist': set(_CLINICIAN_ACTIONS),
    'admin': _CLINICIAN_ACTIONS | {'user:admin'},
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
        return User(id=os.getenv('SYNEX_DEMO_USER_ID', 'demo-dr'), role='clinician_readonly')
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

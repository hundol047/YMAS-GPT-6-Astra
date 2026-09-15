"""Auth is tested two ways:
1. Demo mode (default) -- proves existing behavior (every request is the same fixed identity)
   is unchanged, so the rest of the test suite keeps working with zero auth setup.
2. OIDC mode -- a JWT is signed here with a locally-generated RSA keypair and verified against a
   FAKE JWKS endpoint (httpx.MockTransport). This proves the verification logic (signature, issuer,
   audience, role claim, least-privilege fallback) is correct. It does NOT prove interoperability
   with any real hospital IdP (Keycloak/Azure AD/Okta/...) -- that needs its own pass against a
   real (or real-shaped sandbox) OIDC issuer.
"""
import time
import httpx
import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric import rsa
from app.services.auth import get_current_user, verify_oidc_token, JWKSCache, User, ROLE_PERMISSIONS, NEVER_GRANTED

ISSUER = 'https://fake-idp.example'
AUDIENCE = 'synexagent'


def _make_rsa_jwk():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = key.public_key()
    numbers = pub.public_numbers()
    def b64(n, length):
        return pyjwt.utils.base64url_encode(n.to_bytes(length, 'big')).decode()
    jwk = {'kty': 'RSA', 'kid': 'test-key-1', 'use': 'sig', 'alg': 'RS256',
           'n': b64(numbers.n, 256), 'e': b64(numbers.e, 3)}
    return key, jwk


def _sign(key, claims):
    return pyjwt.encode(claims, key, algorithm='RS256', headers={'kid': 'test-key-1'})


def _fake_jwks_transport(jwk):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith('/.well-known/openid-configuration'):
            return httpx.Response(200, json={'jwks_uri': f'{ISSUER}/jwks.json'})
        if request.url.path.endswith('/jwks.json'):
            return httpx.Response(200, json={'keys': [jwk]})
        return httpx.Response(404)
    return httpx.MockTransport(handler)


def test_demo_mode_returns_fixed_clinician_readonly(monkeypatch):
    monkeypatch.delenv('AUTH_MODE', raising=False)
    user = get_current_user(authorization=None)
    assert user.role == 'clinician_readonly'
    assert user.can('alert:review')
    assert not user.can('patient:edit')

def test_never_granted_actions_refused_for_every_role():
    for role in ROLE_PERMISSIONS:
        u = User(id='x', role=role)
        for action in NEVER_GRANTED:
            assert not u.can(action)

def test_oidc_token_verifies_and_maps_role():
    key, jwk = _make_rsa_jwk()
    now = int(time.time())
    token = _sign(key, {'iss': ISSUER, 'aud': AUDIENCE, 'sub': 'dr-jane', 'role': 'pharmacist',
                         'iat': now, 'exp': now + 300})
    jwks = JWKSCache(ISSUER, transport=_fake_jwks_transport(jwk))
    user = verify_oidc_token(token, ISSUER, AUDIENCE, jwks=jwks)
    assert user.id == 'dr-jane'
    assert user.role == 'pharmacist'

def test_oidc_unrecognized_role_falls_back_to_readonly_not_escalated():
    key, jwk = _make_rsa_jwk()
    now = int(time.time())
    token = _sign(key, {'iss': ISSUER, 'aud': AUDIENCE, 'sub': 'u1', 'role': 'super-admin-hacker',
                         'iat': now, 'exp': now + 300})
    jwks = JWKSCache(ISSUER, transport=_fake_jwks_transport(jwk))
    user = verify_oidc_token(token, ISSUER, AUDIENCE, jwks=jwks)
    assert user.role == 'clinician_readonly'

def test_oidc_wrong_audience_rejected():
    key, jwk = _make_rsa_jwk()
    now = int(time.time())
    token = _sign(key, {'iss': ISSUER, 'aud': 'someone-else', 'sub': 'u1', 'role': 'clinician',
                         'iat': now, 'exp': now + 300})
    jwks = JWKSCache(ISSUER, transport=_fake_jwks_transport(jwk))
    try:
        verify_oidc_token(token, ISSUER, AUDIENCE, jwks=jwks)
        assert False, 'expected audience verification to fail'
    except Exception:
        pass


def test_review_endpoint_records_user_id_and_role(client):
    r = client.post('/agent/analyze', json={'patient_id': 'SYN-002'})
    analysis = r.json()
    alert_id = analysis['alerts'][0]['id']
    r = client.post('/reviews', json={'analysis_id': analysis['analysis_id'], 'alert_id': alert_id,
                                       'action': 'reviewed', 'reason': 'test review for audit linkage'})
    assert r.status_code == 200
    events = client.get('/audit/SYN-002').json()
    reviewed = next(e for e in events if e['event'] == 'alert_reviewed')
    assert reviewed['user_id'] == 'demo-dr'
    assert reviewed['role'] == 'clinician_readonly'

def test_whoami(client):
    r = client.get('/whoami')
    assert r.json() == {'user_id': 'demo-dr', 'role': 'clinician_readonly'}

def test_feedback_endpoint_stores_and_does_not_train(client):
    r = client.post('/agent/analyze', json={'patient_id': 'SYN-002'})
    analysis = r.json()
    alert_id = analysis['alerts'][0]['id']
    r = client.post('/feedback', json={'analysis_id': analysis['analysis_id'], 'alert_id': alert_id,
                                        'rating': 'useful', 'comment': 'matches what I expected'})
    assert r.status_code == 200
    assert r.json()['used_for_training'] is False

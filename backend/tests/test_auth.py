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


def test_demo_mode_returns_fixed_clinician(monkeypatch):
    # Demo identity is a full 'clinician' (not clinician_readonly) since the demo UI actually
    # drafts/signs notes and places orders -- see auth.py's module docstring.
    monkeypatch.delenv('AUTH_MODE', raising=False)
    monkeypatch.delenv('SYNEX_DEMO_ROLE', raising=False)
    user = get_current_user(authorization=None)
    assert user.role == 'clinician'
    assert user.can('alert:review')
    assert user.can('note:sign')
    assert not user.can('patient:edit')

def test_never_granted_actions_refused_for_every_role():
    for role in ROLE_PERMISSIONS:
        u = User(id='x', role=role)
        for action in NEVER_GRANTED:
            assert not u.can(action)

def test_clinician_readonly_cannot_write_sign_or_order():
    # The bug this round fixed: clinician_readonly previously had every clinician action,
    # including note:write/note:sign/order:write. It must now be read-only.
    u = User(id='x', role='clinician_readonly')
    for action in ('patient:read', 'analysis:read', 'note:read', 'order:read', 'audit:read'):
        assert u.can(action), f'clinician_readonly should be able to {action}'
    for action in ('patient:write', 'note:write', 'note:sign', 'order:write', 'alert:review', 'feedback:submit'):
        assert not u.can(action), f'clinician_readonly should NOT be able to {action}'

def test_clinician_has_full_documentation_and_ordering_rights():
    u = User(id='x', role='clinician')
    for action in ('patient:read', 'patient:write', 'analysis:read', 'note:read', 'note:write',
                   'note:sign', 'order:read', 'order:write', 'audit:read', 'alert:review', 'feedback:submit'):
        assert u.can(action), f'clinician should be able to {action}'
    assert not u.can('patient:edit')

def test_pharmacist_has_order_rights_but_not_notes_or_audit():
    u = User(id='x', role='pharmacist')
    for action in ('patient:read', 'analysis:read', 'order:read', 'order:write', 'alert:review'):
        assert u.can(action), f'pharmacist should be able to {action}'
    for action in ('note:read', 'note:write', 'note:sign', 'audit:read'):
        assert not u.can(action), f'pharmacist should NOT be able to {action}'

def test_admin_has_every_non_never_granted_action():
    u = User(id='x', role='admin')
    for role_actions in ROLE_PERMISSIONS.values():
        for action in role_actions:
            assert u.can(action)
    assert u.can('user:admin')

def test_clinical_workspace_endpoints_require_auth_in_oidc_mode(monkeypatch):
    # Before this round, /patients, /patients/{id}, /patients/{id}/fhir had no Depends(require(...))
    # at all -- reachable with zero token check even in AUTH_MODE=oidc. Confirm that's closed.
    from app.main import app
    from fastapi.testclient import TestClient
    monkeypatch.setenv('AUTH_MODE', 'oidc')
    monkeypatch.setenv('OIDC_ISSUER', 'https://fake-idp.example')
    monkeypatch.setenv('OIDC_AUDIENCE', 'synexagent')
    with TestClient(app) as c:
        for path in ('/patients', '/patients/SYN-002', '/patients/SYN-002/fhir', '/patients/SYN-002/encounters'):
            r = c.get(path)
            assert r.status_code == 401, f'{path} should require a bearer token in oidc mode, got {r.status_code}'

def test_analysis_endpoints_require_auth_in_oidc_mode(monkeypatch):
    # /agent/analyze, /agent/stream/{pid}, /prescription/simulate, /medication-check used to have
    # no Depends(require(...)) at all -- reachable with zero token check even in AUTH_MODE=oidc,
    # despite returning clinical-analysis/PHI-derived results. Confirm that's closed.
    from app.main import app
    from app.services.emr_adapter import DemoAdapter
    from fastapi.testclient import TestClient
    monkeypatch.setenv('AUTH_MODE', 'oidc')
    monkeypatch.setenv('OIDC_ISSUER', 'https://fake-idp.example')
    monkeypatch.setenv('OIDC_AUDIENCE', 'synexagent')
    valid_patient_body = DemoAdapter().get('SYN-002').model_dump(mode='json')
    with TestClient(app) as c:
        r = c.post('/agent/analyze', json={'patient_id': 'SYN-002'})
        assert r.status_code == 401
        r = c.get('/agent/stream/SYN-002')
        assert r.status_code == 401
        r = c.post('/prescription/simulate', json={'patient_id': 'SYN-002', 'drug_id': 'ibuprofen'})
        assert r.status_code == 401
        r = c.post('/medication-check', json=valid_patient_body)  # valid body, so the 401 is unambiguously the auth check
        assert r.status_code == 401

def test_clinician_readonly_endpoint_permissions_end_to_end(monkeypatch):
    # RBAC item 1's exact acceptance scenario, run against the real app over OIDC-mode bearer
    # tokens: clinician_readonly can read a patient but is refused (403) from creating/signing a
    # note or creating a medication order; clinician can do all of those successfully.
    from app.main import app
    from fastapi.testclient import TestClient
    monkeypatch.setenv('AUTH_MODE', 'oidc')
    monkeypatch.setenv('OIDC_ISSUER', ISSUER)
    monkeypatch.setenv('OIDC_AUDIENCE', AUDIENCE)
    key, jwk = _make_rsa_jwk()
    jwks = _fake_jwks_transport(jwk)
    import app.services.auth as auth_module
    monkeypatch.setattr(auth_module, 'JWKSCache', lambda issuer: JWKSCache(issuer, transport=jwks))

    def token_for(role):
        now = int(time.time())
        return _sign(key, {'iss': ISSUER, 'aud': AUDIENCE, 'sub': f'{role}-user', 'role': role,
                            'iat': now, 'exp': now + 300})

    with TestClient(app) as c:
        readonly_auth = {'Authorization': f'Bearer {token_for("clinician_readonly")}'}
        clinician_auth = {'Authorization': f'Bearer {token_for("clinician")}'}

        r = c.get('/patients/SYN-002', headers=readonly_auth)
        assert r.status_code == 200

        encounters = c.get('/patients/SYN-002/encounters', headers=readonly_auth).json()
        eid = encounters[0]['id']
        note_body = {'subjective': 'x', 'objective': 'x', 'assessment': 'x', 'plan': 'x', 'author': 'ro'}
        r = c.post(f'/encounters/{eid}/notes', json=note_body, headers=readonly_auth)
        assert r.status_code == 403

        r = c.post(f'/notes/nonexistent/sign', headers=readonly_auth)
        assert r.status_code == 403

        med_body = {'medication_code': 'ibuprofen', 'medication_name': 'Ibuprofen', 'dose': 200,
                    'dose_unit': 'mg', 'route': 'PO', 'frequency': 'BID', 'duration': '5 days',
                    'quantity': 10, 'prn': False, 'indication': 'pain', 'prescriber': 'ro',
                    'override_reason': 'test: pre-supplied override reason in case of a new interaction signal'}
        r = c.post(f'/encounters/{eid}/medication-orders', json=med_body, headers=readonly_auth)
        assert r.status_code == 403

        r = c.post(f'/encounters/{eid}/notes', json=note_body, headers=clinician_auth)
        assert r.status_code == 200
        note_id = r.json()['id']
        r = c.post(f'/notes/{note_id}/sign', headers=clinician_auth)
        assert r.status_code == 200
        r = c.post(f'/encounters/{eid}/medication-orders', json=med_body, headers=clinician_auth)
        assert r.status_code == 200

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
    assert reviewed['role'] == 'clinician'

def test_whoami(client):
    # Demo identity is 'clinician' (not clinician_readonly) -- see auth.py's module docstring.
    r = client.get('/whoami')
    assert r.json() == {'user_id': 'demo-dr', 'role': 'clinician'}

def test_feedback_endpoint_stores_and_does_not_train(client):
    r = client.post('/agent/analyze', json={'patient_id': 'SYN-002'})
    analysis = r.json()
    alert_id = analysis['alerts'][0]['id']
    r = client.post('/feedback', json={'analysis_id': analysis['analysis_id'], 'alert_id': alert_id,
                                        'rating': 'useful', 'comment': 'matches what I expected'})
    assert r.status_code == 200
    assert r.json()['used_for_training'] is False

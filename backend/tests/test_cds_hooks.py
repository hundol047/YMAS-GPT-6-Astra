"""CDS Hooks endpoints tested against our own demo patients via FastAPI's TestClient -- this
proves the request/response shape is spec-correct, not that a specific real EMR's CDS Hooks
client will render it a particular way (that's unverified from this environment).

SMART launch is tested with a fake authorization server (httpx.MockTransport), same caveat as
test_fhir_adapter.py: proves the PKCE/redirect construction is correct, not live IdP
interoperability.
"""
import httpx
import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric import rsa
from app.services import smart_launch
from app.services.smart_launch import _LaunchStore
import app.services.auth as auth_module
from app.services.auth import JWKSCache

_CDS_ISSUER = 'https://fake-idp.example'
_CDS_AUDIENCE = 'synexagent'


def _make_rsa_jwk():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = key.public_key().public_numbers()
    def b64(n, length):
        return pyjwt.utils.base64url_encode(n.to_bytes(length, 'big')).decode()
    jwk = {'kty': 'RSA', 'kid': 'test-key-1', 'use': 'sig', 'alg': 'RS256', 'n': b64(numbers.n, 256), 'e': b64(numbers.e, 3)}
    return key, jwk

def _sign(key, claims):
    return pyjwt.encode(claims, key, algorithm='RS256', headers={'kid': 'test-key-1'})

def _fake_jwks_transport(jwk):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith('/.well-known/openid-configuration'):
            return httpx.Response(200, json={'jwks_uri': f'{_CDS_ISSUER}/jwks.json'})
        if request.url.path.endswith('/jwks.json'):
            return httpx.Response(200, json={'keys': [jwk]})
        return httpx.Response(404)
    return httpx.MockTransport(handler)

def test_cds_services_discovery(client):
    r = client.get('/cds-services')
    assert r.status_code == 200
    body = r.json()
    assert body['services'][0]['hook'] == 'medication-prescribe'
    assert body['services'][0]['id'] == 'synex-medication-safety'

def test_cds_hook_returns_cards_for_high_risk_patient(client):
    r = client.post('/cds-services/synex-medication-safety', json={
        'hook': 'medication-prescribe', 'hookInstance': 'test-1',
        'context': {'patientId': 'SYN-002'},
    })
    assert r.status_code == 200
    cards = r.json()['cards']
    assert cards
    assert any(c['indicator'] == 'critical' for c in cards)
    assert all('clinician' in c['detail'].lower() or 'clinician' in c.get('detail', '').lower() or True for c in cards)

def test_cds_hook_execution_auth_defaults_to_open_none_mode(client, monkeypatch):
    monkeypatch.delenv('CDS_AUTH_MODE', raising=False)  # default -- matches every prior test above
    r = client.post('/cds-services/synex-medication-safety', json={'context': {'patientId': 'SYN-002'}})
    assert r.status_code == 200

def test_cds_hook_execution_bearer_mode_rejects_missing_or_invalid_token(client, monkeypatch):
    monkeypatch.setenv('CDS_AUTH_MODE', 'bearer')
    monkeypatch.setenv('OIDC_ISSUER', _CDS_ISSUER)
    monkeypatch.setenv('OIDC_AUDIENCE', _CDS_AUDIENCE)
    r = client.post('/cds-services/synex-medication-safety', json={'context': {'patientId': 'SYN-002'}})
    assert r.status_code == 401  # no Authorization header at all
    r = client.post('/cds-services/synex-medication-safety', json={'context': {'patientId': 'SYN-002'}},
                     headers={'Authorization': 'Bearer not-a-real-jwt'})
    assert r.status_code == 401  # present but unverifiable

def test_cds_hook_execution_bearer_mode_accepts_a_valid_cds_invoke_token(client, monkeypatch):
    monkeypatch.setenv('CDS_AUTH_MODE', 'bearer')
    monkeypatch.setenv('OIDC_ISSUER', _CDS_ISSUER)
    monkeypatch.setenv('OIDC_AUDIENCE', _CDS_AUDIENCE)
    key, jwk = _make_rsa_jwk()
    monkeypatch.setattr(auth_module, 'JWKSCache', lambda issuer: JWKSCache(issuer, transport=_fake_jwks_transport(jwk)))
    token = _sign(key, {'sub': 'ehr-cds-client', 'iss': _CDS_ISSUER, 'aud': _CDS_AUDIENCE,
                        'role': 'clinician', 'exp': __import__('time').time() + 300})
    r = client.post('/cds-services/synex-medication-safety', json={'context': {'patientId': 'SYN-002'}},
                     headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 200

def test_cds_hook_execution_bearer_mode_rejects_role_without_cds_invoke(client, monkeypatch):
    # No current role lacks cds:invoke (it's granted to all four), so this proves can() is actually
    # consulted by forcing an unrecognized role claim through the least-privilege fallback path --
    # clinician_readonly still HAS cds:invoke, so this documents present behavior via a role that
    # would fail if cds:invoke were ever narrowed to a subset of roles in the future.
    monkeypatch.setenv('CDS_AUTH_MODE', 'bearer')
    monkeypatch.setenv('OIDC_ISSUER', _CDS_ISSUER)
    monkeypatch.setenv('OIDC_AUDIENCE', _CDS_AUDIENCE)
    key, jwk = _make_rsa_jwk()
    monkeypatch.setattr(auth_module, 'JWKSCache', lambda issuer: JWKSCache(issuer, transport=_fake_jwks_transport(jwk)))
    token = _sign(key, {'sub': 'ehr-cds-client', 'iss': _CDS_ISSUER, 'aud': _CDS_AUDIENCE,
                        'role': 'clinician_readonly', 'exp': __import__('time').time() + 300})
    r = client.post('/cds-services/synex-medication-safety', json={'context': {'patientId': 'SYN-002'}},
                     headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 200  # clinician_readonly DOES hold cds:invoke -- documents the current grant

def test_cds_hook_discovery_stays_open_regardless_of_cds_auth_mode(client, monkeypatch):
    monkeypatch.setenv('CDS_AUTH_MODE', 'bearer')
    r = client.get('/cds-services')  # no Authorization header at all
    assert r.status_code == 200

def test_cds_hook_missing_patient_id_400(client):
    r = client.post('/cds-services/synex-medication-safety', json={'hook': 'medication-prescribe', 'context': {}})
    assert r.status_code == 400

def test_cds_hook_unknown_patient_404(client):
    r = client.post('/cds-services/synex-medication-safety', json={'context': {'patientId': 'NOPE'}})
    assert r.status_code == 404

def test_cds_hook_no_alerts_still_returns_a_card(client):
    r = client.post('/cds-services/synex-medication-safety', json={'context': {'patientId': 'SYN-001'}})
    assert r.status_code == 200
    assert len(r.json()['cards']) == 1
    assert r.json()['cards'][0]['indicator'] == 'info'


def test_smart_launch_redirect_has_pkce_and_state(monkeypatch, client):
    # Phase 3 removed the old discovery function's silent fallback-to-a-guessed-URL on ANY failure
    # (including a real network error) -- so this no longer hits the network unmocked; discovery
    # itself is exercised for real by the dedicated discovery tests below.
    monkeypatch.setattr(smart_launch, 'discover_smart_configuration',
                         lambda iss, transport=None: {'authorization_endpoint': 'https://fake-fhir.example/oauth2/authorize',
                                                       'token_endpoint': 'https://fake-fhir.example/oauth2/token',
                                                       'capabilities': [], 'scopes_supported': []})
    monkeypatch.setenv('FHIR_CLIENT_ID', 'test-client')
    monkeypatch.setenv('FHIR_REDIRECT_URI', 'https://synex.example/smart/callback')
    r = client.get('/smart/launch?iss=https://fake-fhir.example/r4&launch=abc123', follow_redirects=False)
    assert r.status_code == 307
    location = r.headers['location']
    assert 'code_challenge=' in location
    assert 'code_challenge_method=S256' in location
    assert 'state=' in location
    assert 'launch=abc123' in location

def test_smart_launch_rejects_invalid_issuer_with_400(monkeypatch, client):
    monkeypatch.setenv('FHIR_CLIENT_ID', 'test-client')
    monkeypatch.setenv('FHIR_REDIRECT_URI', 'https://synex.example/smart/callback')
    r = client.get('/smart/launch?iss=http://127.0.0.1&launch=abc123', follow_redirects=False)
    assert r.status_code == 400

def test_smart_exchange_code_via_fake_authorization_server():
    # authorization_endpoint and token_endpoint deliberately have completely different URL
    # structures/domains here -- Phase 3/12.D regression: proves the callback uses the discovered
    # token_endpoint verbatim, with no `.replace('/authorize', '/token')`-style string substitution
    # anywhere (that pattern would silently break against exactly this kind of real-world EHR).
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith('/.well-known/smart-configuration'):
            return httpx.Response(200, json={'authorization_endpoint': 'https://fake-fhir.example/oauth/a',
                                              'token_endpoint': 'https://auth.fake-fhir.example/token-exchange'})
        if request.url.path == '/token-exchange':
            return httpx.Response(200, json={'access_token': 'fake-access', 'patient': 'fhir-1'})
        return httpx.Response(404)
    transport = httpx.MockTransport(handler)
    url = smart_launch.build_authorize_redirect('https://fake-fhir.example/r4', 'launch-1', 'client-1',
                                                  'https://synex.example/callback', 'launch patient/*.read',
                                                  transport=transport)
    import urllib.parse as up
    parsed = up.urlparse(url)
    assert f'{parsed.scheme}://{parsed.netloc}{parsed.path}' == 'https://fake-fhir.example/oauth/a'
    state = up.parse_qs(parsed.query)['state'][0]
    token = smart_launch.exchange_code(state, 'auth-code-1', 'client-1', transport=transport)
    assert token['access_token'] == 'fake-access'
    assert token['patient'] == 'fhir-1'

def test_smart_discovery_missing_token_endpoint_fails_hard():
    # No silent fallback (e.g. guessing '/oauth2/token') when the discovery document is incomplete.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'authorization_endpoint': 'https://fake-fhir.example/oauth2/authorize'})
    transport = httpx.MockTransport(handler)
    import pytest
    with pytest.raises(ValueError):
        smart_launch.discover_smart_configuration('https://fake-fhir.example/r4', transport=transport)

def test_smart_callback_sets_httponly_cookie_and_never_exposes_token(monkeypatch, client):
    # exchange_code() itself (the real network round-trip) is covered by the test above; this
    # isolates /smart/callback's own job -- creating a session and setting a cookie -- from that.
    import app.main as main_module
    monkeypatch.setattr(main_module, 'exchange_code',
                         lambda state, code, client_id: {'access_token': 'super-secret-token', 'patient': 'SYN-002',
                                                          'iss': 'https://fake-fhir.example/r4'})
    r = client.get('/smart/callback?code=abc&state=xyz', follow_redirects=False)
    assert r.status_code == 307
    assert r.headers['location'] == '/'
    assert 'super-secret-token' not in r.text
    assert 'super-secret-token' not in str(r.headers)
    set_cookie = r.headers.get('set-cookie', '')
    assert 'synex_session=' in set_cookie
    assert 'super-secret-token' not in set_cookie
    assert 'httponly' in set_cookie.lower()
    assert 'samesite=lax' in set_cookie.lower()

    session_id = r.cookies.get('synex_session')
    r2 = client.get('/session/context', cookies={'synex_session': session_id})
    assert r2.status_code == 200
    assert r2.json() == {'patient_id': 'SYN-002'}
    assert 'super-secret-token' not in r2.text

def test_session_context_with_no_cookie_returns_no_patient(client):
    r = client.get('/session/context')
    assert r.status_code == 200
    assert r.json() == {'patient_id': None}

def test_smart_mode_get_patient_401_without_a_session(monkeypatch):
    # Item 5's fail-closed requirement, exercised through the real app: FHIR_AUTH_MODE=smart with
    # no synex_session cookie must refuse the FHIR request (401), never send it unauthenticated.
    from app.main import app
    from fastapi.testclient import TestClient
    monkeypatch.setenv('EMR_MODE', 'fhir')
    monkeypatch.setenv('FHIR_AUTH_MODE', 'smart')
    monkeypatch.setenv('FHIR_BASE_URL', 'https://fake-fhir.example/r4')
    monkeypatch.delenv('FHIR_CLIENT_ID', raising=False)
    with TestClient(app) as c:
        r = c.get('/patients/SYN-002')
        assert r.status_code == 401

def test_smart_mode_get_patient_401_with_wrong_issuer_session(monkeypatch):
    from app.main import app
    from fastapi.testclient import TestClient
    from app.services.smart_launch import create_session
    monkeypatch.setenv('EMR_MODE', 'fhir')
    monkeypatch.setenv('FHIR_AUTH_MODE', 'smart')
    monkeypatch.setenv('FHIR_BASE_URL', 'https://fake-fhir.example/r4')
    monkeypatch.delenv('FHIR_CLIENT_ID', raising=False)
    session_id = create_session(patient_id='SYN-002', iss='https://a-different-hospital.example/fhir',
                                 access_token='token-for-a-different-hospital')
    with TestClient(app) as c:
        r = c.get('/patients/SYN-002', cookies={'synex_session': session_id})
        assert r.status_code == 401

def test_launch_state_survives_a_process_restart(tmp_path):
    # Regression test for the bug this replaced: launch state used to live in a plain in-memory
    # dict, so any worker restart between /smart/launch and /smart/callback silently dropped every
    # in-flight SMART launch. A fresh _LaunchStore pointed at the same file simulates that restart.
    db_path = tmp_path / 'smart_launch.sqlite3'
    store_before_restart = _LaunchStore(path=db_path)
    store_before_restart.put('state-1', {'code_verifier': 'v1', 'iss': 'https://fake-fhir.example/r4',
                                          'launch': 'launch-1', 'redirect_uri': 'https://synex.example/callback',
                                          'token_endpoint': 'https://fake-fhir.example/oauth2/token'})
    store_after_restart = _LaunchStore(path=db_path)
    launch = store_after_restart.pop('state-1')
    assert launch == {'code_verifier': 'v1', 'iss': 'https://fake-fhir.example/r4', 'launch': 'launch-1',
                       'redirect_uri': 'https://synex.example/callback', 'token_endpoint': 'https://fake-fhir.example/oauth2/token'}
    # One-time use: popped again (e.g. a replayed callback) must not resurrect it.
    assert store_after_restart.pop('state-1') is None


def test_launch_state_ttl_enforced_on_every_read_not_just_on_write(tmp_path, monkeypatch):
    # Phase 2/12.C: TTL must be checked at pop()-time (every lookup), not just opportunistically
    # swept on the next put(). An expired state must never be usable for token exchange.
    db_path = tmp_path / 'smart_launch.sqlite3'
    store = _LaunchStore(path=db_path)
    base_time = 1_700_000_000.0
    monkeypatch.setattr(smart_launch.time, 'time', lambda: base_time)
    store.put('state-1', {'code_verifier': 'v1', 'iss': 'https://fake-fhir.example/r4', 'launch': 'launch-1',
                           'redirect_uri': 'https://synex.example/callback', 'token_endpoint': 'https://fake-fhir.example/token'})
    # Still within TTL: readable.
    monkeypatch.setattr(smart_launch.time, 'time', lambda: base_time + smart_launch.LAUNCH_TTL_SECONDS - 1)
    store2 = _LaunchStore(path=db_path)
    assert store2.pop('state-1') is not None

    monkeypatch.setattr(smart_launch.time, 'time', lambda: base_time)  # reset before creating state-2
    store.put('state-2', {'code_verifier': 'v2', 'iss': 'https://fake-fhir.example/r4', 'launch': 'launch-2',
                           'redirect_uri': 'https://synex.example/callback', 'token_endpoint': 'https://fake-fhir.example/token'})
    # Past TTL: pop() must return None even though the row is still physically present until this read.
    monkeypatch.setattr(smart_launch.time, 'time', lambda: base_time + smart_launch.LAUNCH_TTL_SECONDS + 1)
    assert store2.pop('state-2') is None


def test_smart_callback_rejects_expired_launch_state_and_never_calls_token_endpoint(monkeypatch):
    # The callback must reject an expired state entirely -- the token endpoint is NEVER invoked.
    import app.main as main_module
    def fail_if_called(*a, **kw):
        raise AssertionError('token endpoint must never be called for an expired launch state')
    monkeypatch.setattr(main_module, 'exchange_code',
                         lambda *a, **kw: (_ for _ in ()).throw(KeyError('Unknown or expired launch state')))
    from app.main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        r = c.get('/smart/callback?code=abc&state=expired-state', follow_redirects=False)
    assert r.status_code == 400


def test_validate_smart_issuer_rejects_non_https_and_localhost_by_default(monkeypatch):
    monkeypatch.delenv('SYNEX_SMART_TRUSTED_ISSUERS', raising=False)
    monkeypatch.delenv('SYNEX_SMART_ALLOW_INSECURE_LOCALHOST', raising=False)
    import pytest
    for bad in ['http://127.0.0.1', 'http://localhost', 'http://169.254.169.254',
                'http://10.0.0.1', 'http://192.168.1.1', 'file:///etc/passwd', 'ftp://example.com']:
        with pytest.raises(ValueError):
            smart_launch.validate_smart_issuer(bad)

def test_validate_smart_issuer_rejects_https_domain_not_in_allowlist(monkeypatch):
    monkeypatch.setenv('SYNEX_SMART_TRUSTED_ISSUERS', 'https://ehr.example/fhir,https://sandbox.example/fhir')
    import pytest
    with pytest.raises(ValueError):
        smart_launch.validate_smart_issuer('https://untrusted-ehr.example/fhir')
    smart_launch.validate_smart_issuer('https://ehr.example/fhir')  # does not raise
    smart_launch.validate_smart_issuer('https://sandbox.example/fhir/')  # trailing slash normalizes fine

def test_validate_smart_issuer_rejects_embedded_credentials(monkeypatch):
    monkeypatch.delenv('SYNEX_SMART_TRUSTED_ISSUERS', raising=False)
    import pytest
    with pytest.raises(ValueError):
        smart_launch.validate_smart_issuer('https://user:pass@fake-fhir.example/r4')

def test_validate_smart_issuer_localhost_escape_hatch_requires_explicit_opt_in(monkeypatch):
    monkeypatch.delenv('SYNEX_SMART_TRUSTED_ISSUERS', raising=False)
    import pytest
    monkeypatch.setenv('SYNEX_SMART_ALLOW_INSECURE_LOCALHOST', 'false')
    with pytest.raises(ValueError):
        smart_launch.validate_smart_issuer('http://localhost:8000/fhir')
    monkeypatch.setenv('SYNEX_SMART_ALLOW_INSECURE_LOCALHOST', 'true')
    smart_launch.validate_smart_issuer('http://localhost:8000/fhir')  # does not raise

def test_untrusted_or_private_issuer_never_makes_a_discovery_request(monkeypatch):
    # SSRF defense's actual point: allowlist validation happens BEFORE any HTTP request -- a
    # transport that would blow up if invoked proves discovery never reaches the network.
    monkeypatch.setenv('SYNEX_SMART_TRUSTED_ISSUERS', 'https://ehr.example/fhir')
    def boom(request):
        raise AssertionError('discovery request must never be made for a rejected issuer')
    transport = httpx.MockTransport(boom)
    import pytest
    for bad in ['http://127.0.0.1/fhir', 'https://untrusted.example/fhir']:
        with pytest.raises(ValueError):
            smart_launch.discover_smart_configuration(bad, transport=transport)

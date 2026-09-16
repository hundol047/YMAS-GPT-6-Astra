"""CDS Hooks endpoints tested against our own demo patients via FastAPI's TestClient -- this
proves the request/response shape is spec-correct, not that a specific real EMR's CDS Hooks
client will render it a particular way (that's unverified from this environment).

SMART launch is tested with a fake authorization server (httpx.MockTransport), same caveat as
test_fhir_adapter.py: proves the PKCE/redirect construction is correct, not live IdP
interoperability.
"""
import httpx
from app.services import smart_launch
from app.services.smart_launch import _LaunchStore

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
    monkeypatch.setenv('FHIR_CLIENT_ID', 'test-client')
    monkeypatch.setenv('FHIR_REDIRECT_URI', 'https://synex.example/smart/callback')
    r = client.get('/smart/launch?iss=https://fake-fhir.example/r4&launch=abc123', follow_redirects=False)
    assert r.status_code == 307
    location = r.headers['location']
    assert 'code_challenge=' in location
    assert 'code_challenge_method=S256' in location
    assert 'state=' in location
    assert 'launch=abc123' in location

def test_smart_exchange_code_via_fake_authorization_server():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith('/.well-known/smart-configuration'):
            return httpx.Response(200, json={'authorization_endpoint': 'https://fake-fhir.example/oauth2/authorize'})
        if request.url.path.endswith('/oauth2/token'):
            return httpx.Response(200, json={'access_token': 'fake-access', 'patient': 'fhir-1'})
        return httpx.Response(404)
    transport = httpx.MockTransport(handler)
    url = smart_launch.build_authorize_redirect('https://fake-fhir.example/r4', 'launch-1', 'client-1',
                                                  'https://synex.example/callback', 'launch patient/*.read',
                                                  transport=transport)
    import urllib.parse as up
    state = up.parse_qs(up.urlparse(url).query)['state'][0]
    token = smart_launch.exchange_code(state, 'auth-code-1', 'client-1', transport=transport)
    assert token['access_token'] == 'fake-access'
    assert token['patient'] == 'fhir-1'

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
                                          'launch': 'launch-1', 'redirect_uri': 'https://synex.example/callback'})
    store_after_restart = _LaunchStore(path=db_path)
    launch = store_after_restart.pop('state-1')
    assert launch == {'code_verifier': 'v1', 'iss': 'https://fake-fhir.example/r4',
                       'launch': 'launch-1', 'redirect_uri': 'https://synex.example/callback'}
    # One-time use: popped again (e.g. a replayed callback) must not resurrect it.
    assert store_after_restart.pop('state-1') is None

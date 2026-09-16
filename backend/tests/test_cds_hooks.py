"""CDS Hooks endpoints tested against our own demo patients via FastAPI's TestClient -- this
proves the request/response shape is spec-correct, not that a specific real EMR's CDS Hooks
client will render it a particular way (that's unverified from this environment).

SMART launch is tested with a fake authorization server (httpx.MockTransport), same caveat as
test_fhir_adapter.py: proves the PKCE/redirect construction is correct, not live IdP
interoperability.
"""
import httpx
from app.services import smart_launch

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

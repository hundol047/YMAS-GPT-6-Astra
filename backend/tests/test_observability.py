def test_health_subsystems_reports_every_component(client):
    r = client.get('/health/subsystems')
    assert r.status_code == 200
    body = r.json()
    for key in ('emr', 'terminology', 'rule_engine', 'ai_model', 'auth', 'imaging'):
        assert key in body and 'status' in body[key]
    assert body['emr']['mode'] == 'demo'
    assert body['imaging']['status'] == 'not_configured'
    assert body['ai_model']['status'] == 'ok'

def test_health_subsystems_response_has_no_patient_fields(client):
    r = client.get('/health/subsystems')
    text = r.text.lower()
    for leaked in ('patient_id', 'diagnosis', 'allerg', 'syn-00'):
        assert leaked not in text

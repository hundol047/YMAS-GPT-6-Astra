def test_alert_breakdown_endpoint_returns_descriptive_counts_not_accuracy(client):
    r = client.get('/validation/alert-breakdown')
    assert r.status_code == 200
    body = r.json()
    assert body['patients_evaluated'] == 5
    assert 'sensitivity' not in body and 'accuracy' not in body  # must stay descriptive, not a circular metric
    assert 'caveat' in body

def test_alert_fatigue_endpoint(client):
    client.post('/agent/analyze', json={'patient_id': 'SYN-002'})
    r = client.get('/validation/alert-fatigue')
    assert r.status_code == 200
    assert 'SYN-002' in r.json()['per_patient']
    assert r.json()['per_patient']['SYN-002']['detected'] >= 1

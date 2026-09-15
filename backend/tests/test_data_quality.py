from datetime import date
from app.services.data_quality import assess
from app.services.emr_adapter import DemoAdapter

def test_missing_allergy_and_condition_surfaced_not_hidden():
    p = DemoAdapter().get('SYN-001')  # no conditions, no allergies in the demo dataset
    q = assess(p)
    assert q['allergy'] == 'MISSING'
    assert q['condition'] == 'MISSING'
    assert any(g['field'] == 'allergy' and g['status'] == 'MISSING' for g in q['gaps'])

def test_stale_lab_flagged_against_prototype_policy_only():
    p = DemoAdapter().get('SYN-002')
    q = assess(p, today=date(2030, 1, 1))  # force every lab far in the past
    stale = [name for name, info in q['labs'].items() if info['status'] == 'STALE']
    assert stale, 'expected at least one lab to be flagged stale when evaluated far in the future'
    for name in stale:
        assert q['labs'][name]['policy_source'] is not None

def test_lab_with_no_policy_entry_is_never_marked_stale():
    p = DemoAdapter().get('SYN-004')
    q = assess(p, today=date(2030, 1, 1))
    for name, info in q['labs'].items():
        if info['policy_max_age_days'] is None:
            assert info['status'] != 'STALE'

def test_endpoint(client):
    r = client.get('/patients/SYN-002/data-quality')
    assert r.status_code == 200
    assert r.json()['patient_id'] == 'SYN-002'

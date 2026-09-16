from app.services.anatomy import build_anatomy, organ_matches
from app.services.emr_adapter import DemoAdapter
from app.services.rule_engine import evaluate
from fastapi.testclient import TestClient
from app.main import app


def test_deterministic_and_no_lesions():
    patient = DemoAdapter().get('SYN-005')
    alerts = evaluate(patient)['alerts']
    first = build_anatomy(patient, alerts)
    assert first == build_anatomy(patient, list(alerts))
    assert any(t['organ_id']=='kidneys' and t['severity']=='caution' for t in first['targets'])
    assert first['imaging_available'] is False
    assert first['model_score_localized'] is False
    for t in first['targets'] + first['systemic']:
        assert 'coordinates' not in t
        assert t['confidence']=='clinical_relevance'


def test_systemic_interactions_and_allergy():
    patient = DemoAdapter().get('SYN-005')
    base = {'id':'a','title':'Warfarin + aspirin','type':'drug_interaction',
            'reason':'GI bleeding risk', 'drugs':['warfarin','aspirin'],
            'source':'test', 'severity':'danger'}
    result = build_anatomy(patient, [base])
    assert result['systemic'][0]['alert_id']=='a'
    assert not any(t['alert_id']=='a' for t in result['targets'])
    base.update(type='allergy', reason='respiratory reaction')
    assert build_anatomy(patient,[base])['systemic'][0]['localization']=='systemic'


def test_boundaries_and_multiple_targets():
    assert organ_matches('last visit digoxin potassium')==[]
    assert organ_matches('eGFR and ALT')==['kidneys','liver']
    assert organ_matches('신기능 저하')==['kidneys']


def test_no_signal():
    p=DemoAdapter().get('SYN-005').model_copy(deep=True)
    p.conditions=[];p.labs=[];p.allergies=[];p.medications=[]
    result=build_anatomy(p,evaluate(p)['alerts'])
    assert result['targets']==result['systemic']==[]


def test_endpoint_and_simulation_are_consistent():
    with TestClient(app) as client:
        result=client.get('/patients/SYN-005/anatomy').json()
        analysis=client.post('/agent/analyze',json={'patient_id':'SYN-005'}).json()
        assert result==analysis['anatomy']
        assert client.get('/patients/unknown/anatomy').status_code==404
        sim=client.post('/prescription/simulate',json={'patient_id':'SYN-001','drug_id':'aspirin'}).json()
        assert 'anatomy' in sim['after']
        assert sim['original_unchanged']
        assert client.get('/patients/SYN-001/anatomy').json()==sim['before']['anatomy']

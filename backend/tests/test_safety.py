import hashlib,json,sys,subprocess
from pathlib import Path
import pytest
from app.schemas import Patient,Medication,Allergy,RiskFeatures
from app.services.rule_engine import evaluate
from app.services.feature_engineering import features_for
from app.services.emr_adapter import DemoAdapter
from app.services.audit import AuditStore

def analyze(c,pid):
    r=c.post('/agent/analyze',json={'patient_id':pid});assert r.status_code==200;return r.json()

def test_case_1_low(client):
    a=analyze(client,'SYN-001');assert a['risk']['risk_probability']<.1;assert not a['alerts']

def test_case_2_interaction(client):
    a=analyze(client,'SYN-002');assert a['risk']['risk_probability']>.5
    assert any(x['type']=='drug_interaction' and x['severity']=='danger' for x in a['alerts'])

def test_case_3_polypharmacy_without_interaction(client):
    a=analyze(client,'SYN-003');assert a['training_counts']=={'danger':0,'caution':0}
    assert a['risk']['risk_probability']>.5
    assert any(x['type']=='polypharmacy' for x in a['alerts'])

def test_case_4_severe_history(client):
    a=analyze(client,'SYN-004');assert a['risk']['risk_probability']>.5
    assert a['risk']['features']['adverse_history']==1
    assert any(x['type']=='adverse_history' for x in a['alerts'])

def test_case_5_three_cautions(client):
    p=DemoAdapter().get('SYN-001')
    p.medications=[Medication(drug_id=d,dispenses=3) for d in ['metformin','lisinopril','furosemide']]
    p.conditions=['만성신부전'];a=client.post('/medication-check',json=p.model_dump(mode='json')).json()
    assert a['training_counts']=={'danger':0,'caution':3}
    assert a['risk']['features']['drug_conflict']==.6
    assert a['risk']['risk_probability']>.5

def test_case_6_repeat_30(client):
    f=analyze(client,'SYN-002')['risk']['features']
    values=[client.post('/predict',json=f).json()['risk_probability'] for _ in range(30)]
    assert len(set(values))==1

def test_case_7_simulation_recomputes_without_mutation(client):
    original=client.get('/patients/SYN-001').json()
    s=client.post('/prescription/simulate',json={'patient_id':'SYN-001','drug_id':'warfarin'}).json()
    assert s['after']['risk']['features']['polypharmacy_load']==.2
    assert s['before']['risk']['features']['polypharmacy_load']==.1
    assert s['delta_percentage_points']==pytest.approx((s['after']['risk']['risk_probability']-s['before']['risk']['risk_probability'])*100)
    assert client.get('/patients/SYN-001').json()==original
    # Allergy provoking simulation sharply changes a low-risk (non-severe) case through rules.
    p=DemoAdapter().get('SYN-001');p.allergies=[Allergy(substance='페니실린',severity='MILD')]
    baseline=client.post('/medication-check',json=p.model_dump(mode='json')).json()
    p.medications.append(Medication(drug_id='amoxicillin',dispenses=1))
    after=client.post('/medication-check',json=p.model_dump(mode='json')).json()
    assert after['risk']['risk_probability']>baseline['risk']['risk_probability']
    assert any(a['type']=='allergy' for a in after['alerts'])

def test_review_is_persistent_and_scoped(client):
    a=analyze(client,'SYN-002');body={'analysis_id':a['analysis_id'],'alert_id':a['alerts'][0]['id'],'action':'reviewed','reason':'가상 사례 검토'}
    assert client.post('/reviews',json=body).status_code==200
    events=client.get('/audit/SYN-002').json();assert any(e['event']=='alert_reviewed' for e in events)
    from app.main import app
    reopened=AuditStore(app.state.audit.path);assert any(e['event']=='alert_reviewed' for e in reopened.list('SYN-002'))
    body['alert_id']='wrong';assert client.post('/reviews',json=body).status_code==404
    body['reason']='';assert client.post('/reviews',json=body).status_code==422

def test_missing_and_unknown_data_visible(client):
    p=DemoAdapter().get('SYN-001');p.medications.append(Medication(drug_id='unmapped_drug'));p.medications[0].dispenses=None
    p.allergies=[Allergy(substance='unknown',severity='UNKNOWN')]
    a=client.post('/medication-check',json=p.model_dump(mode='json')).json()
    assert a['data_status']=='incomplete';assert len(a['missing'])>=3
    assert a['risk']['features']['adverse_history']==0

def test_contract_validation(client):
    assert client.post('/predict',json={'drug_conflict':0}).status_code==422
    f=analyze(client,'SYN-001')['risk']['features'];f['age_risk']=2
    assert client.post('/predict',json=f).status_code==422
    f['age_risk']=.5;f['allergy_flag']=.3
    assert client.post('/predict',json=f).status_code==422
    assert client.post('/prescription/simulate',json={'patient_id':'SYN-001','drug_id':'missing'}).status_code==422
    assert client.post('/prescription/simulate',json={'patient_id':'SYN-001','drug_id':'vitamind'}).status_code==409
    assert client.get('/patients/not-found').status_code==404

def test_features_match_original_training_audit(monkeypatch):
    original=Path(__file__).resolve().parents[2]/'research'/'original'
    monkeypatch.chdir(original);monkeypatch.syspath_prepend(str(original))
    import build_dataset_v2 as old
    for p in DemoAdapter().list():
        ids={m.drug_id for m in p.medications};allergies={a.substance for a in p.allergies}
        expected=old.audit(ids,set(p.conditions),allergies);rules=evaluate(p)
        assert rules['danger_count']==expected.count('위험')
        assert rules['caution_count']==expected.count('주의')
        f,_=features_for(p,rules)
        assert f.drug_conflict==round(min(1,expected.count('위험')*.5+expected.count('주의')*.2),3)

def test_severity_exact_mapping():
    p=DemoAdapter().get('SYN-001')
    for severity,score in [('NONE',0),('MILD',.34),('MODERATE',.67),('SEVERE',1)]:
        p.allergies=[Allergy(substance='test',severity=severity)]
        f,_=features_for(p,evaluate(p));assert f.adverse_history==score

def test_stopped_meds_and_extra_alerts_dont_pollute_counts(client):
    p=DemoAdapter().get('SYN-002');p.medications[1].status='stopped'
    a=client.post('/medication-check',json=p.model_dump(mode='json')).json()
    assert a['training_counts']=={'danger':0,'caution':0}
    assert a['risk']['features']['drug_conflict']==0
    assert any(x['type']=='lab_review' for x in a['alerts'])

def test_duplicate_ingredient_detected(client):
    p=DemoAdapter().get('SYN-001');p.medications.append(p.medications[0].model_copy())
    a=client.post('/medication-check',json=p.model_dump(mode='json')).json()
    assert any(x['type']=='duplicate_ingredient' for x in a['alerts'])
    assert a['risk']['features']['polypharmacy_load']==.1

def test_health_model_integrity_and_fhir(client):
    r=client.get('/health').json();assert r['model_loaded'];assert r['input']['shape']==['batch',7]
    p=Path(__file__).resolve().parents[2];original=p/'research/original/risk_model_deep_v3.onnx'
    assert r['model_sha256']==hashlib.sha256(original.read_bytes()).hexdigest()
    b=client.get('/patients/SYN-001/fhir').json();assert b['resourceType']=='Bundle'
    assert {'Patient','MedicationStatement','Observation'}<={e['resource']['resourceType'] for e in b['entry']}

def test_sse_real_results(client):
    r=client.get('/agent/stream/SYN-002');assert r.status_code==200
    assert r.text.count('event: step')==8;assert r.text.count('event: result')==1
    payload=json.loads(r.text.split('event: result\ndata: ')[1].strip())
    assert payload['risk']['risk_probability']>.5

def test_cors_and_production_entry(client):
    r=client.options('/predict',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'POST'})
    assert r.headers['access-control-allow-origin']=='http://localhost:5173'
    r=client.options('/predict',headers={'Origin':'https://untrusted.example','Access-Control-Request-Method':'POST'})
    assert 'access-control-allow-origin' not in r.headers
    r=client.get('/');assert r.status_code==200;assert 'SynexAgent' in r.text

def test_cors_allows_patch_and_authorization_header(client):
    # Regression test: PATCH Encounter/PATCH Clinical Note and the OIDC Authorization header used
    # to be blocked by CORS (allow_methods was GET/POST only, allow_headers was Content-Type only).
    r=client.options('/encounters/ENC-1',headers={'Origin':'http://localhost:5173',
        'Access-Control-Request-Method':'PATCH','Access-Control-Request-Headers':'authorization'})
    assert r.headers['access-control-allow-origin']=='http://localhost:5173'
    assert 'PATCH' in r.headers['access-control-allow-methods']
    assert 'authorization' in r.headers['access-control-allow-headers'].lower()

def test_cors_allows_credentials_for_session_cookie(client):
    # The synex_session HttpOnly cookie (SMART on FHIR context, SSE auth) needs allow_credentials
    # so the browser will actually send it on a cross-origin dev request.
    r=client.options('/predict',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'POST'})
    assert r.headers.get('access-control-allow-credentials')=='true'

def test_cors_wildcard_origin_with_credentials_is_refused_at_startup():
    from app.main import resolve_cors_config
    import pytest as _pytest
    with _pytest.raises(RuntimeError):
        resolve_cors_config(cors_origins_env='*', allow_credentials_env='true')
    # Explicitly turning credentials off makes a wildcard origin fine again (no cookie/token ever
    # sent, so there's nothing for a malicious origin to piggyback on).
    origins,allow_credentials=resolve_cors_config(cors_origins_env='*', allow_credentials_env='false')
    assert origins==['*'] and allow_credentials is False
    # The actual production default: explicit origins, credentials on.
    origins,allow_credentials=resolve_cors_config(cors_origins_env='https://emr.example.org', allow_credentials_env='true')
    assert origins==['https://emr.example.org'] and allow_credentials is True

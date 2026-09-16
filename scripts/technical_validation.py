"""Technical Validation (section A, as distinct from Clinical/Retrospective Validation, section B).

Checks each subsystem actually works end-to-end against this deployment:
  - FHIR parsing        (FHIRAdapter against a fake FHIR server)
  - Terminology mapping (RxNorm/LOINC/ICD-10 lookups)
  - Rule execution      (rule_engine.evaluate on every demo patient)
  - ONNX inference      (RiskEngine health + a real prediction)
  - API correctness     (every route this script touches responds with the expected shape)
  - Provider fallback   (ONNX Runtime provider actually selected vs. requested)

This is a real smoke test, not a mock report: every check either runs real code and asserts on
its output, or is explicitly marked SKIPPED with why. Run it after any deployment, including on
new hardware, before trusting the service.

Usage: python3 scripts/technical_validation.py
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

results = []

def check(name, fn):
    try:
        detail = fn()
        results.append({'check': name, 'status': 'PASS', 'detail': detail})
    except Exception as e:
        results.append({'check': name, 'status': 'FAIL', 'detail': str(e)})


def check_onnx_inference():
    from app.services.risk_inference import RiskEngine
    from app.schemas import RiskFeatures
    engine = RiskEngine()
    health = engine.health()
    assert health['model_loaded'], 'model did not load'
    pred = engine.predict(RiskFeatures(drug_conflict=1, comorbidity_load=0, age_risk=.5, allergy_flag=0,
                                        adverse_history=0, polypharmacy_load=0, therapy_duration_load=0))
    assert 0 <= pred['risk_probability'] <= 1
    return {'providers': health['providers'], 'fallback_reason': health['fallback_reason'],
            'sample_prediction': pred['risk_probability']}

def check_rule_execution():
    from app.services.emr_adapter import DemoAdapter
    from app.services.rule_engine import evaluate
    patients = DemoAdapter().list()
    assert patients, 'no demo patients loaded'
    counts = {}
    for p in patients:
        r = evaluate(p)
        counts[p.id] = len(r['alerts'])
    return counts

def check_terminology_mapping():
    from app.services.terminology_mapper import normalize_medication, normalize_lab
    known = normalize_medication('warfarin', 'warfarin')
    unknown = normalize_medication('definitely-not-a-real-id', 'x')
    assert known.mapping_status == 'mapped'
    assert unknown.mapping_status == 'unmapped', 'unknown drug must not be silently mapped'
    lab = normalize_lab('eGFR')
    assert lab.mapping_status == 'mapped'
    return {'known_rxnorm': known.target_code, 'unknown_status': unknown.mapping_status}

def check_fhir_parsing():
    import httpx
    from app.services.emr_adapter import FHIRAdapter
    def handler(request):
        if request.url.path.endswith('/Patient/smoke-1'):
            return httpx.Response(200, json={'resourceType': 'Patient', 'id': 'smoke-1',
                                              'name': [{'text': 'Smoke Test'}], 'gender': 'male', 'birthDate': '1980-01-01'})
        return httpx.Response(200, json={'resourceType': 'Bundle', 'entry': []})
    adapter = FHIRAdapter(base_url='https://fake.invalid/r4', transport=httpx.MockTransport(handler))
    p = adapter.get('smoke-1')
    assert p is not None and p.name == 'Smoke Test'
    return {'parsed_name': p.name, 'parsed_sex': p.sex, 'missing_fields_reported': p.missing}

def check_api_correctness():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        health = c.get('/health');assert health.status_code == 200
        patients = c.get('/patients');assert patients.status_code == 200 and len(patients.json()) > 0
        analyze = c.post('/agent/analyze', json={'patient_id': patients.json()[0]['id']})
        assert analyze.status_code == 200 and 'risk_probability' in analyze.json()['risk']
        cds = c.get('/cds-services');assert cds.status_code == 200
    return {'health': health.status_code, 'patients': patients.status_code, 'analyze': analyze.status_code, 'cds_services': cds.status_code}


check('ONNX inference + provider selection', check_onnx_inference)
check('Rule execution on every demo patient', check_rule_execution)
check('Terminology mapping (mapped vs. honestly unmapped)', check_terminology_mapping)
check('FHIR parsing against a fake FHIR server', check_fhir_parsing)
check('API correctness (health/patients/analyze/cds-services)', check_api_correctness)

print(json.dumps({'results': results,
                  'summary': {'pass': sum(1 for r in results if r['status'] == 'PASS'),
                              'fail': sum(1 for r in results if r['status'] == 'FAIL'),
                              'total': len(results)},
                  'note': 'This validates the code paths run correctly in THIS environment. It does not '
                          'validate interoperability with any specific real hospital FHIR server, IdP, or '
                          'EMR CDS Hooks client -- see backend/app/services/*.py docstrings for what remains '
                          'unverified against a live system.'}, indent=2, ensure_ascii=False))
sys.exit(1 if any(r['status'] == 'FAIL' for r in results) else 0)

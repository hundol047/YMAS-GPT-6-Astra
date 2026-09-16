from app.services.terminology_mapper import normalize_medication, normalize_lab, normalize_condition, patient_terminology
from app.services.rule_engine import DRUGS

def test_known_medication_maps_to_rxnorm():
    r = normalize_medication('warfarin', '와파린')
    assert r.mapping_status == 'mapped'
    assert r.target_system == 'RxNorm'
    assert r.target_code == '11289'

def test_demo_patient_only_medications_are_mapped():
    # backend/data/patients.json uses these drug_ids; before rule_engine's terminology table was
    # extended, 6 of them (acetaminophen/albuterol/haloperidol/lisinopril/lorazepam/simvastatin)
    # had no RxNorm/ATC row at all, so real demo patients silently under-reported coverage.
    for drug_id in ('acetaminophen', 'albuterol', 'haloperidol', 'lisinopril', 'lorazepam', 'simvastatin'):
        r = normalize_medication(drug_id, drug_id)
        assert r.mapping_status == 'mapped', drug_id

def test_unknown_medication_is_unmapped_not_guessed():
    r = normalize_medication('not-a-real-drug-id', 'x')
    assert r.mapping_status == 'unmapped'
    assert r.target_code is None

def test_known_lab_maps_to_loinc():
    r = normalize_lab('eGFR')
    assert r.mapping_status == 'mapped'
    assert r.target_system == 'LOINC'
    assert r.target_code == '33914-3'

def test_unknown_lab_is_unmapped():
    r = normalize_lab('Nonexistent Panel')
    assert r.mapping_status == 'unmapped'

def test_known_condition_maps_to_icd10_and_snomed():
    codes = normalize_condition('만성신부전')
    systems = {c.target_system for c in codes}
    assert 'ICD-10' in systems and 'SNOMED CT' in systems
    icd = next(c for c in codes if c.target_system == 'ICD-10')
    assert icd.target_code == 'N18.9'

def test_patient_terminology_endpoint(client):
    r = client.get('/patients/SYN-002/terminology')
    assert r.status_code == 200
    body = r.json()
    assert body['patient_id'] == 'SYN-002'
    assert body['coverage']['medications_mapped'] >= 1
    assert any(m['rxnorm']['mapping_status'] == 'mapped' for m in body['medications'])

def test_patient_terminology_unknown_patient_404(client):
    r = client.get('/patients/NOPE/terminology')
    assert r.status_code == 404

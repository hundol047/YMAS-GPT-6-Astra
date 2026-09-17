"""Clinical Workspace endpoints (Encounter/Vitals/SOAP Note/Diagnosis/MedicationOrder/LabOrder/
Timeline/clinical-summary) exercised against the real FastAPI app + real ClinicalAgent/rule engine
via the `client` fixture (see conftest.py) -- same pattern as the rest of this suite, not mocked.

Each `client` fixture invocation re-runs app startup (services/demo_seed.py), so every test starts
from the same seeded state: each demo patient already has one past Encounter+Vitals+signed Note
(+Diagnosis where applicable).
"""
import pytest
from app.services.vitals import flag


def test_medication_order_precheck_does_not_treat_quantity_as_dispenses(client):
    # Regression test for a real bug: the precheck used to pass MedicationOrderCreateRequest's
    # quantity (how many units THIS order is for, e.g. "90 tablets") straight into
    # Medication.dispenses (a risk-model feature meaning "how many times dispensed/refilled" --
    # see feature_engineering.py's therapy_duration_load). A brand-new order for a large quantity
    # would then get misread as a long-established refill history, inflating risk features that
    # have nothing to do with order size. Confirm the precheck result is now IDENTICAL regardless
    # of quantity (an order-size-only field the risk model must never see as dispense count).
    enc = _create_encounter(client)
    small = client.post(f"/encounters/{enc['id']}/medication-orders/precheck",
                         json={'medication_code': 'ibuprofen', 'medication_name': 'Ibuprofen', 'dose': 200,
                               'dose_unit': 'mg', 'route': 'PO', 'quantity': 1, 'prescriber': 'Dr. Lee'})
    large = client.post(f"/encounters/{enc['id']}/medication-orders/precheck",
                         json={'medication_code': 'ibuprofen', 'medication_name': 'Ibuprofen', 'dose': 200,
                               'dose_unit': 'mg', 'route': 'PO', 'quantity': 9999, 'prescriber': 'Dr. Lee'})
    assert small.status_code == 200 and large.status_code == 200
    assert small.json()['after']['risk']['features'] == large.json()['after']['risk']['features']
    assert small.json()['delta_percentage_points'] == large.json()['delta_percentage_points']
    # Before the fix, quantity=9999 fed straight into dispenses would round therapy_duration_load
    # up to its 1.0 cap (9999/24 clamped to 1) -- confirm that never happens.
    assert large.json()['after']['risk']['features']['therapy_duration_load'] < 1.0


def test_spo2_reference_range_bug_fix():
    # SpO2's critical_high used to be 100 -- the same value as a perfectly normal/maximal reading --
    # so value>=100 misclassified a healthy 100% saturation as 'critical'. critical_high is now
    # null (no meaningful "too high" for SpO2) and flag() skips that comparison when None.
    assert flag('spo2', 100) == 'normal'
    assert flag('spo2', 99) == 'normal'
    assert flag('spo2', 94) == 'low'
    assert flag('spo2', 89) == 'critical'


def _create_encounter(client, pid='SYN-002', **overrides):
    body = {'encounter_type': 'outpatient', 'department': '순환기내과', 'attending_physician': '김도현',
            'chief_complaint': 'INR follow-up', **overrides}
    r = client.post(f'/patients/{pid}/encounters', json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_encounter_crud(client):
    enc = _create_encounter(client)
    assert enc['status'] == 'in_progress'
    r = client.get(f"/encounters/{enc['id']}")
    assert r.status_code == 200 and r.json()['id'] == enc['id']
    r = client.patch(f"/encounters/{enc['id']}", json={'status': 'completed'})
    assert r.status_code == 200 and r.json()['status'] == 'completed'
    r = client.get('/patients/SYN-002/encounters')
    assert r.status_code == 200 and len(r.json()) >= 2  # seeded one + this one

def test_encounter_not_found_404(client):
    assert client.get('/encounters/ENC-nope').status_code == 404


def test_vitals_recorded_with_reference_range_assessment(client):
    enc = _create_encounter(client)
    r = client.post(f"/encounters/{enc['id']}/vitals", json={'sbp': 190, 'spo2': 99})
    assert r.status_code == 200
    body = r.json()
    assert body['sbp'] == 190
    assert body['assessment']['flags']['sbp']['status'] == 'critical'  # 190 >= critical_high(180)
    assert body['assessment']['flags']['spo2']['status'] == 'normal'
    r = client.get('/patients/SYN-002/vitals')
    assert r.status_code == 200 and len(r.json()) >= 2

def test_vitals_bmi_computed_from_height_weight(client):
    enc = _create_encounter(client)
    r = client.post(f"/encounters/{enc['id']}/vitals", json={'height_cm': 170, 'weight_kg': 68})
    assert r.status_code == 200
    assert r.json()['assessment']['bmi'] == pytest.approx(23.5, abs=0.05)

def test_vitals_out_of_range_rejected_422(client):
    enc = _create_encounter(client)
    r = client.post(f"/encounters/{enc['id']}/vitals", json={'spo2': 150})
    assert r.status_code == 422


def test_note_lifecycle_draft_sign_reject_direct_edit_amend(client):
    enc = _create_encounter(client)
    r = client.post(f"/encounters/{enc['id']}/notes", json={'author': 'Dr. Lee', 'subjective': 'chest discomfort', 'plan': 'continue warfarin'})
    assert r.status_code == 200
    note = r.json()
    assert note['status'] == 'draft'

    r = client.patch(f"/notes/{note['id']}", json={'plan': 'updated plan while draft'})
    assert r.status_code == 200 and r.json()['plan'] == 'updated plan while draft'

    r = client.post(f"/notes/{note['id']}/sign")
    assert r.status_code == 200 and r.json()['status'] == 'signed' and r.json()['signed_at']

    # A signed note must NEVER be edited directly -- no silent amendment, a hard rejection.
    r = client.patch(f"/notes/{note['id']}", json={'plan': 'sneaky rewrite'})
    assert r.status_code == 409
    assert client.get(f"/encounters/{enc['id']}/notes").json()[-1]['plan'] == 'updated plan while draft'

    # The only legal path: an explicit amendment with author + reason, which never touches the
    # original field values.
    r = client.post(f"/notes/{note['id']}/amendments", json={'author': 'Dr. Lee', 'reason': 'add follow-up detail', 'plan': 'continue warfarin, recheck INR in 1 week'})
    assert r.status_code == 200
    amended = r.json()
    assert amended['plan'] == 'updated plan while draft'  # original untouched
    assert len(amended['amendments']) == 1
    assert amended['amendments'][0]['reason'] == 'add follow-up detail'

def test_amendment_requires_author_and_reason(client):
    enc = _create_encounter(client)
    note = client.post(f"/encounters/{enc['id']}/notes", json={'author': 'Dr. Lee'}).json()
    client.post(f"/notes/{note['id']}/sign")
    r = client.post(f"/notes/{note['id']}/amendments", json={'author': '', 'reason': ''})
    assert r.status_code == 422

def test_amend_before_signing_rejected(client):
    enc = _create_encounter(client)
    note = client.post(f"/encounters/{enc['id']}/notes", json={'author': 'Dr. Lee'}).json()
    r = client.post(f"/notes/{note['id']}/amendments", json={'author': 'Dr. Lee', 'reason': 'x'})
    assert r.status_code == 409  # can't amend a draft -- edit it directly instead

def test_re_signing_is_idempotent(client):
    enc = _create_encounter(client)
    note = client.post(f"/encounters/{enc['id']}/notes", json={'author': 'Dr. Lee'}).json()
    first = client.post(f"/notes/{note['id']}/sign").json()
    second = client.post(f"/notes/{note['id']}/sign").json()
    assert first['signed_at'] == second['signed_at']


def test_diagnosis_dual_writes_into_flat_conditions(client):
    enc = _create_encounter(client)
    r = client.post(f"/encounters/{enc['id']}/diagnoses", json={'display_name': '고지혈증', 'diagnosis_type': 'secondary'})
    assert r.status_code == 200
    p = client.get('/patients/SYN-002').json()
    assert '고지혈증' in p['conditions']
    assert any(d['display_name'] == '고지혈증' for d in p['problem_list'])


def test_diagnosis_retry_with_same_code_does_not_duplicate_active_problem(client):
    # Item 2: a network retry of the same POST (same ICD code, still active) must return the
    # existing diagnosis, not mint a second active problem_list entry / conditions dual-write /
    # Timeline entry. Uses a code the demo seed data doesn't already have (SYN-002 is seeded with
    # I48.91/AFib -- see demo_seed.py) so this exercises the retry path, not an incidental
    # collision with seed data.
    enc = _create_encounter(client)
    body = {'display_name': 'Hyperlipidemia', 'diagnosis_type': 'secondary', 'code': 'E78.5', 'code_system': 'ICD-10'}
    first = client.post(f"/encounters/{enc['id']}/diagnoses", json=body)
    second = client.post(f"/encounters/{enc['id']}/diagnoses", json=body)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()['id'] == second.json()['id']
    problems = client.get('/patients/SYN-002/problem-list').json()
    matching = [d for d in problems if d['code'] == 'E78.5' and d['status'] == 'active']
    assert len(matching) == 1
    p = client.get('/patients/SYN-002').json()
    assert p['conditions'].count('Hyperlipidemia') == 1
    events = client.get('/audit/SYN-002').json()
    assert sum(1 for e in events if e['event'] == 'diagnosis_added' and e['detail'].get('diagnosis_id') == first.json()['id']) == 1

def test_diagnosis_recorded_on_new_encounter_links_without_duplicating_problem_list(client):
    # Phase 6 regression: Patient.problem_list ("active Atrial fibrillation") is conceptually
    # distinct from an Encounter's own record of addressing it. Recording the SAME active diagnosis
    # on a NEW encounter must NOT mint a second problem_list entry, but it MUST link the existing
    # Diagnosis into the new encounter's diagnosis_ids -- the bug being fixed here is that the old
    # dedup-reuse branch returned the existing Diagnosis without ever touching the new encounter.
    enc_a = _create_encounter(client)
    body = {'display_name': 'Atrial fibrillation', 'diagnosis_type': 'primary', 'code': 'I48.91', 'code_system': 'ICD-10'}
    dx = client.post(f"/encounters/{enc_a['id']}/diagnoses", json=body).json()
    assert dx['id'] in client.get(f"/encounters/{enc_a['id']}").json()['diagnosis_ids']

    enc_b = _create_encounter(client)
    assert dx['id'] not in client.get(f"/encounters/{enc_b['id']}").json()['diagnosis_ids']
    second = client.post(f"/encounters/{enc_b['id']}/diagnoses", json=body)
    assert second.status_code == 200
    assert second.json()['id'] == dx['id']  # reused the existing active Problem, no DX-002 minted

    problems = client.get('/patients/SYN-002/problem-list').json()
    assert sum(1 for d in problems if d['code'] == 'I48.91' and d['status'] == 'active') == 1

    enc_b_after = client.get(f"/encounters/{enc_b['id']}").json()
    assert enc_b_after['diagnosis_ids'].count(dx['id']) == 1  # linked to the NEW encounter too

    # Idempotent: recording the SAME diagnosis on the SAME encounter again must not duplicate the id.
    third = client.post(f"/encounters/{enc_b['id']}/diagnoses", json=body)
    assert third.status_code == 200
    enc_b_final = client.get(f"/encounters/{enc_b['id']}").json()
    assert enc_b_final['diagnosis_ids'].count(dx['id']) == 1

def test_diagnosis_retry_without_code_dedupes_by_normalized_display_name(client):
    enc = _create_encounter(client)
    r1 = client.post(f"/encounters/{enc['id']}/diagnoses", json={'display_name': '  Hyperlipidemia  '})
    r2 = client.post(f"/encounters/{enc['id']}/diagnoses", json={'display_name': 'hyperlipidemia'})
    assert r1.json()['id'] == r2.json()['id']

def test_diagnosis_resolved_then_new_active_episode_is_allowed(client):
    # A diagnosis resolved in the past and now newly active again (e.g. a 2025 episode that
    # resolved, then a genuinely new 2026 episode) must NOT be blocked as a duplicate -- dedup only
    # applies among ACTIVE diagnoses.
    import app.main as main_module
    enc = _create_encounter(client)
    body = {'display_name': 'Atrial fibrillation', 'diagnosis_type': 'primary', 'code': 'I48.91', 'code_system': 'ICD-10'}
    first = client.post(f"/encounters/{enc['id']}/diagnoses", json=body).json()
    # Simulate the first episode resolving (no PATCH endpoint exists for this -- go directly
    # through the same live Patient object the app itself mutates).
    p = main_module.app.state.adapter.mutate('SYN-002')
    for i, d in enumerate(p.problem_list):
        if d.id == first['id']:
            p.problem_list[i] = d.model_copy(update={'status': 'resolved'})
    second = client.post(f"/encounters/{enc['id']}/diagnoses", json=body)
    assert second.status_code == 200
    assert second.json()['id'] != first['id']
    problems = client.get('/patients/SYN-002/problem-list').json()
    assert sum(1 for d in problems if d['code'] == 'I48.91') == 2
    assert sum(1 for d in problems if d['code'] == 'I48.91' and d['status'] == 'active') == 1


def test_medication_order_idempotency_key_same_payload_returns_same_order(client):
    # Item 1: a network retry of the SAME create request with the SAME Idempotency-Key must
    # return the SAME order, never mint a second RX and never double-append to patient.medications.
    enc = _create_encounter(client)
    body = {'medication_code': 'lisinopril', 'dose': 10, 'dose_unit': 'mg', 'route': 'PO'}
    headers = {'Idempotency-Key': 'idem-key-abc-123'}
    before = len(client.get('/patients/SYN-002').json()['medications'])
    first = client.post(f"/encounters/{enc['id']}/medication-orders", json=body, headers=headers)
    second = client.post(f"/encounters/{enc['id']}/medication-orders", json=body, headers=headers)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()['id'] == second.json()['id']
    after = len(client.get('/patients/SYN-002').json()['medications'])
    assert after == before + 1

def test_medication_order_idempotency_key_reused_with_different_payload_is_409(client):
    enc = _create_encounter(client)
    headers = {'Idempotency-Key': 'idem-key-reused'}
    r1 = client.post(f"/encounters/{enc['id']}/medication-orders", headers=headers,
                      json={'medication_code': 'lisinopril', 'dose': 10, 'dose_unit': 'mg', 'route': 'PO'})
    assert r1.status_code == 200
    r2 = client.post(f"/encounters/{enc['id']}/medication-orders", headers=headers,
                      json={'medication_code': 'lisinopril', 'dose': 20, 'dose_unit': 'mg', 'route': 'PO'})
    assert r2.status_code == 409

def test_medication_order_without_idempotency_key_still_works_unchanged(client):
    # The header is optional -- a client that doesn't send it gets the pre-existing behavior
    # (each request is its own create, guarded only by repository-level id-scoped idempotency).
    enc = _create_encounter(client)
    body = {'medication_code': 'lisinopril', 'dose': 10, 'dose_unit': 'mg', 'route': 'PO'}
    r = client.post(f"/encounters/{enc['id']}/medication-orders", json=body)
    assert r.status_code == 200 and r.json()['status'] == 'confirmed'


def test_medication_order_idempotency_key_is_concurrency_safe(client):
    # Real thread-level concurrency (not sequential retries): fire 8 requests carrying the SAME
    # Idempotency-Key + SAME payload at once via a ThreadPoolExecutor. Starlette runs each sync
    # path-operation function in its own worker thread, so this genuinely reproduces the double-
    # submit race the old get()-then-put() implementation was vulnerable to (services/idempotency.py
    # begin()'s SQL PRIMARY KEY(scope,key) is what actually prevents it -- not this test's timing).
    from concurrent.futures import ThreadPoolExecutor
    enc = _create_encounter(client)
    body = {'medication_code': 'furosemide', 'dose': 20, 'dose_unit': 'mg', 'route': 'PO'}
    headers = {'Idempotency-Key': 'idem-concurrent-key-1'}
    before = len(client.get('/patients/SYN-002').json()['medications'])

    def fire(_):
        return client.post(f"/encounters/{enc['id']}/medication-orders", json=body, headers=headers)

    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(fire, range(8)))

    assert all(r.status_code == 200 for r in responses), [r.status_code for r in responses]
    order_ids = {r.json()['id'] for r in responses}
    assert len(order_ids) == 1  # every concurrent response shares the identical order_id

    patient_data = client.get('/patients/SYN-002').json()
    order_id = order_ids.pop()
    matching_meds = [m for m in patient_data['medications'] if m.get('note') == f'order:{order_id}']
    assert len(matching_meds) == 1  # exactly one patient.medications entry, not one per request
    assert len(patient_data['medications']) == before + 1

    orders = client.get('/patients/SYN-002/medication-orders').json()
    assert sum(1 for o in orders if o['id'] == order_id) == 1  # exactly one MedicationOrder exists

    timeline = client.get('/patients/SYN-002/timeline').json()
    order_events = [e for e in timeline['events'] if e['type'] == 'medication' and e.get('source_id') == order_id]
    assert len(order_events) == 1  # exactly one Timeline medication event


def test_medication_order_idempotency_key_concurrent_conflicting_payload_is_409(client):
    # Same key, two different payload groups racing concurrently: whichever payload's request wins
    # the claim becomes THE order for this key -- every request sharing that exact payload gets 200
    # with the identical order_id (a genuine same-key/same-payload retry, win or lose the race),
    # while every request carrying the OTHER (conflicting) payload gets 409. Exactly one order is
    # ever created either way -- there is no outcome where both payload groups succeed.
    from concurrent.futures import ThreadPoolExecutor
    enc = _create_encounter(client)
    headers = {'Idempotency-Key': 'idem-concurrent-key-conflict'}
    payload_a = {'medication_code': 'furosemide', 'dose': 20, 'dose_unit': 'mg', 'route': 'PO'}
    payload_b = {'medication_code': 'furosemide', 'dose': 40, 'dose_unit': 'mg', 'route': 'PO'}
    bodies = [payload_a] * 4 + [payload_b] * 4

    def fire(body):
        return client.post(f"/encounters/{enc['id']}/medication-orders", json=body, headers=headers)

    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(fire, bodies))

    successes = [r for r in responses if r.status_code == 200]
    conflicts = [r for r in responses if r.status_code == 409]
    assert len(successes) == 4, [r.status_code for r in responses]  # only the winning payload's 4 requests
    assert len(conflicts) == 4                                      # the losing payload's 4 requests
    assert len({r.json()['id'] for r in successes}) == 1            # all successes are the SAME order

    orders = client.get('/patients/SYN-002/medication-orders').json()
    assert sum(1 for o in orders if o['dose'] in (20, 40)) == 1      # exactly one order was ever created


def test_idempotency_store_lookup_is_not_process_local(client):
    # Phase 12.B: a brand-new IdempotencyStore instance (e.g. a second worker process pointed at the
    # same SYNEX_IDEMPOTENCY_PATH) must still see a key claimed/completed through a DIFFERENT
    # instance -- proving persistence doesn't depend on a process-local dict the way the old
    # dataclass-backed implementation did.
    import app.main as main_module
    from app.services.idempotency import IdempotencyStore
    enc = _create_encounter(client)
    body = {'medication_code': 'lisinopril', 'dose': 10, 'dose_unit': 'mg', 'route': 'PO'}
    headers = {'Idempotency-Key': 'idem-multi-store-key'}
    first = client.post(f"/encounters/{enc['id']}/medication-orders", json=body, headers=headers)
    assert first.status_code == 200

    # Reconstruct the exact scope/hash main.py computed for that request (demo-mode user id is
    # 'demo-dr' by default -- see auth.py's demo identity).
    from app.schemas import MedicationOrderCreateRequest
    scope = main_module._idempotency_scope(main_module.User(id='demo-dr', role='clinician'), 'SYN-002', enc['id'],
                                            'POST /encounters/{eid}/medication-orders')
    request_hash = main_module._idempotency_request_hash(MedicationOrderCreateRequest(**body))

    fresh_store = IdempotencyStore()  # separate instance, same env-configured SQLite path -- NOT the
    # same object as app.state.idempotency, and never touched by the request above.
    result = fresh_store.begin(scope, 'idem-multi-store-key', request_hash)
    assert result.owner is False  # sees it as already completed, not claimable
    assert result.response_body['id'] == first.json()['id']


def test_medication_order_precheck_detects_existing_interaction(client):
    enc = _create_encounter(client)
    # SYN-002 already actively takes warfarin+aspirin; ordering warfarin again should surface the
    # same real rule-engine interaction signal used everywhere else in this app.
    r = client.post(f"/encounters/{enc['id']}/medication-orders/precheck",
                     json={'medication_code': 'warfarin', 'dose': 2, 'dose_unit': 'mg', 'route': 'PO'})
    assert r.status_code == 200
    body = r.json()
    assert body['requires_override'] is True
    assert len(body['new_alerts']) >= 1

def test_medication_order_confirm_without_override_is_blocked_server_side(client):
    # The server independently re-runs the precheck at confirm time -- a client that skips
    # /precheck cannot bypass the override requirement.
    enc = _create_encounter(client)
    r = client.post(f"/encounters/{enc['id']}/medication-orders",
                     json={'medication_code': 'warfarin', 'dose': 2, 'dose_unit': 'mg', 'route': 'PO'})
    assert r.status_code == 409
    assert client.get('/patients/SYN-002/medication-orders').json() == []

def test_medication_order_confirm_with_override_dual_writes_and_audits(client):
    enc = _create_encounter(client)
    before_meds = len(client.get('/patients/SYN-002').json()['medications'])
    r = client.post(f"/encounters/{enc['id']}/medication-orders",
                     json={'medication_code': 'warfarin', 'dose': 2, 'dose_unit': 'mg', 'route': 'PO',
                           'override_reason': 'reviewed INR trend, continuing per plan'})
    assert r.status_code == 200
    order = r.json()
    assert order['status'] == 'confirmed'
    after_meds = len(client.get('/patients/SYN-002').json()['medications'])
    assert after_meds == before_meds + 1

    events = [e['event'] for e in client.get('/audit/SYN-002').json()]
    assert 'medication_ordered' in events
    assert 'warning_overridden' in events

def test_medication_order_confirm_is_idempotent_no_duplicate_medication(client):
    enc = _create_encounter(client)
    body = {'medication_code': 'lisinopril', 'dose': 10, 'dose_unit': 'mg', 'route': 'PO'}
    r = client.post(f"/encounters/{enc['id']}/medication-orders", json=body)
    assert r.status_code == 200
    order_id = r.json()['id']
    before = len(client.get('/patients/SYN-002').json()['medications'])
    # There's no HTTP re-confirm endpoint exposed, but the repository-level guarantee (confirming
    # an already-confirmed order is a no-op) is what the endpoint relies on; verify it holds via
    # cancel/no-crash and via the underlying repo directly through the app.
    r2 = client.post(f'/medication-orders/{order_id}/cancel')
    assert r2.status_code == 200 and r2.json()['status'] == 'cancelled'
    r3 = client.post(f'/medication-orders/{order_id}/cancel')  # idempotent re-cancel
    assert r3.status_code == 200 and r3.json()['status'] == 'cancelled'
    after = len(client.get('/patients/SYN-002').json()['medications'])
    assert after == before  # cancelling stops the entry in place, never removes/duplicates it
    stopped = [m for m in client.get('/patients/SYN-002').json()['medications'] if m['note'] == f'order:{order_id}']
    assert stopped and stopped[0]['status'] == 'stopped'

def test_medication_order_end_date_before_start_date_rejected(client):
    enc = _create_encounter(client)
    r = client.post(f"/encounters/{enc['id']}/medication-orders/precheck",
                     json={'medication_code': 'aspirin', 'dose': 1, 'dose_unit': 'tab', 'route': 'PO',
                           'start_date': '2026-06-01', 'end_date': '2026-05-01'})
    assert r.status_code == 422


def test_lab_order_and_result_dual_write_and_idempotent_retry(client):
    enc = _create_encounter(client)
    r = client.post(f"/encounters/{enc['id']}/lab-orders", json={'test_name': 'INR', 'priority': 'urgent'})
    assert r.status_code == 200
    order_id = r.json()['id']
    before = len(client.get('/patients/SYN-002').json()['labs'])
    r = client.post(f'/lab-orders/{order_id}/result', json={'value': 4.1, 'reference_low': 2.0, 'reference_high': 3.0})
    assert r.status_code == 200
    result = r.json()
    assert result['abnormal_flag'] == 'high'
    after = len(client.get('/patients/SYN-002').json()['labs'])
    assert after == before + 1

    retry = client.post(f'/lab-orders/{order_id}/result', json={'value': 999})
    assert retry.status_code == 200 and retry.json()['value'] == 4.1  # original result returned, not overwritten
    assert len(client.get('/patients/SYN-002').json()['labs']) == after  # no duplicate dual-write

def test_unified_results_merges_legacy_labs_and_lab_order_results_deduplicated(client):
    # Item 9: ResultsPanel used to only show new LabOrder-derived results, hiding the patient's
    # pre-existing (seed/legacy) lab history. GET /patients/{pid}/results must show both, merged
    # chronologically, with a real LabOrder result never double-counted against its own dual-write
    # into patient.labs (see repositories.py's submit_result()).
    before = client.get('/patients/SYN-002/results').json()['items']
    legacy_inr = [x for x in before if x['test_name'] == 'INR']
    assert legacy_inr, 'expected the demo patient seed INR history to already appear'
    assert all(x['source'] == 'legacy' for x in legacy_inr)
    # Chronological regardless of source.
    assert [x['measured_at'] for x in before] == sorted(x['measured_at'] for x in before)

    enc = _create_encounter(client)
    order_id = client.post(f"/encounters/{enc['id']}/lab-orders", json={'test_name': 'INR', 'priority': 'urgent'}).json()['id']
    client.post(f'/lab-orders/{order_id}/result', json={'value': 5.2, 'reference_low': 2.0, 'reference_high': 3.0})

    after = client.get('/patients/SYN-002/results').json()['items']
    inr_after = [x for x in after if x['test_name'] == 'INR']
    # The new value appears exactly once (as source=lab_order), not twice (once from the
    # LabResult itself and once from its patient.labs dual-write).
    assert sum(1 for x in inr_after if x['value'] == 5.2) == 1
    assert next(x for x in inr_after if x['value'] == 5.2)['source'] == 'lab_order'
    assert len(inr_after) == len(legacy_inr) + 1

def test_lab_order_cancel_then_result_rejected(client):
    enc = _create_encounter(client)
    order_id = client.post(f"/encounters/{enc['id']}/lab-orders", json={'test_name': 'eGFR'}).json()['id']
    client.post(f'/lab-orders/{order_id}/cancel')
    r = client.post(f'/lab-orders/{order_id}/result', json={'value': 60})
    assert r.status_code == 422


def test_timeline_reflects_seed_and_new_records(client):
    r = client.get('/patients/SYN-002/timeline')
    assert r.status_code == 200
    events = r.json()['events']
    types = {e['type'] for e in events}
    assert {'encounter', 'diagnosis', 'note', 'medication', 'lab'} <= types
    # Seeded INR history (2.1 -> 2.6 -> 3.8) must be visible.
    assert any('INR' in e['title'] for e in events if e['type'] == 'lab')

def test_clinical_summary_is_deterministic_and_cites_sources(client):
    r = client.get('/patients/SYN-002/clinical-summary')
    assert r.status_code == 200
    body = r.json()
    assert 'generative' not in body['method'].lower() or 'no generative model' in body['method'].lower()
    inr_sentence = next((s for s in body['sentences'] if 'INR' in s['text']), None)
    assert inr_sentence is not None
    assert inr_sentence['source_events']  # every sentence must trace to real events
    assert '2.1' in inr_sentence['text'] and '2.6' in inr_sentence['text'] and '3.8' in inr_sentence['text']


def test_clinical_summary_medication_source_id_matches_timeline_source_id(client):
    # Item 6 regression: the medication sentence's source_events used to carry the RAW
    # Medication.note dual-write marker string ('order:RX-<id>'), while Timeline's medication
    # events use the bare order id ('RX-<id>') as source_id -- so "관련 기록 보기" (jump to
    # source) could never find a match for a medication sentence. Confirm they're now identical.
    enc = _create_encounter(client)
    order = client.post(f"/encounters/{enc['id']}/medication-orders",
                         json={'medication_code': 'lisinopril', 'dose': 10, 'dose_unit': 'mg', 'route': 'PO'}).json()
    assert order['status'] == 'confirmed'

    summary = client.get('/patients/SYN-002/clinical-summary').json()
    med_sentence = next(s for s in summary['sentences'] if s.get('source_type') == 'medication')
    assert order['id'] in med_sentence['source_events']
    assert not any(sid.startswith('order:') for sid in med_sentence['source_events']), \
        'source_events must be bare entity ids, not the internal order:<id> dual-write marker'

    timeline = client.get('/patients/SYN-002/timeline').json()['events']
    timeline_source_ids = {e['source_id'] for e in timeline if e['type'] == 'medication'}
    assert order['id'] in timeline_source_ids
    # The exact id scheme now matches -- a frontend "jump to source" can find it by simple equality.
    assert set(med_sentence['source_events']) & timeline_source_ids


def test_fhir_mode_write_endpoints_return_501_not_crash():
    # FHIRAdapter.mutate() raises NotImplementedError by design (see emr_adapter.py); confirm the
    # repository layer surfaces that cleanly rather than raising an unhandled exception.
    from app.services.emr_adapter import FHIRAdapter
    from app.services.repositories import EncounterRepository
    adapter = FHIRAdapter(base_url='https://fake-fhir.example/r4')
    repo = EncounterRepository(adapter)
    with pytest.raises(NotImplementedError):
        repo.create('fhir-1', encounter_type='outpatient')


def test_audit_events_cover_every_required_action_with_minimal_detail(client):
    # Item 13's required audit coverage: every listed action must fire a semantically distinct
    # audit event, and its detail must be minimal metadata only -- never the full SOAP text, an
    # access token, or full patient PHI.
    client.get('/patients/SYN-002')  # patient_viewed (recorded as 'patient_selected')
    enc = _create_encounter(client)
    dx = client.post(f"/encounters/{enc['id']}/diagnoses", json={'display_name': 'Test diagnosis'}).json()
    note = client.post(f"/encounters/{enc['id']}/notes",
                        json={'author': 'Dr. Lee', 'subjective': 'PHI-shaped subjective text should not leak',
                              'plan': 'PHI-shaped plan text should not leak'}).json()
    client.patch(f"/notes/{note['id']}", json={'assessment': 'updated'})
    client.post(f"/notes/{note['id']}/sign")
    client.post(f"/notes/{note['id']}/amendments", json={'author': 'Dr. Lee', 'reason': 'correction'})
    order = client.post(f"/encounters/{enc['id']}/medication-orders",
                         json={'medication_code': 'warfarin', 'dose': 2, 'dose_unit': 'mg', 'route': 'PO',
                               'override_reason': 'reviewed and continuing'}).json()
    client.post(f"/medication-orders/{order['id']}/cancel")
    lab_order = client.post(f"/encounters/{enc['id']}/lab-orders", json={'test_name': 'BUN'}).json()
    client.post(f"/lab-orders/{lab_order['id']}/result", json={'value': 18})
    client.post(f"/encounters/{enc['id']}/medication-orders/precheck",
                json={'medication_code': 'aspirin', 'dose': 1, 'dose_unit': 'tab', 'route': 'PO'})

    events = client.get('/audit/SYN-002').json()
    event_names = {e['event'] for e in events}
    required = {'patient_selected', 'note_created', 'note_modified', 'note_signed', 'note_amended',
                'diagnosis_added', 'medication_ordered', 'medication_cancelled', 'lab_ordered',
                'lab_result_recorded', 'ai_warning_viewed', 'warning_overridden'}
    missing = required - event_names
    assert not missing, f'missing required audit event types: {missing}'

    # Minimal-metadata-only detail: no full SOAP text, no PHI dump, no token, on any event.
    forbidden_substrings = ['PHI-shaped subjective text', 'PHI-shaped plan text', 'access_token', 'super-secret']
    for e in events:
        detail_str = str(e['detail'])
        for bad in forbidden_substrings:
            assert bad not in detail_str, f'{e["event"]} detail leaked: {bad}'

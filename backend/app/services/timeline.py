"""Patient Timeline: a pure read-side aggregation over data that already exists elsewhere
(ClinicalEncounter/Diagnosis on Patient, ClinicalNote/MedicationOrder/LabOrder/LabResult in
repositories.py, plus the audit log's own alert_detected/cds_hook_fired events for "AI Warning"
entries). No new storage, nothing fabricated -- every entry traces back to a real stored record via
`source_id`, and the legacy pre-existing patient.medications/labs (present before this Clinical
Workspace round -- e.g. the demo seed data's dated Lab entries) are folded in too so older data
still shows up instead of only records created through the new endpoints.
"""
from typing import Dict, List

FILTER_TYPES = ['encounter', 'diagnosis', 'medication', 'lab', 'note', 'imaging', 'ai_warning']


def _event(type_, timestamp, title, detail='', source_id=None):
    return {'type': type_, 'timestamp': str(timestamp), 'title': title, 'detail': detail, 'source_id': source_id}


def build_timeline(patient, *, note_repo, medication_order_repo, lab_order_repo) -> List[Dict]:
    events = []

    for e in patient.clinical_encounters:
        events.append(_event('encounter', e.started_at, f'{e.encounter_type} 방문 · {e.department or "부서 미지정"}',
                              e.chief_complaint, e.id))
        if e.ended_at:
            events.append(_event('encounter', e.ended_at, '방문 종료', e.department, e.id))

    for dx in patient.problem_list:
        events.append(_event('diagnosis', dx.diagnosed_at,
                              f'{dx.display_name}' + (' (주진단)' if dx.diagnosis_type == 'primary' else ''),
                              dx.code or dx.code_system, dx.id))

    order_ids_with_dual_write = set()
    for o in medication_order_repo.list_for_patient(patient.id):
        order_ids_with_dual_write.add(o.id)
        events.append(_event('medication', o.ordered_at, f'{o.medication_name or o.medication_code} 처방',
                              f'{o.dose}{o.dose_unit} {o.route} {o.frequency}'.strip(), o.id))
        if o.status == 'confirmed' and o.start_date:
            events.append(_event('medication', o.start_date, f'{o.medication_name or o.medication_code} 복용 시작',
                                  o.indication, o.id))
        if o.status == 'cancelled':
            events.append(_event('medication', o.ordered_at, f'{o.medication_name or o.medication_code} 처방 취소', '', o.id))
    # Legacy/seed medications not created through a MedicationOrder (e.g. demo patients.json data
    # pre-dating this Clinical Workspace round) -- dual-written orders already have their own
    # 'order:<id>' marker in Medication.note, so this only covers genuinely order-less entries.
    for m in patient.medications:
        if m.note.startswith('order:'):
            continue
        if m.started:
            events.append(_event('medication', m.started, f'{m.drug_id} 복용 시작', m.note))

    for o in lab_order_repo.list_for_patient(patient.id):
        events.append(_event('lab', o.ordered_at, f'{o.test_name} 검사 처방', f'{o.priority} · {o.indication}', o.id))
        result = lab_order_repo.result_for(o.id)
        if result:
            arrow = {'high': ' ↑', 'low': ' ↓', 'critical': ' ‼'}.get(result.abnormal_flag, '')
            events.append(_event('lab', result.measured_at, f'{result.test_name} {result.value}{result.unit}{arrow}',
                                  f'참고범위 {result.reference_low}–{result.reference_high}', o.id))
    # Legacy/seed labs (same reasoning as medications above): every lab_order-driven result is
    # ALSO dual-written into patient.labs, so skip those to avoid double-listing -- distinguish by
    # date+name+value match against already-emitted lab-order results.
    seeded = {(r.measured_at[:10], r.test_name, r.value) for o in lab_order_repo.list_for_patient(patient.id)
              for r in [lab_order_repo.result_for(o.id)] if r}
    for l in patient.labs:
        if (str(l.date), l.name, l.value) in seeded:
            continue
        events.append(_event('lab', l.date, f'{l.name} {l.value}{l.unit}', f'참고범위 {l.low}–{l.high}',
                              f'lab:{l.name}:{l.date}'))

    for n in note_repo.list_for_patient(patient.id):
        events.append(_event('note', n.created_at, 'SOAP 노트 작성', n.author, n.id))
        if n.signed_at:
            events.append(_event('note', n.signed_at, 'SOAP 노트 서명', n.author, n.id))
        for a in n.amendments:
            events.append(_event('note', a.created_at, 'SOAP 노트 수정(amendment)', f'{a.author} · {a.reason}', n.id))

    for img in patient.imaging_studies:
        events.append(_event('imaging', img.date or '', f'{img.modality or "영상"} · {img.description}', '', img.id))

    events.sort(key=lambda e: e['timestamp'], reverse=True)
    return events


def with_ai_warnings(events: List[Dict], audit_events: List[Dict]) -> List[Dict]:
    """Merge in AI Warning entries from the real audit log (alert_detected/cds_hook_fired) --
    kept as a separate step from build_timeline() so callers without an AuditStore handy (e.g.
    tests exercising pure repository state) can still get the rest of the timeline."""
    out = list(events)
    for e in audit_events:
        if e['event'] == 'alert_detected':
            d = e['detail']
            out.append(_event('ai_warning', e['timestamp'], d.get('title', 'SynexAgent 신호'),
                               f"{d.get('severity','')} · analysis {d.get('analysis_id','')}", d.get('alert_id')))
    out.sort(key=lambda e: e['timestamp'], reverse=True)
    return out

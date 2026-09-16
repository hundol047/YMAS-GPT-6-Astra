"""Unified Results: merges legacy/demo Patient.labs, FHIR-sourced Observations (which FHIRAdapter
already normalizes into the SAME Patient.labs list at fetch time -- see emr_adapter.py's
_to_patient), and the new Clinical Workspace LabOrder/LabResult records into one chronological
view. This is a pure read-side aggregation (same pattern as timeline.py/clinical_summary.py) --
no new storage, and none of the existing /patients/{pid}/lab-orders, /lab-results endpoints are
removed or changed; this only adds a merged view on top of the same underlying data.
"""


def _flag(value, low, high):
    """Same simple low/high comparison LabOrderRepository.submit_result() already uses for a new
    LabResult -- applied here to legacy Lab entries too (which only ever carried low/high, never a
    'critical' threshold), so every item in the unified list has a comparable abnormal_flag."""
    if low is not None and value < low:
        return 'low'
    if high is not None and value > high:
        return 'high'
    return 'normal'


def unified_results(patient, *, lab_order_repo, legacy_source) -> list[dict]:
    order_results = [(o.id, r) for o in lab_order_repo.list_for_patient(patient.id)
                      for r in [lab_order_repo.result_for(o.id)] if r]
    # A LabOrder result is dual-written into patient.labs (repositories.py) -- skip the matching
    # legacy entry so it isn't listed twice, same dedup rule timeline.py/clinical_summary.py use.
    seeded = {(str(r.measured_at)[:10], r.test_name, r.value) for _, r in order_results}
    items = []
    for l in patient.labs:
        if (str(l.date), l.name, l.value) in seeded:
            continue
        items.append({'id': f'lab:{l.name}:{l.date}', 'source': legacy_source, 'test_code': l.name,
                       'test_name': l.name, 'value': l.value, 'unit': l.unit,
                       'reference_low': l.low, 'reference_high': l.high,
                       'abnormal_flag': _flag(l.value, l.low, l.high), 'measured_at': str(l.date)})
    for order_id, r in order_results:
        items.append({'id': r.id, 'source': 'lab_order', 'test_code': r.test_code, 'test_name': r.test_name,
                       'value': r.value, 'unit': r.unit, 'reference_low': r.reference_low,
                       'reference_high': r.reference_high, 'abnormal_flag': r.abnormal_flag,
                       'measured_at': str(r.measured_at)})
    items.sort(key=lambda x: x['measured_at'])
    return items

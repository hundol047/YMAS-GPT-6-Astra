"""Retrospective/operational metrics computed from REAL audit history and REAL rule output --
never a fabricated accuracy number.

IMPORTANT caveat this module deliberately does NOT paper over: this demo's synthetic training
data (research/original/build_dataset_v3.py) generates its labels FROM the same rule engine that
produces alerts here. Computing sensitivity/specificity/precision/recall of "the rules" against
that data would be circular -- the rules trivially "predict" labels they themselves generated.
That is why this module reports descriptive counts (alerts per type/severity, review/dismiss
rates) instead of an accuracy-shaped number for the rule engine. The one place a real accuracy
metric legitimately exists in this repo is the ONNX model's fit to its held-out validation split,
already measured in research/original/crossval_v3.py (5-fold CV) -- that number describes the
model's fit to synthetic labels, not clinical accuracy against real patient outcomes, and should
always be presented with that caveat attached.
"""
from collections import Counter


def alert_type_breakdown(agent, patients):
    """Run the agent across a patient cohort and describe what actually fired, broken out by
    alert type and severity -- not a single blended number."""
    by_type = Counter()
    by_type_severity = Counter()
    total_alerts = 0
    for p in patients:
        result = agent.run(p)
        for a in result['alerts']:
            by_type[a['type']] += 1
            by_type_severity[(a['type'], a['severity'])] += 1
            total_alerts += 1
    return {
        'patients_evaluated': len(patients),
        'total_alerts': total_alerts,
        'by_type': dict(by_type),
        'by_type_and_severity': {f'{t}:{s}': n for (t, s), n in by_type_severity.items()},
        'caveat': 'Descriptive counts only. Do not read this as sensitivity/specificity -- this '
                  'demo\'s synthetic labels are generated FROM these same rules, so any accuracy '
                  'metric computed against them would be circular.',
    }


def alert_fatigue_metrics(audit_store, patient_ids):
    """Alerts detected vs. how clinicians actually disposed of them, from real audit events."""
    per_patient = {}
    totals = Counter()
    for pid in patient_ids:
        events = audit_store.list(pid)
        detected = sum(1 for e in events if e['event'] == 'alert_detected')
        reviewed = sum(1 for e in events if e['event'] == 'alert_reviewed')
        dismissed = sum(1 for e in events if e['event'] == 'alert_dismissed')
        deferred = sum(1 for e in events if e['event'] == 'alert_deferred')
        alert_ids = [e['detail'].get('alert_id') for e in events if e['event'] == 'alert_detected']
        repeated = sum(1 for _, n in Counter(alert_ids).items() if n > 1)
        per_patient[pid] = {'detected': detected, 'reviewed': reviewed, 'dismissed': dismissed,
                            'deferred': deferred, 'repeated_alert_ids': repeated}
        totals.update({'detected': detected, 'reviewed': reviewed, 'dismissed': dismissed, 'deferred': deferred})
    return {'per_patient': per_patient, 'totals': dict(totals),
            'note': 'From real audit history in this deployment; empty/small until the app has real usage.'}

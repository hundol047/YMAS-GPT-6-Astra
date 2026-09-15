"""Data quality classification. A missing value is never silently treated as normal -- every
category gets an explicit status (COMPLETE/PARTIAL/MISSING/STALE) and unresolved gaps are listed,
never hidden.

Freshness thresholds are SynexAgent PROTOTYPE POLICY, the same status this app already gives its
drug interaction rules (see backend/data/rules.json / rule_engine.py) -- not a clinical guideline
and not any real institution's policy. No threshold is applied unless it is in this table, so a lab
name with no listed policy is never marked STALE by guesswork.
"""
from datetime import date

FRESHNESS_POLICY_SOURCE = 'SynexAgent prototype policy; NOT a clinical guideline or institution policy'
LAB_MAX_AGE_DAYS = {
    'Creatinine': 180, 'eGFR': 180, 'Potassium': 30, 'INR': 30, 'AST': 180, 'ALT': 180, 'Glucose': 90,
}


def assess(patient, today=None):
    today = today or date.today()
    allergy_status = 'MISSING' if not patient.allergies else (
        'PARTIAL' if any(a.severity == 'UNKNOWN' for a in patient.allergies) else 'COMPLETE')
    medication_status = 'MISSING' if not patient.medications else (
        'PARTIAL' if any(m.dispenses is None or m.started is None for m in patient.medications) else 'COMPLETE')
    condition_status = 'MISSING' if not patient.conditions else 'COMPLETE'

    latest_by_name = {}
    for l in patient.labs:
        if l.name not in latest_by_name or l.date > latest_by_name[l.name].date:
            latest_by_name[l.name] = l
    labs = {}
    for name, lab in latest_by_name.items():
        age_days = (today - lab.date).days
        max_age = LAB_MAX_AGE_DAYS.get(name)
        status = 'STALE' if (max_age is not None and age_days > max_age) else 'COMPLETE'
        labs[name] = {'status': status, 'age_days': age_days, 'date': str(lab.date),
                      'policy_max_age_days': max_age,
                      'policy_source': FRESHNESS_POLICY_SOURCE if max_age is not None else None}

    gaps = []
    if allergy_status == 'MISSING':
        gaps.append({'field': 'allergy', 'status': 'MISSING', 'message': 'Allergy information unavailable'})
    elif allergy_status == 'PARTIAL':
        gaps.append({'field': 'allergy', 'status': 'PARTIAL', 'message': '일부 알레르기 반응 중증도가 미상(UNKNOWN)입니다'})
    if medication_status == 'MISSING':
        gaps.append({'field': 'medication', 'status': 'MISSING', 'message': '복용 약물 정보 없음'})
    elif medication_status == 'PARTIAL':
        gaps.append({'field': 'medication', 'status': 'PARTIAL', 'message': '일부 약물의 조제/시작일 정보 누락'})
    if condition_status == 'MISSING':
        gaps.append({'field': 'condition', 'status': 'MISSING', 'message': '기저질환 기록 없음 (질환이 없다는 뜻이 아닙니다)'})
    for name, info in labs.items():
        if info['status'] == 'STALE':
            gaps.append({'field': f'lab:{name}', 'status': 'STALE',
                         'message': f'Latest {name} is {info["age_days"]} days old'})
    for m in patient.missing:
        gaps.append({'field': 'source', 'status': 'MISSING', 'message': m})

    return {'patient_id': patient.id, 'allergy': allergy_status, 'medication': medication_status,
            'condition': condition_status, 'labs': labs, 'gaps': gaps}

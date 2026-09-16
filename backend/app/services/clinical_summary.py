"""AI Patient Summary: a DETERMINISTIC TEMPLATE over stored data, not a generative model call --
this backend has no LLM connected anywhere (confirmed: no anthropic/openai/etc dependency exists in
requirements.txt), and per an explicit product decision the summary must never invent a fact, so
sentences are built the same way ClinicalAgent.run()'s own `summary`/`brief_facts` already are:
real measured values -> a Python f-string, with each sentence naming the real event(s) it came from
so a clinician can jump straight to the source instead of trusting free text.
"""
from datetime import datetime, timedelta, timezone


def _trend(values):
    if len(values) < 2:
        return None
    diffs = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    if all(d > 0 for d in diffs):
        return 'rising'
    if all(d < 0 for d in diffs):
        return 'falling'
    if values[0] and abs(values[-1] - values[0]) / abs(values[0]) < .1:
        return 'stable'
    return None


def _lab_points(patient, lab_order_repo):
    points = {}
    order_results = [(o.id, r) for o in lab_order_repo.list_for_patient(patient.id)
                      for r in [lab_order_repo.result_for(o.id)] if r]
    # A LabOrder result is dual-written into patient.labs (repositories.py), so a legacy patient.labs
    # entry matching one exactly is the SAME reading, not a second one -- skip it here the same way
    # timeline.py's `seeded` set does, or trends would double-count a single real result.
    seeded = {(r.measured_at[:10], r.test_name, r.value) for _, r in order_results}
    for l in patient.labs:
        if (str(l.date), l.name, l.value) in seeded:
            continue
        points.setdefault(l.name, []).append((str(l.date), l.value, f'lab:{l.name}:{l.date}'))
    for order_id, r in order_results:
        points.setdefault(r.test_name, []).append((r.measured_at[:10], r.value, order_id))
    for name in points:
        points[name] = sorted(set(points[name]), key=lambda t: t[0])
    return points


def build_summary(patient, *, lab_order_repo, ai_warning_events, months=6) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=months * 30)).date().isoformat()
    sentences = []

    for name, series in _lab_points(patient, lab_order_repo).items():
        recent = [p for p in series if p[0] >= cutoff][-3:]
        if len(recent) < 2:
            continue
        values = [v for _, v, _ in recent]
        trend = _trend(values)
        arrow = ' → '.join(str(v) for v in values)
        if trend == 'rising':
            sentences.append({'text': f'{name}이(가) 최근 {len(values)}회 연속 상승 추세로 감지되었습니다 ({arrow}).',
                               'source_events': [sid for _, _, sid in recent]})
        elif trend == 'falling':
            sentences.append({'text': f'{name}이(가) 최근 {len(values)}회 연속 하락 추세로 감지되었습니다 ({arrow}).',
                               'source_events': [sid for _, _, sid in recent]})
        elif trend == 'stable':
            sentences.append({'text': f'{name}은(는) 최근 측정값이 안정적입니다 ({arrow}).',
                               'source_events': [sid for _, _, sid in recent]})

    active = [m for m in patient.medications if m.status == 'active']
    if active:
        names = ', '.join(sorted({m.drug_id for m in active}))
        sentences.append({'text': f'현재 활성 처방을 유지 중입니다: {names}.',
                           'source_events': [m.note for m in active if m.note.startswith('order:')]})

    recent_warnings = [w for w in ai_warning_events if w['type'] == 'ai_warning' and w['timestamp'] >= cutoff][:3]
    for w in recent_warnings:
        sentences.append({'text': f'SynexAgent 신호: {w["title"]}.', 'source_events': [w.get('source_id')]})

    return {
        'patient_id': patient.id,
        'window_months': months,
        'sentences': sentences,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'method': 'deterministic template over stored Encounter/Diagnosis/Medication/Lab/audit data -- no generative model involved',
        'disclaimer': ('이 요약은 저장된 실제 데이터에서 결정론적 규칙으로 생성됩니다. 생성형 AI가 사실을 추정하거나 '
                        '창작하지 않으며, 모든 문장은 실제 기록된 이벤트(source_events)에서 도출됩니다. 임상 판단을 '
                        '대체하지 않으며 원기록 확인이 필요합니다.'),
    }

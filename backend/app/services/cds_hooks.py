"""CDS Hooks (https://cds-hooks.org/) service discovery + the medication-prescribe hook.

This lets SynexAgent surface inside an EMR's own prescribing screen as a Card instead of only
living in a separate tab. It has been exercised with FastAPI's TestClient posting a hand-built
CDS Hooks request against our own demo patients (backend/tests/test_cds_hooks.py) -- it has NOT
been launched from inside a real EMR's CDS Hooks client, so the request/response shape is
spec-correct but real-EMR interoperability (exact prefetch behavior, card rendering) is unverified.
"""
SEVERITY_TO_INDICATOR = {'danger': 'critical', 'caution': 'warning', 'info': 'info'}

SERVICES_DOC = {
    'services': [{
        'hook': 'medication-prescribe',
        'title': 'SynexAgent Medication Safety',
        'description': 'Rule-based drug interaction, duplicate therapy, allergy, condition and lab safety signals. '
                        'Reference information only -- the prescriber makes the final decision.',
        'id': 'synex-medication-safety',
        'prefetch': {
            'patient': 'Patient/{{context.patientId}}',
        },
    }],
}


def build_cards(patient_id: str, agent_result: dict, app_base_url: str = '') -> dict:
    cards = []
    for a in agent_result['alerts']:
        cards.append({
            'summary': a['title'][:140],
            'indicator': SEVERITY_TO_INDICATOR.get(a['severity'], 'info'),
            'detail': a['reason'] + '\n\nReference information only. Final treatment selection remains with the clinician.',
            'source': {'label': 'SynexAgent', 'url': app_base_url or None},
            'suggestions': [],
            'selectionBehavior': 'any',
            'links': [{'label': 'Review in SynexAgent', 'url': f'{app_base_url}/?patient={patient_id}', 'type': 'smart'}] if app_base_url else [],
        })
    if not cards:
        cards.append({
            'summary': '제공 규칙에서 감지된 경고가 없습니다 (안전을 보증하지 않음)',
            'indicator': 'info',
            'detail': 'No signal from SynexAgent\'s prototype rules for this patient\'s current active medications. '
                       'This does not certify the prescription is safe -- rules cover a limited, prototype vocabulary.',
            'source': {'label': 'SynexAgent'},
        })
    return {'cards': cards}

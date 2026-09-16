"""One-time Clinical Workspace seed data for the 5 bundled demo patients (SYN-001..005): one past
Encounter + its VitalSigns + (structured Diagnosis, for patients that already have a matching
free-text condition) + one signed SOAP note each.

This runs through the exact same repository methods a real API call would use
(EncounterRepository.create/add_vitals/update, DiagnosisRepository.create,
ClinicalNoteRepository.create/sign) rather than hand-crafted JSON, so the seed data can never drift
from what those endpoints actually produce, and Timeline/clinical-summary see it exactly like any
clinician-entered record.

Only meaningful for EMR_MODE=demo -- DemoAdapter.mutate() supports local write-back; FHIRAdapter
doesn't (by design, see emr_adapter.py), so seeding is skipped there rather than raising.
"""

SEED = {
    'SYN-001': {
        'encounter_type': 'outpatient', 'department': '가정의학과', 'attending_physician': '이하윤',
        'chief_complaint': '정기 건강검진 상담',
        'vitals': {'sbp': 112, 'dbp': 72, 'heart_rate': 68, 'respiratory_rate': 14, 'temperature_c': 36.5, 'spo2': 99},
        'diagnoses': [],
        'note': {'s': '특이 증상 없음. 정기 건강검진 목적으로 내원.',
                  'o': '활력징후 정상 범위. 신체 진찰 특이소견 없음.',
                  'a': '건강한 성인, 특이 소견 없음.',
                  'p': '현재 비타민D 보충 유지. 특별한 추가 검사나 처방 계획 없음. 1년 후 정기 검진 권고.'},
    },
    'SYN-002': {
        'encounter_type': 'outpatient', 'department': '순환기내과', 'attending_physician': '김도현',
        'chief_complaint': 'INR 추적 관찰',
        'vitals': {'sbp': 142, 'dbp': 86, 'heart_rate': 92, 'respiratory_rate': 18, 'temperature_c': 36.7, 'spo2': 97},
        'diagnoses': [{'display_name': '심방세동', 'diagnosis_type': 'primary', 'code_system': 'ICD-10', 'code': 'I48.91'}],
        'note': {'s': '특이 흉통, 호흡곤란 없음. 항응고요법 지속 중.',
                  'o': 'BP 142/86, HR 92 (불규칙), SpO2 97%. 최근 INR 상승 추세 확인.',
                  'a': '심방세동, 항응고요법 중 INR 상승 추세 -- 출혈 위험 관련 재평가 필요.',
                  'p': 'Warfarin/Aspirin 병용 관련 SynexAgent 신호 확인 후 처방 재검토 예정. INR 재검사 및 추적 관찰.'},
    },
    'SYN-003': {
        'encounter_type': 'outpatient', 'department': '노인내과', 'attending_physician': '정하은',
        'chief_complaint': '다약제 복용 검토',
        'vitals': {'sbp': 128, 'dbp': 78, 'heart_rate': 74, 'respiratory_rate': 16, 'temperature_c': 36.6, 'spo2': 96},
        'diagnoses': [{'display_name': '다약제 복용 관리', 'diagnosis_type': 'secondary', 'code_system': 'text'}],
        'note': {'s': '다수 약물 복용 중. 복약 순응도 및 상호작용 재검토 요청.',
                  'o': '활력징후 정상 범위. 10종 활성 약물 확인.',
                  'a': '다약제 복용(polypharmacy) 상태로 중복/상호작용 검토가 필요함.',
                  'p': 'SynexAgent 약물 상호작용 분석 결과 검토. 불필요한 약물 정리 여부 다음 방문 시 재평가.'},
    },
    'SYN-004': {
        'encounter_type': 'outpatient', 'department': '알레르기내과', 'attending_physician': '한소율',
        'chief_complaint': '약물 알레르기 이력 확인',
        'vitals': {'sbp': 118, 'dbp': 74, 'heart_rate': 70, 'respiratory_rate': 15, 'temperature_c': 36.5, 'spo2': 98},
        'diagnoses': [],
        'note': {'s': '과거 페니실린 계열 약물 투약 후 중증 반응(아나필락시스 의심) 이력 보고.',
                  'o': '활력징후 정상. 현재 급성 알레르기 증상 없음.',
                  'a': '페니실린 계열 약물 중증 알레르기 이력 -- 향후 처방 시 반드시 확인 필요.',
                  'p': '알레르기 정보 원기록에 명확히 기재. 향후 처방 전 SynexAgent 알레르기 경고 확인 필수.'},
    },
    'SYN-005': {
        'encounter_type': 'outpatient', 'department': '신장내과', 'attending_physician': '오지훈',
        'chief_complaint': '신기능 저하 추적 관찰',
        'vitals': {'sbp': 138, 'dbp': 84, 'heart_rate': 78, 'respiratory_rate': 16, 'temperature_c': 36.6, 'spo2': 97},
        'diagnoses': [
            {'display_name': '만성신부전', 'diagnosis_type': 'primary', 'code_system': 'ICD-10', 'code': 'N18.9'},
            {'display_name': '고칼륨혈증', 'diagnosis_type': 'secondary', 'code_system': 'ICD-10', 'code': 'E87.5'},
        ],
        'note': {'s': '특이 증상 없음. 신기능 저하 추적 관찰 중.',
                  'o': 'BP 138/84. 최근 eGFR 하락 추세, Potassium 상승 경향 확인.',
                  'a': '만성신부전 진행 및 고칼륨혈증 위험 -- 신기능 관련 약물(메트포르민 등) 용량 재평가 필요.',
                  'p': 'eGFR/Creatinine/Potassium 추적 검사 지속. 신장 기능 관련 약물 조정 여부 검토.'},
    },
}


def seed_demo_clinical_data(adapter, encounter_repo, diagnosis_repo, note_repo):
    for pid, spec in SEED.items():
        if pid not in getattr(adapter, 'patients', {}):
            continue
        enc = encounter_repo.create(pid, encounter_type=spec['encounter_type'], department=spec['department'],
                                     attending_physician=spec['attending_physician'], chief_complaint=spec['chief_complaint'])
        encounter_repo.add_vitals(pid, enc.id, **spec['vitals'])
        for dx in spec['diagnoses']:
            diagnosis_repo.create(pid, enc.id, **dx)
        note = note_repo.create(pid, enc.id, author=spec['attending_physician'], subjective=spec['note']['s'],
                                 objective=spec['note']['o'], assessment=spec['note']['a'], plan=spec['note']['p'])
        note_repo.sign(note.id)
        encounter_repo.update(pid, enc.id, status='completed', ended_at=enc.started_at)

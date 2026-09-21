from ..schemas import RiskFeatures
from .rule_engine import DRUGS, SEVERITY

def features_for(patient, rules):
    active=[m for m in patient.medications if m.status=='active']
    matched=[m for m in active if m.drug_id in DRUGS]
    missing=list(patient.missing)
    unknown=sorted({m.drug_id for m in active if m.drug_id not in DRUGS})
    if unknown:missing.append('카탈로그 미등록 약물: '+', '.join(unknown))
    if any(m.dispenses is None for m in matched):missing.append('조제/리필 횟수 일부 누락')
    if any(a.category=='medication' and a.severity=='UNKNOWN' for a in patient.allergies):missing.append('약물 알레르기 중증도 미상')
    # Missing dispenses uses the same zero convention as raw CSV import, explicitly flagged.
    avg=sum(m.dispenses or 0 for m in matched)/len(matched) if matched else 0
    severe=max((SEVERITY[a.severity] for a in patient.allergies if a.category=='medication'),default=0)
    f=RiskFeatures(drug_conflict=round(min(1.,rules['danger_count']*.5+rules['caution_count']*.2),3),
        comorbidity_load=round(min(1.,len(set(patient.conditions))/5),3),age_risk=round(min(1.,patient.age/100),3),
        allergy_flag=float(bool(patient.allergies)),adverse_history=severe,
        polypharmacy_load=round(min(1.,len(rules['matched_ids'])/10),3),therapy_duration_load=round(min(1.,avg/24),3))
    if not patient.labs:missing.append('검사 결과 없음 (v3 모델 입력에는 검사 수치가 포함되지 않음)')
    return f,sorted(set(missing))

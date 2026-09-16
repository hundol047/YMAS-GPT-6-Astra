from datetime import datetime,timezone
from time import perf_counter
from uuid import uuid4
from .rule_engine import evaluate
from .anatomy import build_anatomy
from .feature_engineering import features_for

class ClinicalAgent:
    def __init__(self,engine):self.engine=engine
    def run(self,p):
        start=perf_counter();steps=[]
        def step(name,detail,warning=False):
            steps.append({'name':name,'detail':detail,'warning':warning,'status':'completed','elapsed_ms':round((perf_counter()-start)*1000,2)})
        step('Patient',f'{p.name} · {p.age}세 · {p.sex}')
        step('Medication',f"활성 처방 {sum(m.status=='active' for m in p.medications)}건")
        rules=evaluate(p)
        step('Drug Interaction',f"상호작용 {sum(a['type']=='drug_interaction' for a in rules['alerts'])}건",any(a['type']=='drug_interaction' for a in rules['alerts']))
        step('Allergy',f'알레르기 이력 {len(p.allergies)}건',any(a['type'] in ['allergy','adverse_history'] for a in rules['alerts']))
        step('Condition',f'기저질환 {len(p.conditions)}건',any(a['type']=='drug_condition' for a in rules['alerts']))
        step('Labs',f'검사 기록 {len(p.labs)}건',any(a['type']=='lab_review' for a in rules['alerts']))
        f,missing=features_for(p,rules);risk=self.engine.predict(f)
        step('Risk Model','v3 ONNX 추론 완료',risk['risk_level']=='high')
        dangers=sum(a['severity']=='danger' for a in rules['alerts'])
        cautions=sum(a['severity']=='caution' for a in rules['alerts'])
        summary=f'{p.name}, {p.age}세. {p.diagnosis}. 활성 약물 {len(rules["matched_ids"])}종을 검토했습니다. 위험 신호 {dangers}건, 주의 신호 {cautions}건입니다.'
        # Clinical Brief: discrete, individually-navigable facts (not just prose) -- each states
        # what is DOCUMENTED, never an inferred severity beyond what the alert/rule already says.
        brief=[{'type':'medication_count','text':f'활성 약물 {len(rules["matched_ids"])}종','nav':'records'}]
        if dangers:brief.append({'type':'signal_count','text':f'고위험 안전 신호 {dangers}건','nav':'overview'})
        if cautions:brief.append({'type':'signal_count','text':f'주의 신호 {cautions}건','nav':'overview'})
        for c in p.conditions:brief.append({'type':'condition','text':f'{c} 기록됨','nav':'records'})
        if missing:brief.append({'type':'missing','text':'정보 부족: '+', '.join(missing),'nav':'overview'})
        checks=[a['title']+' — '+a['reason'] for a in rules['alerts'][:4]]
        if not checks:checks=['제공 규칙에서 경고를 찾지 못했습니다. 처방 안전성이 확인되었다는 뜻은 아닙니다.']
        if missing:checks+=['누락 정보 확인: '+', '.join(missing)]
        checks+=['최종 처방 판단 전 용량·투여경로·환자별 검사 목표범위를 원기록에서 확인하십시오.']
        step('Clinical Summary','근거 기반 요약 완료')
        return {'analysis_id':str(uuid4()),'patient_id':p.id,'timestamp':datetime.now(timezone.utc).isoformat(),
            'anatomy':build_anatomy(p,rules['alerts']),'risk':risk,'alerts':rules['alerts'],'training_counts':{'danger':rules['danger_count'],'caution':rules['caution_count']},
            'rules_sha256':rules['rules_sha256'],'rule_metadata':rules['rule_metadata'],'steps':steps,'summary':summary,
            'brief_facts':brief,'next_checks':checks,
            'missing':missing,'data_status':'incomplete' if missing else 'demo_complete',
            'contributing_factors':[{'type':a['type'],'title':a['title'],'alert_id':a['id']} for a in rules['alerts']],
            'explanation_method':'MODEL INPUT SUMMARY + EVIDENCE PATH (detected contributing factors via rules); not SHAP or another causal attribution method -- no per-feature contribution percentage is computed or shown',
            'agent_mode':'deterministic evidence-grounded summarizer','demo':True,'duration_ms':round((perf_counter()-start)*1000,2)}

"""Training-compatible counts are isolated from additional review signals.
Supplied rules are prototype rules, NOT a clinically validated drug database.
"""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / 'data'
CATALOG = json.loads((DATA/'drug_catalog.json').read_text(encoding='utf-8'))
DRUGS = {d['id']:d for d in CATALOG}
RULES = json.loads((DATA/'rules.json').read_text(encoding='utf-8'))
RULES_HASH = hashlib.sha256((DATA/'rules.json').read_bytes()).hexdigest()
PAIRS = {frozenset((r['a'],r['b'])):(i,r) for i,r in enumerate(RULES['interactions'])}
SEVERITY = {'NONE':0.,'MILD':.34,'MODERATE':.67,'SEVERE':1.,'UNKNOWN':0.}

def make_alert(kind, severity, title, reason, drugs=(), source='SynexAgent prototype policy', training=False, evidence=None):
    key = json.dumps([kind,sorted(drugs),source,reason],ensure_ascii=False)
    return {'id':hashlib.sha256(key.encode()).hexdigest()[:16], 'type':kind,'severity':severity,
            'title':title,'reason':reason,'drugs':list(drugs),'source':source,
            'timestamp':datetime.now(timezone.utc).isoformat(), 'engine':'rule',
            'training_signal':training,'evidence':evidence or {},
            'evidence_status':'Prototype reference; clinician validation required',
            'risk_effect':'Included in training-compatible counts' if training else 'Separate safety signal; not added to drug_conflict'}

def evaluate(patient):
    active = [m for m in patient.medications if m.status=='active']
    ids = sorted({m.drug_id for m in active if m.drug_id in DRUGS})
    alerts=[]
    def add(*args,**kwargs): alerts.append(make_alert(*args,**kwargs))
    for a,b in combinations(ids,2):
        match=PAIRS.get(frozenset((a,b)))
        if match:
            i,r=match
            add('drug_interaction','danger' if r['severity']=='위험' else 'caution',
                f"{DRUGS[a]['name_ko']} + {DRUGS[b]['name_ko']}",r['reason'],[a,b],f'rules.json / interactions/{i}',True)
        if DRUGS[a]['group_ko'] and DRUGS[a]['group_ko']==DRUGS[b]['group_ko']:
            add('duplicate_group','caution',f"약물군 중복 · {DRUGS[a]['group_ko']}",
                '카탈로그의 동일 약물군입니다. 병용 목적과 용량을 확인하십시오.',[a,b],'build_dataset_v2.audit / group_ko',True)
    for d in ids:
        for i,r in enumerate(RULES['comorbid']):
            if d==r['drug'] and r['condition'] in patient.conditions:
                add('drug_condition','caution',f"{DRUGS[d]['name_ko']} · {r['condition']}",r['reason'],[d],f'rules.json / comorbid/{i}',True,{'condition':r['condition']})
        cls=RULES['allergy'].get(d)
        hits=[a for a in patient.allergies if cls and cls in a.substance]
        if hits:
            add('allergy','danger',f"알레르기 이력 · {DRUGS[d]['name_ko']}",
                f'{cls} 이력과 제공된 알레르기 규칙이 일치합니다. 원기록과 반응 유형을 확인하십시오.',[d],f'rules.json / allergy/{d}',True,{'allergies':[x.model_dump() for x in hits]})
    # Freeze original training counts BEFORE adding new policy signals.
    danger=sum(a['severity']=='danger' for a in alerts)
    caution=sum(a['severity']=='caution' for a in alerts)
    for d,n in Counter(m.drug_id for m in active).items():
        if n>1:
            add('duplicate_ingredient','caution','동일 약물 중복 기록',f'{d} 활성 처방 {n}건입니다. 중복 입력 또는 분할 처방인지 확인하십시오.',[d])
    ingredients={}
    for d in ids:
        for token in DRUGS[d]['openfda_search_term'].replace(' AND ',';').split(';'):
            ingredients.setdefault(token.strip().upper(),set()).add(d)
    for ingredient,ds in ingredients.items():
        if ingredient and len(ds)>1:
            add('duplicate_ingredient','caution',f'동일 성분 후보 · {ingredient}',
                '카탈로그 검색 성분이 겹칩니다. 정확한 성분·제형·함량은 원처방에서 확인하십시오.',sorted(ds), 'drug_catalog.json / openfda_search_term')
    if len(ids)>=10:
        add('polypharmacy','danger','과다 다약제 검토',f'카탈로그에 매칭된 활성 약물이 {len(ids)}종입니다.',ids,'build_dataset_v3 / n_drugs >= 10')
    elif len(ids)>=5:
        add('polypharmacy','info','다약제 검토',f'활성 약물 {len(ids)}종의 병용 목적을 확인하십시오.',ids)
    severe=[a for a in patient.allergies if a.category=='medication' and a.severity=='SEVERE']
    if severe:
        add('adverse_history','danger','중증 약물 반응 이력','과거 중증 반응 원기록을 확인하십시오. 현재 약물과의 교차 반응은 별도 검토가 필요합니다.',[], 'build_dataset_v3 / adverse_history >= 1',evidence={'allergies':[a.model_dump() for a in severe]})
    if caution>=3:
        add('caution_accumulation','danger','주의 신호 누적',f'학습 규칙의 주의 신호 {caution}건이 함께 탐지되었습니다.',[], 'build_dataset_v3 / caution_count >= 3')
    latest={}
    for lab in sorted(patient.labs,key=lambda l:l.date):latest[lab.name]=lab
    related={'INR':['warfarin'],'eGFR':['metformin','lithium','ibuprofen'],'Creatinine':['metformin','lithium'],'Potassium':['lisinopril','spironolactone','digoxin'],'AST':['simvastatin'],'ALT':['simvastatin'],'Glucose':['metformin']}
    for name,lab in latest.items():
        outside=(lab.low is not None and lab.value<lab.low) or (lab.high is not None and lab.value>lab.high)
        if outside:
            ds=[d for d in related.get(name,[]) if d in ids]
            add('lab_review','caution',f'{name} · 제공 참고범위 이탈',
                f'{lab.date}: {lab.value} {lab.unit}. 환자별 목표범위와 검사 시점·약물 연관성을 검토하십시오.',ds,
                'Demo Observation / supplied reference range', evidence={'lab':lab.model_dump(mode='json')})
    alerts.sort(key=lambda a:({'danger':0,'caution':1,'info':2}[a['severity']],a['id']))
    return {'alerts':alerts,'danger_count':danger,'caution_count':caution,'matched_ids':ids,'rules_sha256':RULES_HASH}

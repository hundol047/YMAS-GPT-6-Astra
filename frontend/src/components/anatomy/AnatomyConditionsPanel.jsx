import React from 'react';
import {ChevronRight,Info} from 'lucide-react';
import {CONDITION_ICD10} from '../../data/anatomyMap';

// Lists exactly what is documented on the patient record -- never inferred, never hidden when
// empty. Clicking a condition focuses the organ(s) the backend already linked via the fixed
// anatomy_mapping.json keyword table (see backend/app/services/anatomy.py); it does not invent
// a relationship at click time.
export default function AnatomyConditionsPanel({patient,data,onFocusCondition}){
 const conditions=patient?.conditions||[];
 return <section className="an-conditions">
 <h3>PATIENT CONDITIONS</h3>
 {!conditions.length&&<p className="an-empty">No documented condition data</p>}
 <ul>
  {conditions.map(c=>{
   const icd=CONDITION_ICD10[c];
   const targets=(data?.targets||[]).filter(t=>t.sources.some(s=>s.type==='condition'&&s.name===c));
   const organIds=[...new Set(targets.map(t=>t.organ_id))];
   return <li key={c}>
    <button onClick={()=>onFocusCondition(c,organIds)}>
     <div><b>{c}</b>{icd?<small className="an-icd">ICD-10: {icd}</small>:<small className="an-icd muted">코드 매핑 없음</small>}</div>
     <ChevronRight size={15}/>
    </button>
    {!organIds.length&&<p className="an-condition-note"><Info size={12}/> 연결된 해부학적 구조 없음 · 전신으로 표시</p>}
   </li>;
  })}
 </ul>
 <p className="an-note">Documented diagnosis는 환자 기록, Associated organ은 규칙 기반 연결입니다. Confirmed lesion은 실제 영상 근거가 있을 때만 사용합니다.</p>
 </section>;
}

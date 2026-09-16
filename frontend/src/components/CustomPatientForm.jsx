import React,{useState} from 'react';
import {X,Plus,Trash2,UserPlus} from 'lucide-react';
import DrugCombobox from './DrugCombobox';

const CONDITION_HINTS=['고혈압','만성신부전','고칼륨혈증'];
const ALLERGY_HINTS=['페니실린','마크로라이드'];
const emptyMed=()=>({drug_id:'',dispenses:'',started:'',note:''});
const emptyAllergy=()=>({substance:'',category:'medication',severity:'UNKNOWN',reaction:''});
const emptyLab=()=>({name:'',value:'',unit:'',date:'',low:'',high:''});

function num(v){return v===''||v===null||v===undefined?null:Number(v)}

export default function CustomPatientForm({catalog,onClose,onSubmit}){
 const [name,setName]=useState(''),[age,setAge]=useState(''),[sex,setSex]=useState('female'),[diagnosis,setDiagnosis]=useState(''),[scenario,setScenario]=useState('');
 const [heightCm,setHeightCm]=useState(''),[weightKg,setWeightKg]=useState('');
 const [medications,setMedications]=useState([emptyMed()]);
 const [conditions,setConditions]=useState([]),[conditionInput,setConditionInput]=useState('');
 const [allergies,setAllergies]=useState([]);
 const [labs,setLabs]=useState([]);
 const [history,setHistory]=useState([]),[historyInput,setHistoryInput]=useState('');
 const [busy,setBusy]=useState(false),[error,setError]=useState('');

 function updateRow(setter,i,patch){setter(rows=>rows.map((r,ri)=>ri===i?{...r,...patch}:r))}
 function removeRow(setter,i){setter(rows=>rows.filter((_,ri)=>ri!==i))}
 function addTag(list,setList,input,setInput){const v=input.trim();if(!v)return;if(!list.includes(v))setList([...list,v]);setInput('')}

 async function submit(e){
  e.preventDefault();
  if(!name.trim()||age===''||!diagnosis.trim()){setError('이름, 나이, 진단명은 필수입니다.');return}
  const patient={
   id:'CUSTOM-'+Date.now().toString(36).toUpperCase(),
   name:name.trim(),age:Number(age),sex,diagnosis:diagnosis.trim(),scenario:scenario.trim(),
   height_cm:num(heightCm),weight_kg:num(weightKg),
   medications:medications.filter(m=>m.drug_id).map(m=>({drug_id:m.drug_id,dispenses:num(m.dispenses),started:m.started||null,status:'active',note:m.note||''})),
   conditions,
   allergies:allergies.filter(a=>a.substance.trim()).map(a=>({substance:a.substance.trim(),category:a.category,severity:a.severity,reaction:a.reaction||''})),
   labs:labs.filter(l=>l.name.trim()&&l.value!==''&&l.date).map(l=>({name:l.name.trim(),value:Number(l.value),unit:l.unit||'',date:l.date,low:num(l.low),high:num(l.high)})),
   history
  };
  setBusy(true);setError('');
  try{await onSubmit(patient)}catch(err){setError(err.message||'환자 생성에 실패했습니다.')}finally{setBusy(false)}
 }

 return <div className="drawer-backdrop" onClick={onClose}>
 <section className="alert-drawer custom-patient-drawer" role="dialog" aria-modal="true" aria-labelledby="custom-patient-title" onClick={e=>e.stopPropagation()}>
  <div className="drawer-top"><span>NEW PATIENT</span><button aria-label="닫기" onClick={onClose}><X size={22}/></button></div>
  <h2 id="custom-patient-title"><UserPlus size={20}/> 환자 직접 입력</h2>
  <p className="drawer-note">입력한 정보는 이 브라우저 세션에서만 유지되며, 기존 데모 규칙·모델로 동일하게 분석됩니다. 실제 환자 정보를 입력하지 마십시오. 키·몸무게는 위험도 분석에는 쓰이지 않고 3D 인체도 크기를 근사하는 데만 사용됩니다.</p>
  <form onSubmit={submit} className="cp-form">
   <div className="cp-section">
    <h3>기본 정보</h3>
    <div className="cp-grid">
     <label>이름<input value={name} onChange={e=>setName(e.target.value)} required maxLength={40}/></label>
     <label>나이<input type="number" min={0} max={120} value={age} onChange={e=>setAge(e.target.value)} required/></label>
     <label>성별<select value={sex} onChange={e=>setSex(e.target.value)}><option value="female">여성</option><option value="male">남성</option></select></label>
     <label>키(cm)<input type="number" min={30} max={250} step="0.1" value={heightCm} onChange={e=>setHeightCm(e.target.value)} placeholder="선택 입력"/></label>
     <label>몸무게(kg)<input type="number" min={1} max={400} step="0.1" value={weightKg} onChange={e=>setWeightKg(e.target.value)} placeholder="선택 입력"/></label>
     <label className="cp-wide">진단명<input value={diagnosis} onChange={e=>setDiagnosis(e.target.value)} required maxLength={120}/></label>
     <label className="cp-wide">메모 / 시나리오<input value={scenario} onChange={e=>setScenario(e.target.value)} maxLength={120} placeholder="선택 입력"/></label>
    </div>
   </div>

   <div className="cp-section">
    <h3>복용 약물</h3>
    {medications.map((m,i)=><div className="cp-row" key={i}>
     <DrugCombobox label={'복용 약물 '+(i+1)} catalog={catalog} value={m.drug_id} onChange={id=>updateRow(setMedications,i,{drug_id:id})}/>
     <input type="number" min={0} max={10000} placeholder="조제/리필" value={m.dispenses} onChange={e=>updateRow(setMedications,i,{dispenses:e.target.value})}/>
     <input type="date" value={m.started} onChange={e=>updateRow(setMedications,i,{started:e.target.value})}/>
     <button type="button" className="cp-remove" aria-label="약물 삭제" onClick={()=>removeRow(setMedications,i)}><Trash2 size={15}/></button>
    </div>)}
    <button type="button" className="text-button" onClick={()=>setMedications(m=>[...m,emptyMed()])}><Plus size={15}/> 약물 추가</button>
   </div>

   <div className="cp-section">
    <h3>기저질환</h3>
    <div className="cp-tags">{conditions.map(c=><span className="cp-tag" key={c}>{c}<button type="button" onClick={()=>setConditions(cs=>cs.filter(x=>x!==c))}><X size={12}/></button></span>)}</div>
    <div className="cp-tag-input"><input list="cp-condition-hints" placeholder="예: 고혈압 (Enter로 추가)" value={conditionInput} onChange={e=>setConditionInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();addTag(conditions,setConditions,conditionInput,setConditionInput)}}}/><datalist id="cp-condition-hints">{CONDITION_HINTS.map(c=><option value={c} key={c}/>)}</datalist><button type="button" className="outline-button" onClick={()=>addTag(conditions,setConditions,conditionInput,setConditionInput)}>추가</button></div>
   </div>

   <div className="cp-section">
    <h3>알레르기</h3>
    {allergies.map((a,i)=><div className="cp-row cp-row-allergy" key={i}>
     <input list="cp-allergy-hints" placeholder="원인 물질" value={a.substance} onChange={e=>updateRow(setAllergies,i,{substance:e.target.value})}/>
     <select value={a.category} onChange={e=>updateRow(setAllergies,i,{category:e.target.value})}><option value="medication">약물</option><option value="food">음식</option><option value="environment">환경</option></select>
     <select value={a.severity} onChange={e=>updateRow(setAllergies,i,{severity:e.target.value})}><option value="MILD">경미</option><option value="MODERATE">중등도</option><option value="SEVERE">중증</option><option value="UNKNOWN">미상</option></select>
     <input placeholder="반응" value={a.reaction} onChange={e=>updateRow(setAllergies,i,{reaction:e.target.value})}/>
     <button type="button" className="cp-remove" aria-label="알레르기 삭제" onClick={()=>removeRow(setAllergies,i)}><Trash2 size={15}/></button>
    </div>)}
    <datalist id="cp-allergy-hints">{ALLERGY_HINTS.map(c=><option value={c} key={c}/>)}</datalist>
    <button type="button" className="text-button" onClick={()=>setAllergies(a=>[...a,emptyAllergy()])}><Plus size={15}/> 알레르기 추가</button>
   </div>

   <div className="cp-section">
    <h3>검사 수치</h3>
    {labs.map((l,i)=><div className="cp-row cp-row-lab" key={i}>
     <input placeholder="항목 (예: INR)" value={l.name} onChange={e=>updateRow(setLabs,i,{name:e.target.value})}/>
     <input type="number" placeholder="값" value={l.value} onChange={e=>updateRow(setLabs,i,{value:e.target.value})}/>
     <input placeholder="단위" value={l.unit} onChange={e=>updateRow(setLabs,i,{unit:e.target.value})}/>
     <input type="date" value={l.date} onChange={e=>updateRow(setLabs,i,{date:e.target.value})}/>
     <input type="number" placeholder="정상 하한" value={l.low} onChange={e=>updateRow(setLabs,i,{low:e.target.value})}/>
     <input type="number" placeholder="정상 상한" value={l.high} onChange={e=>updateRow(setLabs,i,{high:e.target.value})}/>
     <button type="button" className="cp-remove" aria-label="검사 삭제" onClick={()=>removeRow(setLabs,i)}><Trash2 size={15}/></button>
    </div>)}
    <button type="button" className="text-button" onClick={()=>setLabs(l=>[...l,emptyLab()])}><Plus size={15}/> 검사 추가</button>
   </div>

   <div className="cp-section">
    <h3>과거 병력 <small>(선택)</small></h3>
    <div className="cp-tags">{history.map(h=><span className="cp-tag" key={h}>{h}<button type="button" onClick={()=>setHistory(hs=>hs.filter(x=>x!==h))}><X size={12}/></button></span>)}</div>
    <div className="cp-tag-input"><input placeholder="예: 2023년 위장관 출혈 (Enter로 추가)" value={historyInput} onChange={e=>setHistoryInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();addTag(history,setHistory,historyInput,setHistoryInput)}}}/><button type="button" className="outline-button" onClick={()=>addTag(history,setHistory,historyInput,setHistoryInput)}>추가</button></div>
   </div>

   {error&&<p className="cp-error" role="alert">{error}</p>}
   <div className="cp-actions"><button type="button" className="outline-button" onClick={onClose} disabled={busy}>취소</button><button className="primary-button" disabled={busy}>{busy?'분석 중…':'환자 생성 및 분석'}</button></div>
  </form>
 </section>
 </div>;
}

import React,{useState,useEffect} from 'react';
import {Plus,Check} from 'lucide-react';
import {api} from '../lib/api';

const emptyForm={author:'담당의',s:'',o:'',a:'',p:''};

// SOAP note editor. Signing a note (POST /notes/{id}/sign) freezes its S/O/A/P text on the
// server -- a PATCH after that is rejected there (409), so the only edit path once signed is the
// explicit amendment form below, which always requires an author and a reason.
const emptyVitals={sbp:'',dbp:'',heart_rate:'',respiratory_rate:'',temperature_c:'',spo2:'',height_cm:'',weight_kg:''};
const num=v=>v===''?undefined:Number(v);
const emptyDiagnosis={display_name:'',code:'',code_system:'ICD-10',diagnosis_type:'secondary',clinician:'담당의'};

export default function ClinicalNotePanel({patientId,encounters,onStartEncounter,onVitalsChanged,onDiagnosisChanged,disabled}){
 const [activeId,setActiveId]=useState('');
 const [notes,setNotes]=useState([]),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [form,setForm]=useState(emptyForm);
 const [amending,setAmending]=useState(null),[amendReason,setAmendReason]=useState(''),[amendPlan,setAmendPlan]=useState('');
 const [vitals,setVitals]=useState(emptyVitals),[vitalsBusy,setVitalsBusy]=useState(false),[vitalsAssessment,setVitalsAssessment]=useState(null);
 const [problemList,setProblemList]=useState([]),[diagnosis,setDiagnosis]=useState(emptyDiagnosis),[diagnosisBusy,setDiagnosisBusy]=useState(false);

 useEffect(()=>{
  if(!encounters?.length){setActiveId('');return}
  if(!encounters.some(e=>e.id===activeId))setActiveId(encounters[0].id);
 },[encounters]);

 async function refresh(eid){
  const id=eid||activeId;if(!id)return;
  try{setNotes(await api('/encounters/'+id+'/notes'))}catch(e){setError(e.message)}
 }
 useEffect(()=>{if(activeId)refresh(activeId)},[activeId]);

 async function refreshProblemList(){
  if(!patientId)return;
  try{setProblemList(await api('/patients/'+patientId+'/problem-list'))}catch(e){setError(e.message)}
 }
 useEffect(()=>{refreshProblemList()},[patientId]);

 async function createDiagnosis(e){
  e.preventDefault();if(!activeId||!diagnosis.display_name.trim())return;setDiagnosisBusy(true);setError('');
  try{
   await api('/encounters/'+activeId+'/diagnoses',{display_name:diagnosis.display_name.trim(),diagnosis_type:diagnosis.diagnosis_type,
    code:diagnosis.code,code_system:diagnosis.code_system,clinician:diagnosis.clinician});
   setDiagnosis(emptyDiagnosis);await refreshProblemList();onDiagnosisChanged?.();
  }catch(err){setError(err.message)}finally{setDiagnosisBusy(false)}
 }

 async function createNote(e){
  e.preventDefault();if(!activeId)return;setBusy(true);setError('');
  try{
   await api('/encounters/'+activeId+'/notes',{author:form.author,subjective:form.s,objective:form.o,assessment:form.a,plan:form.p});
   setForm({...emptyForm,author:form.author});await refresh();
  }catch(err){setError(err.message)}finally{setBusy(false)}
 }
 async function sign(id){setBusy(true);setError('');try{await api('/notes/'+id+'/sign',{});await refresh()}catch(e){setError(e.message)}finally{setBusy(false)}}
 async function recordVitals(e){
  e.preventDefault();if(!activeId)return;setVitalsBusy(true);setError('');setVitalsAssessment(null);
  try{
   const body=Object.fromEntries(Object.entries(vitals).map(([k,v])=>[k,num(v)]).filter(([,v])=>v!==undefined));
   const r=await api('/encounters/'+activeId+'/vitals',body);
   setVitalsAssessment(r.assessment);setVitals(emptyVitals);onVitalsChanged?.();
  }catch(err){setError(err.message)}finally{setVitalsBusy(false)}
 }
 async function submitAmend(id){
  if(!amendReason.trim())return;setBusy(true);setError('');
  try{
   await api('/notes/'+id+'/amendments',{author:form.author,reason:amendReason,plan:amendPlan||undefined});
   setAmending(null);setAmendReason('');setAmendPlan('');await refresh();
  }catch(e){setError(e.message)}finally{setBusy(false)}
 }

 if(disabled)return <p className="muted">직접 입력한 환자는 Clinical Note를 제공하지 않습니다.</p>;
 if(!encounters?.length)return <div className="empty-encounter"><p className="muted">노트를 작성하려면 먼저 Encounter가 필요합니다.</p><button className="primary-button" onClick={onStartEncounter}><Plus size={16}/> 새 Encounter 시작</button></div>;

 return <section className="white-card note-panel">
  <div className="section-head"><h2>Clinical Note (SOAP)</h2>
   <select aria-label="Encounter 선택" value={activeId} onChange={e=>setActiveId(e.target.value)}>
    {encounters.map(en=><option key={en.id} value={en.id}>{en.started_at.slice(0,10)} · {en.department||en.encounter_type}</option>)}
   </select>
  </div>
  {error&&<p className="text-danger" role="alert">{error}</p>}
  <div className="vitals-block">
   <h3>Vital Signs</h3>
   {(()=>{const enc=encounters.find(en=>en.id===activeId);const vs=enc?.vital_signs||[];
    return vs.length?<div className="vitals-history">{[...vs].sort((a,b)=>(b.measured_at||'').localeCompare(a.measured_at||'')).map(v=><div key={v.id} className="vitals-row">
     <span>{(v.measured_at||'').slice(0,16).replace('T',' ')}</span>
     <span>BP {v.sbp&&v.dbp?`${v.sbp}/${v.dbp}`:'—'}</span><span>HR {v.heart_rate??'—'}</span><span>RR {v.respiratory_rate??'—'}</span>
     <span>Temp {v.temperature_c??'—'}°C</span><span>SpO₂ {v.spo2??'—'}%</span>
    </div>)}</div>:<p className="muted">기록된 vital이 없습니다.</p>})()}
   <form onSubmit={recordVitals} className="vitals-form cp-grid">
    <label>SBP<input type="number" value={vitals.sbp} onChange={e=>setVitals(v=>({...v,sbp:e.target.value}))}/></label>
    <label>DBP<input type="number" value={vitals.dbp} onChange={e=>setVitals(v=>({...v,dbp:e.target.value}))}/></label>
    <label>Heart Rate<input type="number" value={vitals.heart_rate} onChange={e=>setVitals(v=>({...v,heart_rate:e.target.value}))}/></label>
    <label>Resp. Rate<input type="number" value={vitals.respiratory_rate} onChange={e=>setVitals(v=>({...v,respiratory_rate:e.target.value}))}/></label>
    <label>Temp (°C)<input type="number" step="0.1" value={vitals.temperature_c} onChange={e=>setVitals(v=>({...v,temperature_c:e.target.value}))}/></label>
    <label>SpO₂ (%)<input type="number" value={vitals.spo2} onChange={e=>setVitals(v=>({...v,spo2:e.target.value}))}/></label>
    <label>Height (cm)<input type="number" value={vitals.height_cm} onChange={e=>setVitals(v=>({...v,height_cm:e.target.value}))}/></label>
    <label>Weight (kg)<input type="number" value={vitals.weight_kg} onChange={e=>setVitals(v=>({...v,weight_kg:e.target.value}))}/></label>
    <button className="primary-button" disabled={vitalsBusy}>Vital 기록</button>
   </form>
   {vitalsAssessment&&<div className="vitals-assessment">
    {vitalsAssessment.bmi!=null&&<span>BMI {vitalsAssessment.bmi}</span>}
    {Object.entries(vitalsAssessment.flags).filter(([,f])=>f.status!=='normal').map(([k,f])=><span key={k} className={'badge '+(f.status==='critical'?'danger':'caution')}>{k} {f.status}</span>)}
    {Object.values(vitalsAssessment.flags).every(f=>f.status==='normal')&&<span className="muted">모두 참고범위(prototype policy) 내</span>}
   </div>}
  </div>
  <div className="diagnosis-block">
   <h3>Diagnosis / Problem List</h3>
   {problemList.length?<div className="diagnosis-list">{problemList.map(dx=><div key={dx.id} className="diagnosis-row">
    <b>{dx.display_name}</b><span>{dx.code?`${dx.code_system} ${dx.code}`:dx.code_system}</span>
    <span className="badge info">{dx.diagnosis_type==='primary'?'Primary':'Secondary'}</span>
    <span className={'badge '+(dx.status==='active'?'caution':'info')}>{dx.status==='active'?'Active':'Resolved'}</span>
    <small>{dx.diagnosed_at?.slice(0,10)}</small>
   </div>)}</div>:<p className="muted">등록된 진단이 없습니다.</p>}
   <form onSubmit={createDiagnosis} className="diagnosis-form">
    <label>Display<input value={diagnosis.display_name} onChange={e=>setDiagnosis(d=>({...d,display_name:e.target.value}))} placeholder="예: Atrial fibrillation" required/></label>
    <label>Code<input value={diagnosis.code} onChange={e=>setDiagnosis(d=>({...d,code:e.target.value}))} placeholder="예: I48.91"/></label>
    <label>Code system<select value={diagnosis.code_system} onChange={e=>setDiagnosis(d=>({...d,code_system:e.target.value}))}><option value="ICD-10">ICD-10</option><option value="SNOMED-CT">SNOMED-CT</option><option value="text">Text</option></select></label>
    <label>Type<select value={diagnosis.diagnosis_type} onChange={e=>setDiagnosis(d=>({...d,diagnosis_type:e.target.value}))}><option value="primary">Primary</option><option value="secondary">Secondary</option></select></label>
    <button className="primary-button" disabled={diagnosisBusy||!activeId}><Plus size={16}/> 진단 추가</button>
   </form>
  </div>
  <form onSubmit={createNote} className="soap-form">
   <label>작성자<input value={form.author} onChange={e=>setForm(f=>({...f,author:e.target.value}))} required/></label>
   <label>S (Subjective)<textarea value={form.s} onChange={e=>setForm(f=>({...f,s:e.target.value}))} placeholder="chief complaint, symptoms, HPI"/></label>
   <label>O (Objective)<textarea value={form.o} onChange={e=>setForm(f=>({...f,o:e.target.value}))} placeholder="vitals, exam, lab findings"/></label>
   <label>A (Assessment)<textarea value={form.a} onChange={e=>setForm(f=>({...f,a:e.target.value}))} placeholder="diagnosis, differential"/></label>
   <label>P (Plan)<textarea value={form.p} onChange={e=>setForm(f=>({...f,p:e.target.value}))} placeholder="medication, orders, follow-up"/></label>
   <button className="primary-button" disabled={busy}><Plus size={16}/> 임시 저장 (Draft)</button>
  </form>
  <div className="note-list">
   {notes.map(n=><article key={n.id} className={'note-card '+n.status}>
    <header><b>{n.status==='signed'?'서명됨':'초안'}</b><span>{n.author} · {n.created_at.slice(0,16).replace('T',' ')}{n.signed_at?' · 서명 '+n.signed_at.slice(0,16).replace('T',' '):''}</span></header>
    <dl><dt>S</dt><dd>{n.subjective||'—'}</dd><dt>O</dt><dd>{n.objective||'—'}</dd><dt>A</dt><dd>{n.assessment||'—'}</dd><dt>P</dt><dd>{n.plan||'—'}</dd></dl>
    {n.status==='draft'?<button className="outline-button" onClick={()=>sign(n.id)} disabled={busy}><Check size={15}/> 서명</button>:<>
     {n.amendments.length>0&&<div className="amendments"><b>수정 이력 ({n.amendments.length})</b>{n.amendments.map((am,i)=><p key={i}><small>{am.author} · {am.created_at.slice(0,16).replace('T',' ')}</small><br/>{am.reason}{am.plan?<> · Plan: {am.plan}</>:null}</p>)}</div>}
     {amending===n.id?<div className="amend-form">
      <textarea placeholder="수정 사유 (필수)" value={amendReason} onChange={e=>setAmendReason(e.target.value)}/>
      <textarea placeholder="수정된 Plan (선택)" value={amendPlan} onChange={e=>setAmendPlan(e.target.value)}/>
      <div><button className="primary-button" disabled={!amendReason.trim()||busy} onClick={()=>submitAmend(n.id)}>수정 제출</button><button type="button" className="text-button" onClick={()=>setAmending(null)}>취소</button></div>
     </div>:<button className="text-button" onClick={()=>{setAmending(n.id);setAmendReason('');setAmendPlan('')}}>수정 (Amendment)</button>}
    </>}
   </article>)}
   {!notes.length&&<p className="muted">이 Encounter에 작성된 노트가 없습니다.</p>}
  </div>
 </section>;
}

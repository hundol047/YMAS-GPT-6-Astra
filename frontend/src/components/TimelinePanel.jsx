import React,{useState,useEffect} from 'react';
import {api} from '../lib/api';

const FILTERS=[['all','All'],['diagnosis','Diagnosis'],['medication','Medication'],['lab','Lab'],['note','Note'],['imaging','Imaging'],['ai_warning','SynexAgent']];

// GET /patients/{id}/timeline is a pure server-side aggregation over Encounter/Diagnosis/
// MedicationOrder/LabOrder/LabResult/ClinicalNote/audit records (see backend/app/services/
// timeline.py) -- nothing here is computed client-side, this just renders what the server sends.
export default function TimelinePanel({patient,disabled}){
 const [events,setEvents]=useState([]),[busy,setBusy]=useState(false),[error,setError]=useState(''),[filter,setFilter]=useState('all');
 useEffect(()=>{
  if(!patient||disabled)return;
  const controller=new AbortController();setBusy(true);setError('');
  api('/patients/'+patient.id+'/timeline',undefined,controller.signal).then(d=>setEvents(d.events)).catch(e=>{if(e.name!=='AbortError')setError(e.message)}).finally(()=>setBusy(false));
  return()=>controller.abort();
 },[patient?.id,disabled]);
 if(disabled)return <p className="muted">직접 입력한 환자는 Timeline을 제공하지 않습니다.</p>;
 const visible=filter==='all'?events:events.filter(e=>e.type===filter);
 return <section className="white-card timeline-panel">
  <div className="section-head"><h2>Patient Timeline</h2><span className="muted">{events.length}건</span></div>
  <div className="timeline-filters" role="tablist" aria-label="Timeline 필터">{FILTERS.map(([id,label])=><button key={id} role="tab" aria-selected={filter===id} className={filter===id?'active':''} onClick={()=>setFilter(id)}>{label}</button>)}</div>
  {busy&&<p className="muted">불러오는 중…</p>}
  {error&&<p className="text-danger" role="alert">{error}</p>}
  {!busy&&!visible.length&&<p className="muted">표시할 이벤트가 없습니다.</p>}
  <ol className="timeline-list">
   {visible.map((e,i)=><li key={i} className={'timeline-item type-'+e.type}>
    <span className="timeline-date">{(e.timestamp||'').slice(0,10)}</span>
    <div className="timeline-body">
     <b>{e.title}{e.type==='ai_warning'&&<span className="timeline-tag">SynexAgent</span>}</b>
     {e.detail&&<p>{e.detail}</p>}
    </div>
   </li>)}
  </ol>
 </section>;
}

import React,{useState,useEffect} from 'react';
import {Plus,Check,TriangleAlert,RotateCw} from 'lucide-react';
import {api} from '../lib/api';
import DrugCombobox from './DrugCombobox';

// The order-entry workflow the spec calls for: 약물 선택 -> dose/route/frequency -> SynexAgent
// precheck (reuses the same before/after risk-diff logic as /prescription/simulate, see
// main.py's _agent_diff) -> warnings shown -> clinician can still submit, but only with a
// non-blank override reason -- the server re-verifies this independently (never trusts the
// client's precheck result), so this UI reflects that same gate rather than enforcing it alone.
export default function OrdersPanel({catalog,encounters,onStartEncounter,onOrdersChanged,disabled}){
 const [activeId,setActiveId]=useState('');
 useEffect(()=>{if(!encounters?.length){setActiveId('');return}if(!encounters.some(e=>e.id===activeId))setActiveId(encounters[0].id)},[encounters]);

 const [drug,setDrug]=useState(''),[dose,setDose]=useState(''),[doseUnit,setDoseUnit]=useState('mg'),[route,setRoute]=useState('PO'),[frequency,setFrequency]=useState('QD'),[duration,setDuration]=useState(''),[indication,setIndication]=useState('');
 const [precheck,setPrecheck]=useState(null),[precheckBusy,setPrecheckBusy]=useState(false);
 const [overrideReason,setOverrideReason]=useState('');
 const [confirmBusy,setConfirmBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');

 const [labName,setLabName]=useState(''),[priority,setPriority]=useState('routine'),[labIndication,setLabIndication]=useState('');
 const [labBusy,setLabBusy]=useState(false);

 function orderBody(){return {medication_code:drug,dose:Number(dose),dose_unit:doseUnit,route,frequency,duration,indication}}

 async function runPrecheck(e){
  e.preventDefault();if(!drug||!dose||!activeId)return;setPrecheckBusy(true);setError('');setPrecheck(null);setNotice('');
  try{setPrecheck(await api(`/encounters/${activeId}/medication-orders/precheck`,orderBody()))}
  catch(err){setError(err.message)}finally{setPrecheckBusy(false)}
 }
 async function confirmOrder(){
  if(!activeId)return;setConfirmBusy(true);setError('');
  try{
   const body={...orderBody()};
   if(precheck?.requires_override)body.override_reason=overrideReason;
   await api(`/encounters/${activeId}/medication-orders`,body);
   setNotice('처방이 저장되었습니다.');setPrecheck(null);setDrug('');setDose('');setOverrideReason('');setDuration('');setIndication('');
   onOrdersChanged?.();
  }catch(err){setError(err.message)}finally{setConfirmBusy(false)}
 }
 async function createLabOrder(e){
  e.preventDefault();if(!labName||!activeId)return;setLabBusy(true);setError('');setNotice('');
  try{await api(`/encounters/${activeId}/lab-orders`,{test_name:labName,priority,indication:labIndication});setNotice('검사 처방이 저장되었습니다.');setLabName('');setLabIndication('');onOrdersChanged?.()}
  catch(err){setError(err.message)}finally{setLabBusy(false)}
 }

 if(disabled)return <p className="muted">직접 입력한 환자는 Orders를 제공하지 않습니다.</p>;
 if(!encounters?.length)return <div className="empty-encounter"><p className="muted">처방을 작성하려면 먼저 Encounter가 필요합니다.</p><button className="primary-button" onClick={onStartEncounter}><Plus size={16}/> 새 Encounter 시작</button></div>;

 return <div className="orders-panel">
  <section className="white-card">
   <div className="section-head"><h2>Medication Order</h2>
    <select aria-label="Encounter 선택" value={activeId} onChange={e=>{setActiveId(e.target.value);setPrecheck(null)}}>
     {encounters.map(en=><option key={en.id} value={en.id}>{en.started_at.slice(0,10)} · {en.department||en.encounter_type}</option>)}
    </select>
   </div>
   {error&&<p className="text-danger" role="alert">{error}</p>}
   {notice&&<p className="success-message" role="status">{notice}</p>}
   <form onSubmit={runPrecheck} className="order-form cp-grid">
    <DrugCombobox label="Medication" catalog={catalog} value={drug} onChange={d=>{setDrug(d);setPrecheck(null)}}/>
    <label>Dose<input type="number" min="0" step="0.1" value={dose} onChange={e=>setDose(e.target.value)} required/></label>
    <label>Unit<input value={doseUnit} onChange={e=>setDoseUnit(e.target.value)}/></label>
    <label>Route<select value={route} onChange={e=>setRoute(e.target.value)}>{['PO','IV','IM','SC','topical'].map(r=><option key={r}>{r}</option>)}</select></label>
    <label>Frequency<input value={frequency} onChange={e=>setFrequency(e.target.value)} placeholder="QD"/></label>
    <label>Duration<input value={duration} onChange={e=>setDuration(e.target.value)} placeholder="30 days"/></label>
    <label className="cp-wide">Indication<input value={indication} onChange={e=>setIndication(e.target.value)}/></label>
    <button className="primary-button" disabled={!drug||!dose||precheckBusy}>{precheckBusy?<RotateCw size={16} className="spin"/>:null} SynexAgent 사전 분석 실행</button>
   </form>
   {precheck&&<div className="precheck-result">
    <div className="comparison"><div><small>현재 RISK INDEX</small><b>{Math.round(precheck.before.risk.risk_probability*100)}<small>/100</small></b></div><span>→</span><div><small>추가 후</small><b>{Math.round(precheck.after.risk.risk_probability*100)}<small>/100</small></b></div></div>
   <p className="muted small">모델 신호를 0–100으로 재표현한 값이며 실제 부작용 확률이 아닙니다.</p>
    {precheck.new_alerts.length>0?<>
     <div className="precheck-warning"><TriangleAlert size={18}/><b>{precheck.new_alerts.length}건의 새로운 SynexAgent 신호가 감지되었습니다.</b></div>
     {precheck.new_alerts.map(a=><div key={a.id} className="sim-alert"><span className={'badge '+a.severity}>{a.severity}</span><span>{a.title}</span></div>)}
     <label>Override 사유 (필수) — 경고를 확인했고 처방을 진행하는 임상적 이유<textarea value={overrideReason} onChange={e=>setOverrideReason(e.target.value)} required/></label>
     <button className="primary-button" disabled={!overrideReason.trim()||confirmBusy} onClick={confirmOrder}>경고 확인 후 처방 제출</button>
    </>:<>
     <p className="muted">새로운 SynexAgent 신호가 없습니다. (안전을 보증하는 것은 아닙니다)</p>
     <button className="primary-button" disabled={confirmBusy} onClick={confirmOrder}><Check size={16}/> 처방 제출</button>
    </>}
   </div>}
  </section>
  <section className="white-card">
   <h2>Lab Order</h2>
   <form onSubmit={createLabOrder} className="order-form cp-grid">
    <label>Test<input value={labName} onChange={e=>setLabName(e.target.value)} placeholder="예: INR" required/></label>
    <label>Priority<select value={priority} onChange={e=>setPriority(e.target.value)}>{['routine','urgent','stat'].map(p=><option key={p}>{p}</option>)}</select></label>
    <label className="cp-wide">Indication<input value={labIndication} onChange={e=>setLabIndication(e.target.value)}/></label>
    <button className="primary-button" disabled={!labName||labBusy}>검사 처방</button>
   </form>
  </section>
 </div>;
}

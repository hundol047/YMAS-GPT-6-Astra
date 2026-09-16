import React,{useState,useEffect} from 'react';
import {ResponsiveContainer,LineChart,Line,XAxis,YAxis,Tooltip,CartesianGrid} from 'recharts';
import {api} from '../lib/api';

const sourceLabel={legacy:'기존 기록',fhir:'FHIR',lab_order:'Lab Order'};

// Demo scope: no real lab instrument feed exists, so a result is direct clinician data entry
// (POST /lab-orders/{id}/result) -- never fabricated by SynexAgent. The trend chart reuses the
// same recharts pattern as the Overview tab's lab chart.
//
// Unified Results (GET /patients/{id}/results, backend/app/services/results.py): merges legacy/
// demo Patient.labs + FHIR-sourced Observations (already normalized into the same Patient.labs
// list by FHIRAdapter) + Clinical Workspace LabOrder/LabResult into one chronological trend per
// test name, deduplicated server-side -- this used to only show the new LabOrder-derived results,
// hiding a patient's pre-existing lab history.
export default function ResultsPanel({patient,disabled}){
 const [orders,setOrders]=useState([]),[items,setItems]=useState([]),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [entering,setEntering]=useState(null),[value,setValue]=useState(''),[refLow,setRefLow]=useState(''),[refHigh,setRefHigh]=useState(''),[unit,setUnit]=useState('');
 const [trendName,setTrendName]=useState('');

 async function refresh(){
  if(!patient)return;setBusy(true);setError('');
  try{
   const [o,res]=await Promise.all([api('/patients/'+patient.id+'/lab-orders'),api('/patients/'+patient.id+'/results')]);
   setOrders(o);setItems(res.items);
   setTrendName(t=>t&&res.items.some(x=>x.test_name===t)?t:(res.items[0]?.test_name||''));
  }catch(e){setError(e.message)}finally{setBusy(false)}
 }
 useEffect(()=>{refresh()},[patient?.id,disabled]);

 async function submitResult(orderId){
  setBusy(true);setError('');
  try{
   await api(`/lab-orders/${orderId}/result`,{value:Number(value),unit,reference_low:refLow===''?undefined:Number(refLow),reference_high:refHigh===''?undefined:Number(refHigh)});
   setEntering(null);setValue('');setRefLow('');setRefHigh('');setUnit('');await refresh();
  }catch(e){setError(e.message)}finally{setBusy(false)}
 }

 if(disabled)return <p className="muted">직접 입력한 환자는 Results를 제공하지 않습니다.</p>;
 const pending=orders.filter(o=>o.status==='ordered');
 // Deduplicate defensively by (date, test_name, value) in case two sources describe the same
 // real reading -- the backend already dedupes lab_order-vs-legacy overlap, this only guards
 // against a coincidental FHIR/legacy overlap the server can't know about.
 const seen=new Set();
 const deduped=items.filter(r=>{const key=r.measured_at.slice(0,10)+'|'+r.test_name+'|'+r.value;if(seen.has(key))return false;seen.add(key);return true});
 const names=[...new Set(deduped.map(r=>r.test_name))];
 const grouped={};
 for(const name of names)grouped[name]=deduped.filter(r=>r.test_name===name).sort((a,b)=>a.measured_at.localeCompare(b.measured_at));
 const trendData=(grouped[trendName]||[]).map(r=>({...r,day:r.measured_at.slice(5,10)}));
 const latest=trendData.at(-1);

 return <div className="results-panel">
  <section className="white-card">
   <h2>대기 중인 검사 Order</h2>
   {error&&<p className="text-danger" role="alert">{error}</p>}
   {!pending.length&&<p className="muted">대기 중인 검사가 없습니다.</p>}
   {pending.map(o=><div key={o.id} className="lab-order-row">
    <div><b>{o.test_name}</b><small>{o.priority} · {o.indication||'적응증 미기재'}</small></div>
    {entering===o.id?<div className="result-entry">
     <input type="number" placeholder="값" value={value} onChange={e=>setValue(e.target.value)} aria-label={o.test_name+' 결과 값'}/>
     <input placeholder="단위" value={unit} onChange={e=>setUnit(e.target.value)}/>
     <input type="number" placeholder="하한" value={refLow} onChange={e=>setRefLow(e.target.value)}/>
     <input type="number" placeholder="상한" value={refHigh} onChange={e=>setRefHigh(e.target.value)}/>
     <button className="primary-button" disabled={!value||busy} onClick={()=>submitResult(o.id)}>결과 저장</button>
    </div>:<button className="outline-button" onClick={()=>setEntering(o.id)}>결과 입력</button>}
   </div>)}
  </section>
  <section className="white-card">
   <div className="section-head"><h2>검사 결과 추세 (통합)</h2>{!!names.length&&<select aria-label="검사 항목 선택" value={trendName} onChange={e=>setTrendName(e.target.value)}>{names.map(n=><option key={n}>{n}</option>)}</select>}</div>
   {latest&&<p className="muted">최근: {latest.value}{latest.unit} ({latest.abnormal_flag}) · 참고범위 {latest.reference_low}–{latest.reference_high}</p>}
   {trendData.length?<ResponsiveContainer width="100%" height={200}><LineChart data={trendData} margin={{top:10,right:18,bottom:0,left:-20}}><CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e5eced"/><XAxis dataKey="day" axisLine={false} tickLine={false} tick={{fontSize:12,fill:'#697c82'}}/><YAxis domain={['auto','auto']} axisLine={false} tickLine={false} tick={{fontSize:12,fill:'#697c82'}}/><Tooltip formatter={v=>[v,trendName]}/><Line type="linear" dataKey="value" stroke="#008a78" strokeWidth={2.5} dot={{r:4,fill:'#fff',strokeWidth:2}} activeDot={{r:6}}/></LineChart></ResponsiveContainer>:<p className="muted">결과 데이터가 없습니다.</p>}
   {trendData.length>1&&<p className="result-trend">{trendName}: {trendData.map(r=>r.value).join(' → ')}{trendData.at(-1).value>trendData[0].value?' ↑':trendData.at(-1).value<trendData[0].value?' ↓':''}</p>}
  </section>
  <section className="white-card">
   <h2>전체 검사 항목 (출처 통합)</h2>
   {!names.length&&<p className="muted">결과 데이터가 없습니다.</p>}
   {names.map(name=><div key={name} className="result-group">
    <b>{name}</b>
    <div className="result-trend">{grouped[name].map((r,i)=><React.Fragment key={r.id}>{i>0&&<span>→</span>}<span>{r.value}{r.unit}</span><span className="source-tag">{sourceLabel[r.source]||r.source} · {r.measured_at.slice(0,10)}</span></React.Fragment>)}</div>
   </div>)}
  </section>
 </div>;
}

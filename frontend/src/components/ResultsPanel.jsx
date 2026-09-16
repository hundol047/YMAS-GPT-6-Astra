import React,{useState,useEffect} from 'react';
import {ResponsiveContainer,LineChart,Line,XAxis,YAxis,Tooltip,CartesianGrid} from 'recharts';
import {api} from '../lib/api';

// Demo scope: no real lab instrument feed exists, so a result is direct clinician data entry
// (POST /lab-orders/{id}/result) -- never fabricated by SynexAgent. The trend chart reuses the
// same recharts pattern as the Overview tab's lab chart.
export default function ResultsPanel({patient,disabled}){
 const [orders,setOrders]=useState([]),[results,setResults]=useState([]),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [entering,setEntering]=useState(null),[value,setValue]=useState(''),[refLow,setRefLow]=useState(''),[refHigh,setRefHigh]=useState(''),[unit,setUnit]=useState('');
 const [trendName,setTrendName]=useState('');

 async function refresh(){
  if(!patient)return;setBusy(true);setError('');
  try{
   const [o,r]=await Promise.all([api('/patients/'+patient.id+'/lab-orders'),api('/patients/'+patient.id+'/lab-results')]);
   setOrders(o);setResults(r);
   setTrendName(t=>t&&r.some(x=>x.test_name===t)?t:(r[0]?.test_name||''));
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
 const names=[...new Set(results.map(r=>r.test_name))];
 const trendData=results.filter(r=>r.test_name===trendName).sort((a,b)=>a.measured_at.localeCompare(b.measured_at)).map(r=>({...r,day:r.measured_at.slice(5,10)}));
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
   <div className="section-head"><h2>검사 결과 추세</h2>{!!names.length&&<select aria-label="검사 항목 선택" value={trendName} onChange={e=>setTrendName(e.target.value)}>{names.map(n=><option key={n}>{n}</option>)}</select>}</div>
   {latest&&<p className="muted">최근: {latest.value}{latest.unit} ({latest.abnormal_flag}) · 참고범위 {latest.reference_low}–{latest.reference_high}</p>}
   {trendData.length?<ResponsiveContainer width="100%" height={200}><LineChart data={trendData} margin={{top:10,right:18,bottom:0,left:-20}}><CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e5eced"/><XAxis dataKey="day" axisLine={false} tickLine={false} tick={{fontSize:12,fill:'#697c82'}}/><YAxis domain={['auto','auto']} axisLine={false} tickLine={false} tick={{fontSize:12,fill:'#697c82'}}/><Tooltip formatter={v=>[v,trendName]}/><Line type="linear" dataKey="value" stroke="#008a78" strokeWidth={2.5} dot={{r:4,fill:'#fff',strokeWidth:2}} activeDot={{r:6}}/></LineChart></ResponsiveContainer>:<p className="muted">결과 데이터가 없습니다.</p>}
  </section>
 </div>;
}

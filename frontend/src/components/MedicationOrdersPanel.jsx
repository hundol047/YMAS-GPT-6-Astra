import React,{useState,useEffect} from 'react';
import {api} from '../lib/api';

// Structured MedicationOrder records (id/dose/route/status/override_reason), distinct from the
// flat "현재 복용 약물" table on the 진료 기록 tab -- a confirmed order also dual-writes into that
// flat list (see repositories.py), so both views stay consistent; this one shows the order-level
// detail (who confirmed it, was there an override, can it still be cancelled).
export default function MedicationOrdersPanel({patient,catalog,disabled}){
 const [orders,setOrders]=useState([]),[busy,setBusy]=useState(false),[error,setError]=useState('');
 async function refresh(){if(!patient)return;try{setOrders(await api('/patients/'+patient.id+'/medication-orders'))}catch(e){setError(e.message)}}
 useEffect(()=>{refresh()},[patient?.id,disabled]);
 async function cancel(id){setBusy(true);setError('');try{await api(`/medication-orders/${id}/cancel`,{});await refresh()}catch(e){setError(e.message)}finally{setBusy(false)}}
 if(disabled)return <p className="muted">직접 입력한 환자는 Medication Orders를 제공하지 않습니다.</p>;
 const medInfo=id=>catalog?.find(d=>d.id===id)||{name_ko:id};
 return <section className="white-card">
  <h2>Medication Orders</h2>
  {error&&<p className="text-danger" role="alert">{error}</p>}
  {!orders.length&&<p className="muted">기록된 처방 order가 없습니다. Orders 탭에서 처방을 시작하십시오.</p>}
  {!!orders.length&&<div className="table-wrap"><table><thead><tr><th>약물</th><th>Dose</th><th>Route</th><th>상태</th><th>Override 사유</th><th/></tr></thead><tbody>
   {orders.map(o=><tr key={o.id}><td><b>{medInfo(o.medication_code).name_ko}</b><small>{o.medication_code}</small></td><td>{o.dose}{o.dose_unit}</td><td>{o.route}</td>
    <td><span className={'badge '+(o.status==='confirmed'?'info':o.status==='cancelled'?'caution':'')}>{o.status}</span></td>
    <td>{o.override_reason||'—'}</td>
    <td>{o.status==='confirmed'&&<button className="text-button" onClick={()=>cancel(o.id)} disabled={busy}>취소</button>}</td></tr>)}
  </tbody></table></div>}
 </section>;
}

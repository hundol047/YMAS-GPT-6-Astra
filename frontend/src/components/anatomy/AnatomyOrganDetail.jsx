import React,{useState,useEffect} from 'react';
import AnatomyRiskPanel from './AnatomyRiskPanel';
import {organs,targetsFor,severityFor,colors,labels,ORGAN_LABS} from '../../data/anatomyMap';

const TABS=[['clinical','Clinical Data'],['anatomy','Anatomy'],['imaging','Imaging'],['labs','Labs'],['medication','Medication'],['warnings','Warnings']];

// Wraps the existing (unchanged) AnatomyRiskPanel as the default "Clinical Data" tab so nothing
// that already reads `.an-risk-panel` breaks, and adds the Anatomy/Imaging/Labs/Medication/
// Warnings tabs the Patient Digital Twin spec calls for. Labs/Medication use the fixed
// anatomyMap.ORGAN_LABS table and the backend's own alert sources -- never an LLM guess at
// runtime.
// Deterministic monotonic-trend check over real stored lab values (last 3 points) -- same method
// as backend/app/services/clinical_summary.py, applied client-side here so the 3D detail panel can
// show it without a round-trip. "감지" (detected) only, never "진단"/"확정" -- this is a trend
// observation, not a clinical diagnosis.
function labTrend(points){
 const recent=points.slice(-3);
 if(recent.length<2)return null;
 const values=recent.map(p=>p.value);
 const diffs=values.slice(1).map((v,i)=>v-values[i]);
 if(diffs.every(d=>d>0))return{direction:'상승',values};
 if(diffs.every(d=>d<0))return{direction:'하락',values};
 return null;
}

export default function AnatomyOrganDetail(props){
 const {selected,data,patient,catalog,demoImagingOpen,onOpenImaging}=props;
 const [tab,setTab]=useState('clinical');
 useEffect(()=>{setTab('clinical')},[selected]);
 const organ=organs.find(o=>o.id===selected);
 const targets=targetsFor(data,organ?.group);
 const severity=severityFor(targets);
 const labNames=organ?(ORGAN_LABS[organ.group]||[]):[];
 const labs=(patient?.labs||[]).filter(l=>labNames.includes(l.name));
 const labsByName={};
 labs.forEach(l=>{(labsByName[l.name]=labsByName[l.name]||[]).push(l)});
 Object.values(labsByName).forEach(arr=>arr.sort((a,b)=>a.date.localeCompare(b.date)));
 const findings=Object.entries(labsByName).map(([name,points])=>{const t=labTrend(points);return t?{name,...t}:null}).filter(Boolean);
 const medIds=[...new Set(targets.flatMap(t=>t.sources.filter(s=>s.type==='medication').map(s=>s.name)))];
 const meds=(patient?.medications||[]).filter(m=>medIds.includes(m.drug_id));
 const medInfo=id=>catalog?.find(d=>d.id===id)||{name_ko:id,group_ko:''};
 const warnings=targets.filter(t=>t.alert_id);
 return <div className="an-detail-tabs">
 <div className="an-detail-tabbar" role="tablist" aria-label="장기 상세">
  {TABS.map(([id,label])=><button key={id} role="tab" aria-selected={tab===id} className={tab===id?'active':''} onClick={()=>setTab(id)}>{label}</button>)}
 </div>
 {tab==='clinical'&&<AnatomyRiskPanel {...props}/>}
 {tab==='anatomy'&&<section className="an-risk-panel an-anatomy-tab">
  <h3>ANATOMY</h3>
  {organ?<><h2>{organ.ko}</h2><p>{organ.en} · reference group: {organ.group}</p><strong style={{color:colors[severity]}}>{labels[severity]}</strong><p className="an-note">참고용 절차적 모델 좌표이며 환자별 실제 크기·위치를 나타내지 않습니다.</p></>:<p>장기를 선택하십시오.</p>}
 </section>}
 {tab==='imaging'&&<section className="an-risk-panel">
  <h3>IMAGING</h3>
  {demoImagingOpen
   ?<p>데모 참고 영상이 열려 있습니다. 하단 IMAGING STUDIES 패널에서 단면을 확인하십시오. 실제 환자 영상이 아닙니다.</p>
   :<><p>이 환자에게 연결된 실제 의료영상이 없습니다.</p><button className="outline-button" onClick={onOpenImaging}>OPEN DEMO IMAGING</button></>}
 </section>}
 {tab==='labs'&&<section className="an-risk-panel">
  <h3>LABS</h3>
  {Object.keys(labsByName).length?Object.entries(labsByName).map(([name,points])=><div key={name} className="an-lab-row">
    <b>{name}</b>
    <span>{points.map(p=>p.value).join(' → ')} <small>{points.at(-1).unit}</small></span>
    <small>{points.at(-1).date} · 참고범위 {points.at(-1).low}–{points.at(-1).high}</small>
   </div>):<p>이 장기와 연결된 검사 데이터가 없습니다.</p>}
  <h4 className="an-findings-head">SynexAgent Findings</h4>
  {findings.length?findings.map((f,i)=><p key={i} className="an-finding">{f.name} {f.direction} 추세 감지 ({f.values.join(' → ')}). 임상적 확정 진단이 아니며 원기록 확인이 필요합니다.</p>):<p className="an-note">감지된 연속 추세가 없습니다.</p>}
 </section>}
 {tab==='medication'&&<section className="an-risk-panel">
  <h3>MEDICATION</h3>
  {meds.length?meds.map((m,i)=><div key={i} className="an-lab-row"><b>{medInfo(m.drug_id).name_ko}</b><span>{medInfo(m.drug_id).group_ko}</span></div>):<p>이 장기와 연결된 약물 신호가 없습니다.</p>}
 </section>}
 {tab==='warnings'&&<section className="an-risk-panel">
  <h3>WARNINGS</h3>
  {warnings.length?warnings.map((t,i)=><article key={i}><b>{t.title}</b><p>{t.reason}</p></article>):<p>연결된 SynexAgent 경고가 없습니다.</p>}
 </section>}
 </div>;
}

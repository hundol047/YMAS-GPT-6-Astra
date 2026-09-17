import React,{useState,useEffect,useRef,lazy,Suspense} from 'react';
const AnatomyWorkspace=lazy(()=>import('./components/anatomy/AnatomyWorkspace'));
import CustomPatientForm from './components/CustomPatientForm';
import DrugCombobox from './components/DrugCombobox';
import {organs} from './data/anatomyMap';
import {Activity,ArrowUpRight,ArrowRight,Search,Users,ShieldCheck,TriangleAlert,Pill,FlaskConical,HeartPulse,ChevronRight,Check,Plus,X,RotateCw,ClipboardCheck,History,Database,BrainCircuit,PanelRightClose,Info,Layers,FileText,CircleCheck,Clock,UserPlus,Trash2} from 'lucide-react';
import {ResponsiveContainer,LineChart,Line,XAxis,YAxis,Tooltip,CartesianGrid,ReferenceArea} from 'recharts';
import {api,BASE,streamSSE} from './lib/api';
import PatientClinicalHeader from './components/PatientClinicalHeader';
import TimelinePanel from './components/TimelinePanel';
import ClinicalNotePanel from './components/ClinicalNotePanel';
import OrdersPanel from './components/OrdersPanel';
import ResultsPanel from './components/ResultsPanel';
import MedicationOrdersPanel from './components/MedicationOrdersPanel';

const STEPS=['Patient','Medication','Drug Interaction','Allergy','Condition','Labs','Risk Model','Clinical Summary'];
const stepIcons=[Users,Pill,Layers,ShieldCheck,HeartPulse,FlaskConical,BrainCircuit,FileText];
const featureLabels={drug_conflict:'상호작용·규칙 신호',comorbidity_load:'기저질환 부담',age_risk:'연령',allergy_flag:'알레르기 이력',adverse_history:'과거 약물 반응',polypharmacy_load:'다약제 부담',therapy_duration_load:'조제·리필 횟수'};
const severityLabels={danger:'위험',caution:'주의',info:'정보'};
// Frontend-only lookup by alert type -- not a new backend computation, matches the "reuse what
// already exists in alert.evidence/reason/drugs/source" approach for the WHY THIS ALERT section.
const RECOMMENDED_ACTIONS={drug_interaction:'약물 상호작용 재검토 및 대체/모니터링 계획 수립을 고려하십시오.',allergy:'알레르기 원기록을 확인하고 교차반응 가능성을 검토하십시오.',drug_condition:'기저질환과 약물의 상호작용을 재평가하십시오.',duplicate_group:'동일 약물군 중복 처방 여부를 확인하십시오.',duplicate_ingredient:'동일 성분 중복 여부를 확인하십시오.',polypharmacy:'전체 처방 목록을 재검토하고 불필요한 약물 정리를 고려하십시오.',adverse_history:'과거 중증 반응 원기록을 확인하십시오.',caution_accumulation:'누적된 주의 신호를 종합적으로 재평가하십시오.',lab_review:'검사 수치와 약물의 연관성을 재검토하고 추적 관찰하십시오.'};
function recommendedAction(a){return RECOMMENDED_ACTIONS[a.type]||'원처방과 근거를 검토하고 필요한 경우 전문의 상담을 고려하십시오.'}
// Human-readable labels for every audit event this app's backend actually records (see
// backend/app/services/audit.py callers) -- an event type missing here falls back to the raw
// internal string (a.event) rather than crashing, but every currently-emitted event should have an
// entry so the Audit tab never shows a raw backend identifier like 'note_created' to a clinician.
const AUDIT_EVENT_LABELS={patient_selected:'환자 선택',analysis_started:'분석 시작',analysis_completed:'AI 분석 완료',
 alert_detected:'위험 신호 탐지',prescription_simulated:'가상 처방 비교',simulation_baseline:'시뮬레이션 기준 분석',
 simulation_proposal:'시뮬레이션 추가 분석',alert_reviewed:'의료진 확인',alert_dismissed:'경고 무시 기록',
 alert_deferred:'검토 보류',alert_feedback:'AI 피드백 제출',ai_warning_viewed:'AI 경고 확인',
 encounter_created:'진료(Encounter) 생성',encounter_updated:'진료(Encounter) 정보 수정',vitals_recorded:'활력징후 기록',
 note_created:'SOAP 노트 작성',note_modified:'SOAP 노트 수정(초안)',note_signed:'SOAP 노트 서명',
 note_amended:'서명된 노트 Amendment 추가',diagnosis_added:'진단(Diagnosis) 등록',medication_ordered:'처방(Medication Order) 등록',
 medication_cancelled:'처방 취소',warning_overridden:'SynexAgent 경고 Override',lab_ordered:'검사(Lab Order) 등록',
 lab_order_cancelled:'검사 주문 취소',lab_result_recorded:'검사 결과 입력',cds_hook_fired:'CDS Hooks 호출'}
// Mirrors backend/app/services/rule_engine.py's own `related` lab<->drug map (used there for
// lab_review alerts) so a drug_interaction alert (e.g. warfarin+aspirin) can also surface the
// patient's own most recent relevant lab value (e.g. INR) as a patient-specific factor -- pulled
// from real patient.labs data, never fabricated.
const DRUG_RELATED_LABS={warfarin:['INR'],metformin:['eGFR','Creatinine','Glucose'],lithium:['eGFR','Creatinine'],ibuprofen:['eGFR'],lisinopril:['Potassium'],spironolactone:['Potassium'],digoxin:['Potassium'],simvastatin:['AST','ALT']};
const fmt=v=>v*100<0.1?'<0.1':v*100>99.9?'>99.9':(v*100).toFixed(1);
// SYNEX RISK INDEX: risk_probability re-expressed as a rounded 0-100 index, never shown as a
// percentage/probability -- see the disclaimer next to the main risk-card.
const riskIndex=v=>Math.round(v*100);
function Badge({severity,children}){return <span className={'badge '+severity}>{children||severityLabels[severity]}</span>}
export default function App(){
 const [patients,setPatients]=useState([]),[catalog,setCatalog]=useState([]),[selected,setSelected]=useState('SYN-002'),[query,setQuery]=useState(''),[patient,setPatient]=useState(null),[analysis,setAnalysis]=useState(null),[steps,setSteps]=useState([]),[busy,setBusy]=useState(false),[error,setError]=useState(''),[tab,setTab]=useState('overview'),[alert,setAlert]=useState(null),[simulation,setSimulation]=useState(null),[drug,setDrug]=useState(''),[simBusy,setSimBusy]=useState(false),[audit,setAudit]=useState([]),[reviewReason,setReviewReason]=useState(''),[reviewed,setReviewed]=useState({}),[reviewBusy,setReviewBusy]=useState(false),[notice,setNotice]=useState(''),[labName,setLabName]=useState('INR'),[revision,setRevision]=useState(0),[boot,setBoot]=useState(0);
 const [anatomyFocus,setAnatomyFocus]=useState(null);
 const [dataQuality,setDataQuality]=useState(null);
 const [encounters,setEncounters]=useState([]);
 const [clinicalSummary,setClinicalSummary]=useState(null);
 const [timelineHighlight,setTimelineHighlight]=useState(null);
 const [customPatients,setCustomPatients]=useState([]),[customResults,setCustomResults]=useState({}),[customOpen,setCustomOpen]=useState(false);
 const [patientsUnavailable,setPatientsUnavailable]=useState(false),[fhirLookup,setFhirLookup]=useState('');
 const epoch=useRef(0), dialogRef=useRef(null), priorFocus=useRef(null), customRef=useRef([]);
 useEffect(()=>{
  const controller=new AbortController();
  api('/catalog',undefined,controller.signal).then(setCatalog).catch(e=>{if(e.name!=='AbortError')setError(e.message)});
  // Separate from /catalog: EMR_MODE=fhir makes /patients (roster browsing) return 501 by design
  // (see backend/app/services/emr_adapter.py FHIRAdapter.list()) -- that must not also block the
  // drug catalog from loading, and the UI needs to fall back to manual patient-ID lookup instead
  // of just showing a dead error banner.
  fetch(BASE+'/patients',{signal:controller.signal,credentials:'include'}).then(async r=>{
   if(r.status===501){
    setPatientsUnavailable(true);setPatients([]);
    // Production SMART on FHIR flow: the EMR already chose the patient via SMART Launch, and
    // /smart/callback stored that in a server-side session (HttpOnly cookie, never a token in the
    // browser -- see backend/app/services/smart_launch.py). If that session exists, use its
    // patient automatically instead of asking the clinician to type an id by hand.
    api('/session/context',undefined,controller.signal).then(ctx=>{if(ctx.patient_id)setSelected(ctx.patient_id)}).catch(()=>{});
    return;
   }
   if(!r.ok){let data;try{data=await r.json()}catch{}throw new Error(typeof data?.detail==='string'?data.detail:`요청 실패 (${r.status}). 서버 연결을 확인하십시오.`)}
   setPatientsUnavailable(false);setPatients(await r.json());
  }).catch(e=>{if(e.name!=='AbortError')setError(e.message)});
  return()=>controller.abort();
 },[boot]);
 useEffect(()=>{customRef.current=customPatients},[customPatients]);
 useEffect(()=>{
  const run=++epoch.current,controller=new AbortController();let streamController,timers=[];
  setPatient(null);setAnalysis(null);setSteps([]);setBusy(true);setError('');setSimulation(null);setAlert(null);setNotice('');setReviewed({});setAudit([]);setTab(t=>t==='anatomy'?'anatomy':'overview');setDrug('');setDataQuality(null);setEncounters([]);setClinicalSummary(null);setTimelineHighlight(null);
  const custom=customRef.current.find(c=>c.id===selected);
  if(custom){
   setPatient(custom);setLabName(custom.labs[0]?.name||'INR');
   const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
   api('/medication-check',custom,controller.signal).then(result=>{
    if(run!==epoch.current)return;
    setCustomResults(prev=>({...prev,[custom.id]:result}));
    result.steps.forEach((s,i)=>timers.push(setTimeout(()=>{if(run===epoch.current)setSteps(prev=>[...prev,s])},reduced?0:i*120)));
    timers.push(setTimeout(()=>{if(run===epoch.current){setAnalysis(result);setBusy(false)}},reduced?0:result.steps.length*120));
   }).catch(e=>{if(e.name!=='AbortError'&&run===epoch.current){setError(e.message);setBusy(false)}});
   return()=>{controller.abort();timers.forEach(clearTimeout)};
  }
  api('/patients/'+selected,undefined,controller.signal).then(p=>{
   if(run!==epoch.current)return;setPatient(p);setLabName(p.id==='SYN-005'?'eGFR':'INR');
   api('/patients/'+selected+'/data-quality',undefined,controller.signal).then(dq=>{if(run===epoch.current)setDataQuality(dq)}).catch(()=>{});
   api('/patients/'+selected+'/encounters',undefined,controller.signal).then(es=>{if(run===epoch.current)setEncounters(es)}).catch(()=>{});
   api('/patients/'+selected+'/clinical-summary',undefined,controller.signal).then(cs=>{if(run===epoch.current)setClinicalSummary(cs)}).catch(()=>{});
   streamController=new AbortController();const received=[];
   streamSSE('/agent/stream/'+selected,{signal:streamController.signal,onEvent:(event,data)=>{
    if(event==='step'){received.push(JSON.parse(data));return}
    if(event==='result'){
     const result=JSON.parse(data);const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
     // Reveal completed server steps. Labels explicitly say this is a result playback.
     received.forEach((s,i)=>timers.push(setTimeout(()=>{if(run===epoch.current)setSteps(prev=>[...prev,s])},reduced?0:i*120)));
     timers.push(setTimeout(()=>{if(run===epoch.current){setAnalysis(result);setBusy(false);refreshAudit(selected,run)}},reduced?0:received.length*120));
     return;
    }
    if(event==='failure'){if(run===epoch.current){setError('분석에 실패했습니다. 다시 분석을 눌러주십시오.');setBusy(false)}}
   }}).catch(e=>{if(e.name!=='AbortError'&&run===epoch.current){setError('분석 서버 연결이 끊겼습니다. 다시 분석을 눌러주십시오.');setBusy(false)}});
  }).catch(e=>{if(e.name!=='AbortError'&&run===epoch.current){setError(e.message);setBusy(false)}});
  return()=>{controller.abort();streamController?.abort();timers.forEach(clearTimeout)};
 },[selected,revision]);
 async function refreshAudit(pid=selected,run=epoch.current){try{const data=await api('/audit/'+pid);if(run===epoch.current)setAudit(data)}catch(e){if(run===epoch.current)setError(e.message)}}
 async function refreshEncounters(){if(customRef.current.some(c=>c.id===selected))return;try{setEncounters(await api('/patients/'+selected+'/encounters'))}catch(e){setError(e.message)}}
 async function refreshClinicalSummary(){if(customRef.current.some(c=>c.id===selected))return;try{setClinicalSummary(await api('/patients/'+selected+'/clinical-summary'))}catch{}}
 function jumpToSource(sourceEvents){setTimelineHighlight(new Set((sourceEvents||[]).filter(Boolean)));setTab('timeline')}
 async function startEncounter(){
  if(customRef.current.some(c=>c.id===selected))return;
  const last=[...encounters].sort((a,b)=>(b.started_at||'').localeCompare(a.started_at||''))[0];
  try{
   const enc=await api('/patients/'+selected+'/encounters',{encounter_type:'outpatient',department:last?.department||'',attending_physician:last?.attending_physician||'',chief_complaint:'금일 진료'});
   setEncounters(es=>[enc,...es]);
  }catch(e){setError(e.message)}
 }
 async function createCustomPatient(p){
  const result=await api('/medication-check',p);
  setCustomPatients(cs=>[...cs,p]);setCustomResults(r=>({...r,[p.id]:result}));setCustomOpen(false);setSelected(p.id);
 }
 function removeCustomPatient(id){setCustomPatients(cs=>cs.filter(c=>c.id!==id));setCustomResults(({[id]:_,...rest})=>rest);if(selected===id)setSelected(patients[0]?.id||'')}
 async function simulate(e){
  e.preventDefault();if(!drug)return;const run=epoch.current;setSimBusy(true);setError('');setSimulation(null);
  try{
   const custom=customRef.current.find(c=>c.id===selected);
   let s;
   if(custom){
    const before=analysis;
    const proposal={...custom,medications:[...custom.medications,{drug_id:drug,dispenses:1,status:'active',note:'Simulation only'}]};
    const after=await api('/medication-check',proposal);
    const oldIds=new Set(before.alerts.map(a=>a.id));
    s={patient_id:custom.id,drug:catalog.find(d=>d.id===drug),before,after,delta_percentage_points:(after.risk.risk_probability-before.risk.risk_probability)*100,new_alerts:after.alerts.filter(a=>!oldIds.has(a.id)),original_unchanged:true,prescription_committed:false};
   }else s=await api('/prescription/simulate',{patient_id:selected,drug_id:drug});
   if(run===epoch.current){setSimulation(s);if(!custom)refreshAudit()}
  }catch(e){if(run===epoch.current)setError(e.message)}finally{if(run===epoch.current)setSimBusy(false)}
 }
 useEffect(()=>{setSimBusy(false)},[selected]);
 function openAlert(a,aid=analysis?.analysis_id){priorFocus.current=document.activeElement;setAlert({...a,analysis_id:aid});setReviewReason('');setNotice('')}
 function showAnatomy(a){
  const simulated=simulation?.after.analysis_id===a.analysis_id;
  const result=simulated?simulation.after:analysis;
  const targets=[...(result?.anatomy?.targets||[]),...(result?.anatomy?.systemic||[])];
  const target=targets.find(t=>t.alert_id===a.id);
  if(!target)return;
  setAnatomyFocus({patientId:selected,organId:organs.find(o=>o.group===target.organ_id)?.id||'vascular',alertId:a.id,simulated,nonce:Date.now()});
  setAlert(null);setTab('anatomy');
 }
 function closeAlert(){setAlert(null);priorFocus.current?.focus()}
 useEffect(()=>{if(!alert)return;dialogRef.current?.focus();const handler=e=>{if(e.key==='Escape')closeAlert();if(e.key==='Tab'){const nodes=dialogRef.current?.querySelectorAll('button,textarea,[tabindex="0"]');if(!nodes?.length)return;const first=nodes[0],last=nodes[nodes.length-1];if(e.shiftKey&&(document.activeElement===first||document.activeElement===dialogRef.current)){e.preventDefault();last.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}}};document.addEventListener('keydown',handler);return()=>document.removeEventListener('keydown',handler)},[alert]);
 async function review(action){if(!reviewReason.trim())return;const run=epoch.current;setReviewBusy(true);try{await api('/reviews',{analysis_id:alert.analysis_id,alert_id:alert.id,action,reason:reviewReason.trim()});if(run===epoch.current){setReviewed(x=>({...x,[alert.analysis_id+alert.id]:action}));setNotice('검토 기록을 저장했습니다. 처방은 변경되지 않았습니다.');refreshAudit()}}catch(e){if(run===epoch.current)setError(e.message)}finally{setReviewBusy(false)}}
 async function sendFeedback(rating){const run=epoch.current;try{await api('/feedback',{analysis_id:alert.analysis_id,alert_id:alert.id,rating,comment:''});if(run===epoch.current)setNotice('피드백을 저장했습니다. 연구용 데이터로만 사용되며 모델을 바로 재학습하지 않습니다.')}catch(e){if(run===epoch.current)setError(e.message)}}
 const customList=customPatients.map(c=>({id:c.id,name:c.name,age:c.age,sex:c.sex,diagnosis:c.diagnosis,scenario:c.scenario||'직접 입력',risk:customResults[c.id]?.risk||{risk_level:'low'},custom:true}));
 const visible=[...patients,...customList].filter(p=>(p.name+p.id+p.diagnosis).toLowerCase().includes(query.toLowerCase()));
 const active=patient?.medications.filter(m=>m.status==='active')||[];
 const medInfo=id=>catalog.find(d=>d.id===id)||{name_ko:id,group_ko:''};
 const labs=(patient?.labs||[]).filter(l=>l.name===labName).map(l=>({...l,day:l.date.slice(5)}));
 const isCustom=customPatients.some(c=>c.id===selected);
 const danger=analysis?.alerts.filter(a=>a.severity==='danger').length||0,caution=analysis?.alerts.filter(a=>a.severity==='caution').length||0;
 return <div className="app-shell">
  <header className="topbar"><a className="brand" href="/" aria-label="SynexAgent 홈"><span className="brand-icon"><Activity size={24}/></span><span>Synex<span className="brand-light">Agent</span></span><span className="version">CLINICAL WORKSPACE</span></a><div className="top-meta"><span className="demo-label">DEMO · 가상 환자</span><span className="top-sep"/><span className="user-avatar">DR</span><span>의료진 검토 모드</span></div></header>
  <aside className="patient-sidebar"><div className="workspace-label">WORKSPACE <span>01</span></div><div className="sidebar-title"><h2>환자 목록</h2><span>{(patients.length+customPatients.length).toString().padStart(2,'0')}</span></div><label className="searchbox"><Search size={17}/><input aria-label="환자 검색" placeholder="환자명, ID 검색" value={query} onChange={e=>setQuery(e.target.value)}/></label><button className="new-patient-button" onClick={()=>setCustomOpen(true)}><UserPlus size={16}/> 새 환자 직접 입력</button>{patientsUnavailable&&<div className="fhir-lookup"><p className="muted small">FHIR 연동 모드에서는 전체 환자 목록을 조회할 수 없습니다 (병원 시스템의 승인된 검색 범위가 필요합니다). SMART 실행 시 전달된 환자 ID를 직접 입력하십시오.</p><label className="searchbox"><Search size={17}/><input aria-label="FHIR 환자 ID 조회" placeholder="환자 ID 입력 후 Enter" value={fhirLookup} onChange={e=>setFhirLookup(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&fhirLookup.trim()){setSelected(fhirLookup.trim());setFhirLookup('')}}}/></label></div>}<div className="list-caption">오늘의 데모 사례 <Users size={15}/></div><nav aria-label="환자 선택" className="patient-list">{visible.map(p=><div key={p.id} className={'patient-row '+(selected===p.id?'selected':'')}><button className="patient-row-btn" onClick={()=>setSelected(p.id)} aria-current={selected===p.id?'true':undefined}><div className="patient-row-top"><span className="patient-avatar">{p.name.slice(0,1)}</span><div><b>{p.name}</b><small>{p.age}세 · {p.sex==='female'?'여':'남'} · {p.id}</small>{p.custom&&<span className="custom-tag">직접 입력</span>}</div><ChevronRight size={17}/></div><div className="patient-row-bottom"><span>{p.scenario.split(' · ')[0]}</span><span className={'risk-dot '+(p.risk.risk_level==='high'?'red':'teal')}/></div></button>{p.custom&&<button className="patient-row-delete" aria-label={p.name+' 삭제'} onClick={()=>removeCustomPatient(p.id)}><Trash2 size={14}/></button>}</div>)}</nav>{!visible.length&&<p className="muted empty">검색 결과가 없습니다.</p>}<div className="sidebar-foot"><ShieldCheck size={20}/><b>의료진의 판단을 위한 보조</b><p>모든 데이터는 가상 사례입니다.<br/>진단·처방은 자동 실행되지 않습니다.</p><span>SynexAgent / MVP 1.0</span></div></aside>
  <main className="main-workspace">
   <div className="breadcrumb">Clinical workspace <ChevronRight size={13}/> 환자 분석 <span className="mono">{selected}</span></div>
   {error&&<div className="error-banner" role="alert"><TriangleAlert size={18}/><span>{error}</span><button onClick={()=>{setBoot(v=>v+1);setRevision(v=>v+1)}}>다시 시도</button></div>}
   <div className="page-heading"><div><div className="eyebrow">PATIENT OVERVIEW</div><h1>{patient?.name||'환자 정보 로딩'}<span>{patient?`${patient.age}세 / ${patient.sex==='female'?'여성':'남성'}`:''}</span></h1><p>{patient?.diagnosis||'기록을 불러오고 있습니다.'}</p></div><button className="outline-button" disabled={busy} onClick={()=>setRevision(v=>v+1)}><RotateCw size={15} className={busy?'spin':''}/> 다시 분석</button></div>
   <div className="patient-facts"><div><Pill size={17}/><span>현재 약물</span><b>{active.length}<small>종</small></b></div><div><HeartPulse size={17}/><span>기저질환</span><b>{patient?.conditions.length??'—'}<small>건</small></b></div><div><ShieldCheck size={17}/><span>알레르기</span><b className={patient?.allergies.length?'text-danger':''}>{patient?.allergies.length??'—'}<small>건</small></b></div><div><FlaskConical size={17}/><span>최근 검사</span><b className="date-value">{patient?.labs.at(-1)?.date.slice(5)||'정보 없음'}</b></div></div>
   {!isCustom&&<PatientClinicalHeader patient={patient} encounters={encounters}/>}
   <div className="tabbar" role="tablist" aria-label="환자 보기">{[['overview','분석 요약',BrainCircuit],['timeline','Timeline',Clock],['clinical-note','Clinical Note',ClipboardCheck],['orders','Orders',Pill],['results','Results',FlaskConical],['medication','Medication',Database],['anatomy','3D 해부학',Layers],['records','진료 기록',FileText],['audit','검토 이력',History]].map(([id,label,Icon])=><button role="tab" id={'tab-'+id} aria-selected={tab===id} aria-controls={'panel-'+id} key={id} className={tab===id?'active':''} onClick={()=>{setTab(id);if(id==='audit'&&!customRef.current.some(c=>c.id===selected))refreshAudit()}}><Icon size={16}/>{label}{id==='audit'&&<span>{audit.length}</span>}</button>)}</div>
   <section role="tabpanel" id={'panel-'+tab} aria-labelledby={'tab-'+tab}>
   {tab==='overview'&&<>
    <div className="analysis-grid"><section className="risk-card"><div className="card-label"><span>SYNEX RISK INDEX</span><BrainCircuit size={18}/></div><div className="score-line"><strong>{analysis?Math.round(analysis.risk.risk_probability*100):'—'}</strong><span>/100</span></div><div className="score-bottom"><Badge severity={analysis?.risk.risk_level==='high'?'danger':'info'}>{analysis?(analysis.risk.risk_level==='high'?'HIGH · 모델 고위험':'LOW · 모델 저위험'):'분석 중'}</Badge><span>v3 ONNX</span></div><div className="score-meter"><span style={{width:analysis?`${analysis.risk.risk_probability*100}%`:'0%'}}/></div><p>이 값은 모델 내부 신호를 0–100 척도로 재표현한 것이며,<br/>실제 부작용 발생 확률이나 보정(calibrated)된 임상 위험도가 아닙니다.<br/>임상 의사결정을 보조하기 위한 참고 신호입니다.</p></section>
    <section className="summary-card"><div className="section-head"><h2><BrainCircuit size={18}/> Agent 임상 요약</h2><span className="small-status">{busy?'분석 결과 수신 중':analysis?'분석 완료':'결과 없음'}</span></div>{analysis?<><p className="summary-text">{analysis.summary}</p><div className="summary-counts"><span><i className="signal danger"/>{danger} 위험</span><span><i className="signal caution"/>{caution} 주의</span><span><Check size={15}/> {analysis.steps.length} 단계 완료</span></div><div className="summary-note"><Info size={15}/><span>{analysis.missing.length?'정보 부족: '+analysis.missing.join(', '):'규칙 근거를 요약했습니다. 최종 판단은 의료진이 수행합니다.'}</span></div>{!!analysis.brief_facts?.length&&<div className="brief-facts">{analysis.brief_facts.map((f,i)=><button key={i} onClick={()=>setTab(f.nav==='overview'?'overview':f.nav)}>{f.text}<ChevronRight size={13}/></button>)}</div>}</>:<div className="skeleton-block"><span/><span/><span/></div>}</section></div>
    {!isCustom&&<section className="clinical-summary-card"><div className="section-head"><h2><FileText size={18}/> SynexAgent Clinical Summary</h2><span className="small-status">최근 {clinicalSummary?.window_months??6}개월</span></div>
     {!clinicalSummary?<p className="muted">요약을 불러오는 중…</p>:!clinicalSummary.sentences.length?<p className="muted">최근 기간 내 감지된 주요 변화가 없습니다.</p>:<>
      <p className="muted small">최근 주요 변화</p>
      <ul className="clinical-summary-list">{clinicalSummary.sentences.map((s,i)=><li key={i}><span>{s.text}</span>{!!s.source_events?.filter(Boolean).length&&<button className="text-button" onClick={()=>jumpToSource(s.source_events)}>관련 기록 보기<ChevronRight size={13}/></button>}</li>)}</ul>
     </>}
     <p className="clinical-summary-disclaimer"><Info size={14}/>{clinicalSummary?.disclaimer||'이 요약은 저장된 실제 데이터에서 결정론적 규칙으로 생성되며, 임상 판단을 대체하지 않습니다.'}</p>
    </section>}
    <section className="alerts-section"><div className="section-head"><h2>검토가 필요한 신호 <span className="count">{analysis?.alerts.length??'—'}</span></h2><span className="muted">위험도순 · 규칙 기반</span></div><div className="alert-list">{analysis?.alerts.map(a=><button className={'alert-row '+a.severity} key={a.id} onClick={()=>openAlert(a)}><span className="alert-icon">{a.severity==='danger'?<TriangleAlert size={20}/>:a.severity==='caution'?<Info size={20}/>:<Layers size={20}/>}</span><div className="alert-body"><div><b>{a.title}</b><Badge severity={a.severity}/>{reviewed[analysis.analysis_id+a.id]&&<span className="review-tag">검토 기록됨</span>}</div><p>{a.reason}</p></div><ChevronRight size={18}/></button>)}{analysis&&!analysis.alerts.length&&<div className="no-alert"><CircleCheck size={25}/><div><b>제공 규칙에서 경고를 찾지 못했습니다.</b><p>미등록 약물·용량·새로운 상호작용은 별도 검토가 필요합니다.</p></div></div>}{busy&&<div className="loading-note">환자별 위험 신호를 정리하고 있습니다.</div>}</div></section>
    <section className="simulation-card"><div className="section-head"><h2><Pill size={18}/> 처방 시뮬레이션</h2><span className="simulation-pill">가상 추가</span></div><p className="alt-info-tag">ALTERNATIVE INFORMATION FOR CLINICIAN REVIEW · Reference information only. Final treatment selection remains with the clinician.</p><p className="muted">추가할 약물을 선택해 현재 처방과 비교합니다.</p><form onSubmit={simulate} className="simulation-form"><DrugCombobox label="추가 약물" catalog={catalog} value={drug} onChange={d=>{setDrug(d);setSimulation(null)}} exclude={new Set(active.map(m=>m.drug_id))} disabled={simBusy||busy}/><button className="primary-button" disabled={!drug||simBusy||busy}>{simBusy?<RotateCw size={17} className="spin"/>:<Plus size={17}/>} {simBusy?'재분석 중':'위험 비교'}</button></form>{simulation&&<div className="simulation-result" aria-live="polite"><div className="comparison"><div><small>현재 RISK INDEX</small><b>{riskIndex(simulation.before.risk.risk_probability)}<small>/100</small></b></div><ArrowRight size={22}/><div><small>{simulation.drug.name_ko} 추가</small><b>{riskIndex(simulation.after.risk.risk_probability)}<small>/100</small></b></div><span className={'delta '+(simulation.delta_percentage_points>0?'text-danger':'')}>{simulation.delta_percentage_points>0?'+':''}{simulation.delta_percentage_points.toFixed(1)}p</span></div><p className="muted small">모델 신호 재표현값이며 실제 확률이 아닙니다.</p><p>새 신호 {simulation.new_alerts.length}건 · 원래 처방 유지</p>{simulation.new_alerts.map(a=><button className="sim-alert" key={a.id} onClick={()=>openAlert(a,simulation.after.analysis_id)}><Badge severity={a.severity}/><span>{a.title}</span><ChevronRight size={15}/></button>)}{!simulation.new_alerts.length&&<p className="muted">새로운 규칙 경고 없음. 안전한 처방임을 보증하지 않습니다.</p>}<button className="text-button" onClick={()=>setSimulation(null)}>비교 닫기</button></div>}</section>
    <section className="labs-card"><div className="section-head"><h2><FlaskConical size={18}/> 검사 수치 변화</h2><select aria-label="검사 항목" value={labName} onChange={e=>setLabName(e.target.value)}>{[...new Set(patient?.labs.map(l=>l.name)||[])].map(n=><option key={n}>{n}</option>)}</select></div><div className="lab-meta"><strong>{labs.at(-1)?.value??'—'}</strong><span>{labs.at(-1)?.unit} · {labs.at(-1)?.date}</span></div><div className="chart-wrap">{labs.length?<ResponsiveContainer width="100%" height={180}><LineChart data={labs} margin={{top:10,right:18,bottom:0,left:-20}}><CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e5eced"/><XAxis dataKey="day" axisLine={false} tickLine={false} tick={{fontSize:12,fill:'#697c82'}}/><YAxis domain={['auto','auto']} axisLine={false} tickLine={false} tick={{fontSize:12,fill:'#697c82'}}/><Tooltip formatter={v=>[v,labName]}/><Line type="linear" dataKey="value" stroke="#008a78" strokeWidth={2.5} dot={{r:4,fill:'#fff',strokeWidth:2}} activeDot={{r:6}}/></LineChart></ResponsiveContainer>:<p>검사 정보가 없습니다.</p>}</div><p className="chart-note">가상 검사 데이터 · 제공 참고범위 {labs.at(-1)?.low}–{labs.at(-1)?.high}. 검사 수치는 v3 모델의 직접 입력이 아닙니다.</p></section>
    <section className="gaps-card"><div className="section-head"><h2><TriangleAlert size={18}/> DATA GAPS</h2></div>{customPatients.some(c=>c.id===selected)?<p className="muted">직접 입력한 환자는 데이터 품질 평가를 제공하지 않습니다.</p>:!dataQuality?<p className="muted">평가 중…</p>:!dataQuality.gaps.length?<div className="no-alert"><CircleCheck size={20}/><div><b>현재 확인된 데이터 공백이 없습니다.</b><p>완전성 확인이지 임상적 정상 판정이 아닙니다.</p></div></div>:<ul className="gaps-list">{dataQuality.gaps.map((g,i)=><li key={i}><Badge severity={g.status==='STALE'?'caution':'danger'}>{g.status}</Badge><span>{g.message}</span></li>)}</ul>}</section>
   </>}
   {tab==='timeline'&&<TimelinePanel patient={patient} disabled={isCustom} highlightIds={timelineHighlight}/>}
   {tab==='clinical-note'&&<ClinicalNotePanel patientId={patient?.id} encounters={encounters} onStartEncounter={startEncounter} onVitalsChanged={()=>{refreshEncounters();refreshClinicalSummary()}} onDiagnosisChanged={()=>{refreshEncounters();refreshClinicalSummary();refreshAudit()}} disabled={isCustom}/>}
   {tab==='orders'&&<OrdersPanel catalog={catalog} encounters={encounters} onStartEncounter={startEncounter} onOrdersChanged={()=>{refreshEncounters();refreshAudit();refreshClinicalSummary()}} disabled={isCustom}/>}
   {tab==='results'&&<ResultsPanel patient={patient} disabled={isCustom}/>}
   {tab==='medication'&&<MedicationOrdersPanel patient={patient} catalog={catalog} disabled={isCustom}/>}
   {tab==='anatomy'&&<Suspense fallback={<p>Loading anatomical model…</p>}><AnatomyWorkspace key={selected} patient={patient} analysis={analysis} simulation={simulation} onOpenAlert={openAlert} focus={anatomyFocus} catalog={catalog}/></Suspense>}
   {tab==='records'&&<div className="records"><section className="white-card"><h2>현재 복용 약물</h2><div className="table-wrap"><table><thead><tr><th>약물</th><th>약물군</th><th>시작일</th><th>조제/리필</th></tr></thead><tbody>{active.map((m,i)=><tr key={i}><td><b>{medInfo(m.drug_id).name_ko}</b><small>{m.drug_id}</small></td><td>{medInfo(m.drug_id).group_ko}</td><td>{m.started||'정보 없음'}</td><td>{m.dispenses??'정보 없음'}</td></tr>)}</tbody></table></div></section><section className="white-card"><h2>알레르기 및 과거 약물 반응</h2>{patient?.allergies.length?patient.allergies.map((a,i)=><p key={i}><b>{a.substance}</b> · {a.severity}<br/>{a.reaction}</p>):<p>제공 기록에 알레르기 이력이 없습니다.</p>}<h2>기저질환</h2><p>{patient?.conditions.join(' · ')||'기록 없음'}</p><h2>진료 기록</h2>{patient?.history.map((h,i)=><p key={i}>{h}</p>)}</section><section className="white-card"><h2>모델 입력값</h2><p className="muted">정규화된 입력값이며, 중요도 또는 기여율이 아닙니다.</p>{analysis&&Object.entries(analysis.risk.features).map(([k,v])=><div className="feature-row" key={k}><span>{featureLabels[k]}</span><code>{k}</code><b>{v.toFixed(3)}</b></div>)}</section></div>}
   {tab==='audit'&&<section className="white-card">{customPatients.some(c=>c.id===selected)?<><h2>분석 및 의료진 검토 기록</h2><p className="muted">직접 입력한 환자는 서버 감사 기록을 저장하지 않습니다. 데모 환자 목록의 사례를 선택하면 감사 이력을 확인할 수 있습니다.</p></>:<><div className="section-head"><h2>분석 및 의료진 검토 기록</h2><button className="text-button" onClick={()=>refreshAudit()}><RotateCw size={15}/> 새로고침</button></div><p className="muted">서버에 저장된 최근 200건입니다. 현재 AUTH_MODE 설정에 따라 demo identity 또는 실제 인증된 사용자(역할 포함) 기준으로 감사 이벤트가 기록·표시됩니다.</p><div className="audit-list">{audit.map(a=><article key={a.id}><span className="audit-node"/><div><time>{new Date(a.timestamp).toLocaleString('ko-KR')}</time><b>{AUDIT_EVENT_LABELS[a.event]||a.event}</b>{a.role&&<span className="muted"> · {a.role}</span>}<p>{a.detail.title||a.detail.reason||a.detail.drug_id||a.detail.name||(a.detail.risk_probability!=null?`AI risk score ${fmt(a.detail.risk_probability)}%`:'')}</p></div></article>)}</div>{!audit.length&&<p>저장된 기록이 없습니다.</p>}</>}</section>}
   </section><footer className="workspace-footer">SYNEXAGENT <span>의료진 검토용 프로토타입 · 외부 임상 검증 전</span></footer>
  </main>
  <aside className="agent-panel"><div className="agent-panel-title"><span className="agent-mark"><BrainCircuit size={22}/></span><div><b>SynexAgent</b><small>Clinical copilot</small></div><span className={'connection '+(error?'offline':'')}/></div><div className="agent-state"><span className="eyebrow">ANALYSIS PIPELINE</span><h2>{error?'분석을 완료하지 못했습니다':busy?'환자 기록 분석':analysis?'분석이 완료되었습니다':'결과 대기'}</h2><p>{error?'연결을 확인하고 다시 분석하십시오.':busy?'서버 분석 결과를 불러옵니다.':'근거를 검토하고 판단을 기록하십시오.'}</p></div><div className="pipeline">{STEPS.map((name,i)=>{const s=steps.find(s=>s.name===name),Icon=stepIcons[i];return <div key={name} className={'pipeline-step '+(s?'done ':'')+(s?.warning?'warning ':'')+(!s&&i===steps.length&&busy?'current':'')}><span className="pipeline-icon">{s?<Check size={15}/>:<Icon size={16}/>}</span><div><b>{name}</b><small>{s?s.detail:'대기 중'}</small></div>{s?.warning&&<TriangleAlert size={14} className="text-warning"/>}</div>})}</div><div className="pipeline-caption"><Clock size={13}/>{analysis?`${analysis.duration_ms.toFixed(1)}ms 서버 처리 · 완료 단계 재생`:'분석 완료 단계가 순서대로 표시됩니다.'}</div>{analysis&&<div className="agent-findings"><div><span>DETECTED SIGNALS</span><b>{analysis.alerts.length.toString().padStart(2,'0')}</b></div><p><Badge severity="danger">{danger} 위험</Badge><Badge severity="caution">{caution} 주의</Badge></p></div>}<div className="checks-panel"><h3><ClipboardCheck size={17}/> 의료진 확인 사항</h3>{analysis?.next_checks.map((c,i)=><p key={i}><span>{String(i+1).padStart(2,'0')}</span>{c}</p>)}{busy&&<p>분석 후 확인 사항이 표시됩니다.</p>}</div><div className="agent-disclaimer"><Info size={16}/><p>LLM이 금기를 생성하지 않습니다. 제공 규칙과 모델 결과를 연결한 근거 기반 요약입니다.</p></div></aside>
  {alert&&<div className="drawer-backdrop" onClick={closeAlert}><section className="alert-drawer" role="dialog" aria-modal="true" aria-labelledby="alert-title" tabIndex={-1} ref={dialogRef} onClick={e=>e.stopPropagation()}><div className="drawer-top"><span>ALERT DETAIL</span><button aria-label="경고 상세 닫기" onClick={closeAlert}><X size={22}/></button></div><Badge severity={alert.severity}/><h2 id="alert-title">{alert.title}</h2><button className="outline-button" onClick={()=>showAnatomy(alert)}>3D에서 보기</button><h3>왜 감지되었는가</h3><p>{alert.reason}</p><h3>관련 약물</h3><div className="drug-tags">{alert.drugs.length?alert.drugs.map(d=><span key={d}>{medInfo(d).name_ko}</span>):'특정 약물에 국한되지 않은 환자 이력·누적 신호'}</div>
<h3>이 신호가 도움이 되었습니까?</h3><div className="feedback-row">{[['useful','유용함'],['not_useful','유용하지 않음'],['incorrect','부정확함'],['already_known','이미 알고 있음'],['needs_more_information','정보 부족']].map(([id,label])=><button key={id} className="outline-button" onClick={()=>sendFeedback(id)}>{label}</button>)}</div>
<h3>WHY THIS ALERT?</h3><ol className="why-chain"><li><b>Issue</b><span>{alert.drugs.length?alert.drugs.map(d=>medInfo(d).name_ko).join(' + '):alert.title}</span></li><li><b>Risk factor</b><span>{alert.reason}</span></li><li><b>Patient-specific factors</b><span>{[patient?.age!=null?`Age ${patient.age}`:null,alert.evidence?.lab?`${alert.evidence.lab.name} ${alert.evidence.lab.value}${alert.evidence.lab.unit||''} (${alert.evidence.lab.date})`:null,alert.evidence?.condition?`기저질환: ${alert.evidence.condition}`:null,...(alert.evidence?.allergies||[]).map(a=>`알레르기: ${a.substance} (${a.severity})`),...alert.drugs.filter(d=>active.some(m=>m.drug_id===d)).map(d=>`${medInfo(d).name_ko} 복용 중`),...[...new Set(alert.drugs.flatMap(d=>DRUG_RELATED_LABS[d]||[]))].map(labName=>{const l=[...(patient?.labs||[])].filter(x=>x.name===labName).sort((a,b)=>b.date.localeCompare(a.date))[0];return l?`${l.name} ${l.value}${l.unit} (${l.date})${(l.low!=null&&l.value<l.low)||(l.high!=null&&l.value>l.high)?' ⚠':''}`:null}).filter(Boolean)].filter(Boolean).join(' · ')||'환자 기록 · 누적 신호'}</span></li><li><b>Evidence source</b><span>{alert.source}{alert.rule_id?` · ${alert.rule_id}`:''}</span></li><li><b>Recommended action</b><span>{recommendedAction(alert)}</span></li></ol>
<h3>근거 및 모델 연결</h3><dl><dt>판단 방식</dt><dd>규칙 기반</dd><dt>근거 위치</dt><dd>{alert.source}</dd><dt>입력 반영</dt><dd>{alert.training_signal?'학습 규칙의 위험·주의 건수에 반영':'drug_conflict에는 추가하지 않는 별도 안전 신호'}</dd><dt>검증 상태</dt><dd>{alert.evidence_level||'프로토타입 규칙 · 임상 검증 필요'}</dd></dl>{Object.keys(alert.evidence).length>0&&<details><summary>환자 근거 데이터</summary><pre>{JSON.stringify(alert.evidence,null,2)}</pre></details>}<p className="drawer-note">개별 경고의 정확한 점수 기여율은 계산하지 않습니다. 추가 약물의 영향은 처방 시뮬레이션에서 비교할 수 있습니다.</p><h3>의료진 검토</h3><label htmlFor="reason">판단 근거 또는 확인 내용</label><textarea id="reason" value={reviewReason} maxLength={500} onChange={e=>setReviewReason(e.target.value)} placeholder="검토 내용 입력 (필수)"/><div className="review-buttons"><button className="primary-button" disabled={!reviewReason.trim()||reviewBusy} onClick={()=>review('reviewed')}><Check size={16}/> 확인</button><button className="outline-button" disabled={!reviewReason.trim()||reviewBusy} onClick={()=>review('deferred')}>보류</button><button className="outline-button" disabled={!reviewReason.trim()||reviewBusy} onClick={()=>review('dismissed')}>무시</button></div>{notice&&<p className="success-message" role="status">{notice}</p>}<p className="muted">검토 기록은 저장되며, 경고 자체나 처방을 삭제하지 않습니다.</p></section></div>}
  {customOpen&&<CustomPatientForm catalog={catalog} onClose={()=>setCustomOpen(false)} onSubmit={createCustomPatient}/>}
 </div>
}

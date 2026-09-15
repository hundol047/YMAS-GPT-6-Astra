import React,{lazy,Suspense,useState,useMemo,useEffect,useCallback,useRef} from 'react';
import {Maximize,Minimize} from 'lucide-react';
import AnatomyOrganList from './AnatomyOrganList';
import AnatomyControls from './AnatomyControls';
import AnatomyOrganDetail from './AnatomyOrganDetail';
import AnatomySlicePanel from './AnatomySlicePanel';
import AnatomyLegend from './AnatomyLegend';
import AnatomyConditionsPanel from './AnatomyConditionsPanel';
import AnatomyImagingPanel from './AnatomyImagingPanel';
import {DISCLAIMER,organs,targetsFor,severityFor,resolveSex,SEX_LABELS} from '../../data/anatomyMap';
import './anatomy.css';
import {AnatomyAssets,useAnatomyAssetStatus} from './AnatomyAssets';
const AnatomyScene=lazy(()=>import('./AnatomyScene'));

function AnatomyWorkspace({patient,analysis,simulation,onOpenAlert,focus,catalog}){
 const [useSimulation,setUseSimulation]=useState(!!simulation),[selected,setSelected]=useState(null),[hidden,setHidden]=useState({skeleton:true}),[checked,setChecked]=useState(new Set());
 const [mode,setMode]=useState('axial'),[position,setPosition]=useState(0),[clipping,setClipping]=useState(false),[view,setView]=useState({kind:'reset'}),[reduced,setReduced]=useState(false);
 const [bodyOpacity,setBodyOpacity]=useState(55),[activePreset,setActivePreset]=useState(null),[showLabels,setShowLabels]=useState(false);
 const [imagingOpen,setImagingOpen]=useState(false),[fullscreen,setFullscreen]=useState(false);
 const rootRef=useRef(null);
 const assetStatus=useAnatomyAssetStatus();
 const current=useSimulation&&simulation?simulation.after:analysis,data=current?.anatomy;
 const sex=resolveSex(patient?.sex);
 useEffect(()=>{setUseSimulation(!!simulation)},[simulation]);
 useEffect(()=>{const q=window.matchMedia('(prefers-reduced-motion: reduce)'),update=()=>setReduced(q.matches);update();q.addEventListener('change',update);return()=>q.removeEventListener('change',update)},[]);
 useEffect(()=>{const h=()=>setFullscreen(!!document.fullscreenElement);document.addEventListener('fullscreenchange',h);return()=>document.removeEventListener('fullscreenchange',h)},[]);
 const choose=useCallback(id=>{setSelected(id);setHidden(h=>({...h,[id]:false}));setView({kind:'focus',nonce:Date.now()})},[]);
 useEffect(()=>{
  if(focus&&focus.patientId===patient?.id){setUseSimulation(focus.simulated);choose(focus.organId);}
 },[focus,patient?.id,choose]);
 const count=useMemo(()=>organs.filter(o=>severityFor(targetsFor(data,o.group))!=='none').length,[data]);
 function applyPreset(id){
  setActivePreset(id);
  if(id==='skin'){setBodyOpacity(100);setHidden(h=>({...h,body:false}))}
  else if(id==='transparent'){setBodyOpacity(22);setHidden(h=>({...h,body:false}))}
  else if(id==='xray'){setBodyOpacity(12);setHidden(h=>({...h,body:false,skeleton:false}))}
  else if(id==='organsOnly'){setHidden(h=>({...h,body:true}))}
 }
 // Body opacity ↓ on focus so the highlighted organ isn't hidden behind the skin shell; never
 // invents an organ<->condition relationship -- organIds comes straight from the backend's fixed
 // anatomy_mapping.json linkage already present on `data`.
 function onFocusCondition(_condition,organIds){
  setActivePreset(null);
  setBodyOpacity(o=>o>40?25:o);
  choose(organIds[0]||'vascular');
 }
 function toggleFullscreen(){
  if(document.fullscreenElement)document.exitFullscreen();
  else rootRef.current?.requestFullscreen?.();
 }
 const activeMeds=patient?.medications.filter(m=>m.status==='active').length??0;
 if(!patient||!analysis)return <div className="an-loading">환자 분석 결과를 기다리고 있습니다…</div>;
 return <div className="an-workspace" ref={rootRef}>
 <header className="an-heading">
  <div><small>CLINICAL RELEVANCE MAP</small><h2>3D 해부학 <span>3D ANATOMY</span></h2></div>
  <div className="an-heading-right"><span>{count}개 레이어 연결</span><button className="an-fullscreen" aria-label={fullscreen?'전체화면 종료':'전체화면'} onClick={toggleFullscreen}>{fullscreen?<Minimize size={15}/>:<Maximize size={15}/>}</button></div>
 </header>
 <section className="an-twin-header">
  <span className="an-twin-tag">PATIENT DIGITAL TWIN</span>
  <b>{patient.name}</b><span>{patient.age}세 · {sex?SEX_LABELS[sex]:SEX_LABELS.unspecified}</span>
  <span>Conditions: {patient.conditions.length}</span>
  <span>Active medications: {activeMeds}</span>
  <span>Imaging: {imagingOpen?'Demo imaging open':'No imaging'}</span>
  <span>Clinical signals: {current?.alerts?.length??0}</span>
 </section>
 {!sex&&<p className="an-sex-warning" role="status">Sex-specific anatomy unavailable · 환자 성별 정보가 없거나 지원되지 않아 중립 참고 모델을 표시합니다.</p>}
 {assetStatus==='fallback'&&<p className="an-sex-warning" role="status">정밀 인체 모델을 불러오지 못해 절차적 참고 모델로 대체했습니다.</p>}
 <p className="an-disclaimer">{DISCLAIMER}</p>
 {simulation&&<div className="an-simulation"><label><input type="checkbox" checked={useSimulation} onChange={e=>setUseSimulation(e.target.checked)}/> 시뮬레이션 결과 표시 · {simulation.drug.name_ko} 가상 추가</label><span>실제 처방 유지</span></div>}
 {!data&&<p role="status">장기 연결 결과가 없습니다. 업데이트된 백엔드로 다시 분석하십시오.</p>}
 <div className="an-layout">
  <AnatomyOrganList {...{selected,choose,hidden,setHidden,data,checked,setChecked,setView}}/>
  <div className="an-center">
   <div className="an-viewport"><div className="an-viewport-title">01 / 3D ANATOMY <span>PROCEDURAL REFERENCE{sex?` · ${SEX_LABELS[sex].toUpperCase()}`:''}</span></div>
    <Suspense fallback={<div className="an-loading">Loading anatomical model…</div>}>
     <AnatomyScene {...{selected,choose,hidden,data,mode,position,clipping,view,reduced,sex,bodyOpacity,showLabels,demoImagingOpen:imagingOpen}}/>
    </Suspense>
    <div className="an-help">드래그 회전 · 휠 확대 · 우클릭 이동<br/>A 전방 / P 후방 · S 상방 / I 하방</div>
   </div>
   <AnatomyControls {...{mode,setMode,position,setPosition,clipping,setClipping,setView,bodyOpacity,setBodyOpacity:v=>{setBodyOpacity(v);setActivePreset(null)},applyPreset,activePreset,showLabels,setShowLabels}}/>
   <AnatomyLegend/>
   {!imagingOpen
    ?<p className="an-imaging-empty">No patient imaging available. <button className="outline-button" onClick={()=>setImagingOpen(true)}>OPEN DEMO IMAGING</button></p>
    :<AnatomyImagingPanel hidden={hidden} data={data} onSyncScene={(m,v)=>{setMode(m);setPosition(v);setClipping(true)}} onClose={()=>setImagingOpen(false)}/>}
  </div>
  <aside className="an-detail">
   <AnatomyConditionsPanel patient={patient} data={data} onFocusCondition={onFocusCondition}/>
   <AnatomySlicePanel {...{mode,position,selected,choose,hidden,data}}/>
   <AnatomyOrganDetail {...{selected,data,onOpenAlert}} analysis={current} focusAlert={focus?.alertId} patient={patient} catalog={catalog} demoImagingOpen={imagingOpen} onOpenImaging={()=>setImagingOpen(true)}/>
  </aside>
 </div>
 <footer className="an-bottom">가상 환자 · 절차적 참고 모델 · CT / MRI 미연결 · 병변 위치 추정 없음</footer>
 </div>;
}

export default function AnatomyWithAssets(props){
 const sex=resolveSex(props.patient?.sex);
 return <AnatomyAssets sex={sex}><AnatomyWorkspace {...props}/></AnatomyAssets>;
}

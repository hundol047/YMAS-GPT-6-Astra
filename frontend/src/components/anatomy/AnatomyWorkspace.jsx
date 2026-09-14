import React,{lazy,Suspense,useState,useMemo,useEffect,useCallback} from 'react';
import AnatomyOrganList from './AnatomyOrganList';
import AnatomyControls from './AnatomyControls';
import AnatomyRiskPanel from './AnatomyRiskPanel';
import AnatomySlicePanel from './AnatomySlicePanel';
import AnatomyLegend from './AnatomyLegend';
import {DISCLAIMER,organs,targetsFor,severityFor} from '../../data/anatomyMap';
import './anatomy.css';
import {AnatomyAssets} from './AnatomyAssets';
const AnatomyScene=lazy(()=>import('./AnatomyScene'));
function AnatomyWorkspace({patient,analysis,simulation,onOpenAlert,focus}){
 const [useSimulation,setUseSimulation]=useState(!!simulation),[selected,setSelected]=useState(null),[hidden,setHidden]=useState({}),[mode,setMode]=useState('axial'),[position,setPosition]=useState(0),[clipping,setClipping]=useState(false),[view,setView]=useState({kind:'reset'}),[reduced,setReduced]=useState(false);
 const current=useSimulation&&simulation?simulation.after:analysis,data=current?.anatomy;
 useEffect(()=>{setUseSimulation(!!simulation)},[simulation]);
 useEffect(()=>{const q=window.matchMedia('(prefers-reduced-motion: reduce)'),update=()=>setReduced(q.matches);update();q.addEventListener('change',update);return()=>q.removeEventListener('change',update)},[]);
 const choose=useCallback(id=>{setSelected(id);setHidden(h=>({...h,[id]:false}));setView({kind:'focus',nonce:Date.now()})},[]);
 useEffect(()=>{
  if(focus?.patientId===patient?.id){setUseSimulation(focus.simulated);choose(focus.organId);}
 },[focus,patient?.id,choose]);
 const count=useMemo(()=>organs.filter(o=>severityFor(targetsFor(data,o.group))!=='none').length,[data]);
 if(!patient||!analysis)return <div className="an-loading">환자 분석 결과를 기다리고 있습니다…</div>;
 return <div className="an-workspace"><header className="an-heading"><div><small>CLINICAL RELEVANCE MAP</small><h2>3D 해부학 <span>3D ANATOMY</span></h2></div><span>{count}개 레이어 연결</span></header>
 <p className="an-disclaimer">{DISCLAIMER}</p>
 {simulation&&<div className="an-simulation"><label><input type="checkbox" checked={useSimulation} onChange={e=>setUseSimulation(e.target.checked)}/> 시뮬레이션 결과 표시 · {simulation.drug.name_ko} 가상 추가</label><span>실제 처방 유지</span></div>}
 {!data&&<p role="status">장기 연결 결과가 없습니다. 업데이트된 백엔드로 다시 분석하십시오.</p>}
 <div className="an-layout"><AnatomyOrganList {...{selected,choose,hidden,setHidden,data}}/><div className="an-center"><div className="an-viewport"><div className="an-viewport-title">01 / 3D ANATOMY <span>PROCEDURAL REFERENCE</span></div><Suspense fallback={<div className="an-loading">Loading anatomical model…</div>}><AnatomyScene {...{selected,choose,hidden,data,mode,position,clipping,view,reduced}}/></Suspense><div className="an-help">드래그 회전 · 휠 확대 · 우클릭 이동<br/>A 전방 / P 후방 · S 상방 / I 하방</div></div><AnatomyControls {...{mode,setMode,position,setPosition,clipping,setClipping,setView}}/><AnatomyLegend/></div><aside className="an-detail"><AnatomySlicePanel {...{mode,position,selected,choose,hidden,data}}/><AnatomyRiskPanel {...{selected,data,onOpenAlert}} analysis={current} focusAlert={focus?.alertId}/></aside></div><footer className="an-bottom">가상 환자 · 절차적 참고 모델 · CT / MRI 미연결 · 병변 위치 추정 없음</footer></div>;
}

export default function AnatomyWithAssets(props){return <AnatomyAssets><AnatomyWorkspace {...props}/></AnatomyAssets>}

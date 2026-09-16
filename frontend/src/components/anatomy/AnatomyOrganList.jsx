import React from 'react';
import {Eye,EyeOff,Focus} from 'lucide-react';
import {organs,pseudoLayers,colors,labels,targetsFor,severityFor,primaryTargetFor} from '../../data/anatomyMap';

const ALL_IDS=[...pseudoLayers.map(p=>p.id),...organs.map(o=>o.id)];

// Layer visibility never touches patient data or the underlying anatomy objects -- every action
// here (Eye, Isolate, Show/Hide All, Show Selected, Reset) only changes the `hidden` map that
// AnatomyModel reads to decide what to render this frame.
export default function AnatomyOrganList({selected,choose,hidden,setHidden,data,checked,setChecked,setView}){
 const rows=[...pseudoLayers.map(p=>({...p,pseudo:true})),...organs];
 const visible=ALL_IDS.filter(id=>!hidden[id]);
 const isolatedId=visible.length===1?visible[0]:null;
 function toggleEye(id){setHidden(h=>({...h,[id]:!h[id]}))}
 function isolate(id){
  if(isolatedId===id){setHidden({});return}
  setHidden(Object.fromEntries(ALL_IDS.map(x=>[x,x!==id])));
 }
 function toggleCheck(id){setChecked(c=>{const n=new Set(c);n.has(id)?n.delete(id):n.add(id);return n})}
 function showAll(){setHidden({})}
 function hideAll(){setHidden(Object.fromEntries(ALL_IDS.map(id=>[id,true])))}
 function showSelected(){if(!checked.size)return;setHidden(Object.fromEntries(ALL_IDS.map(id=>[id,!checked.has(id)])))}
 function reset(){setHidden({});setChecked(new Set());setView?.({kind:'reset',nonce:Date.now()})}
 return <aside className="an-organ-list">
 <h3>ANATOMY <span>{rows.length} LAYERS</span></h3>
 <div className="an-layer-toolbar">
  <button onClick={showAll}>SHOW ALL</button>
  <button onClick={hideAll}>HIDE ALL</button>
  <button onClick={showSelected} disabled={!checked.size}>SHOW SELECTED</button>
  <button onClick={reset}>RESET VIEW</button>
 </div>
 {rows.map(o=>{
  const targets=o.pseudo?[]:targetsFor(data,o.group);
  const severity=o.pseudo?'none':severityFor(targets);
  const primary=primaryTargetFor(targets);
  return <div key={o.id} className={'an-organ '+(selected===o.id?'active':'')+(o.pseudo?' an-organ-pseudo':'')}>
   <input className="an-check" type="checkbox" aria-label={o.ko+' 선택'} checked={checked.has(o.id)} onChange={()=>toggleCheck(o.id)}/>
   <button className="an-eye" aria-label={o.ko+(hidden[o.id]?' 표시':' 숨기기')} aria-pressed={!hidden[o.id]} onClick={()=>toggleEye(o.id)}>{hidden[o.id]?<EyeOff size={15}/>:<Eye size={15}/>}</button>
   <button className="an-isolate" aria-label={o.ko+(isolatedId===o.id?' 단독 보기 해제':' 단독 보기')} aria-pressed={isolatedId===o.id} onClick={()=>isolate(o.id)}><Focus size={14}/></button>
   {o.pseudo
    ?<span className="an-organ-name"><b>{o.ko}</b><span>{o.en}</span></span>
    :<button className="an-select" aria-pressed={selected===o.id} onClick={()=>choose(o.id)}><b>{o.ko}</b><span>{o.en}</span><small style={{color:colors[severity]}}>{primary?primary.reason:labels[severity]}</small></button>}
  </div>;
 })}
 <p>좌·우는 환자 기준입니다. Body/Skeleton은 3D 실루엣 표시 여부입니다.</p>
 </aside>;
}

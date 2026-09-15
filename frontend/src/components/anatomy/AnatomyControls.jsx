import React from 'react';
export default function AnatomyControls({mode,setMode,position,setPosition,clipping,setClipping,setView,bodyOpacity,setBodyOpacity,applyPreset,activePreset,showLabels,setShowLabels}){
 return <div className="an-controls">
 <div className="an-control-row"><div className="an-segments">{['axial','coronal','sagittal'].map(m=><button key={m} aria-pressed={mode===m} onClick={()=>{setMode(m);setPosition(0)}}>{m.toUpperCase()}</button>)}</div><label><input type="checkbox" checked={clipping} onChange={e=>setClipping(e.target.checked)}/> 실제 메시 절단</label></div>
 <label className="an-slider">단면 위치 <output>{position}</output><input aria-label="단면 위치" type="range" min="-100" max="100" value={position} onChange={e=>setPosition(Number(e.target.value))}/><small>상대 좌표</small></label>
 <div className="an-camera">{['reset','front','back','left','right','top'].map(kind=><button key={kind} onClick={()=>setView({kind,nonce:Date.now()})}>{kind.toUpperCase()}</button>)}</div>
 <div className="an-opacity-block">
  <label className="an-slider an-opacity-slider">BODY OPACITY <output>{bodyOpacity}%</output><input aria-label="신체 불투명도" type="range" min="0" max="100" value={bodyOpacity} onChange={e=>{setBodyOpacity(Number(e.target.value));applyPreset(null)}}/></label>
  <div className="an-presets" role="group" aria-label="신체 표시 프리셋">
   {[['skin','Skin'],['transparent','Transparent'],['xray','X-Ray'],['organsOnly','Organs Only']].map(([id,label])=><button key={id} aria-pressed={activePreset===id} onClick={()=>applyPreset(id)}>{label}</button>)}
  </div>
  <label className="an-label-toggle"><input type="checkbox" checked={showLabels} onChange={e=>setShowLabels(e.target.checked)}/> Labels ON/OFF</label>
 </div>
 </div>;
}

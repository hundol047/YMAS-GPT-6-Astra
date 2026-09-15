import React,{useMemo,useState} from 'react';
import {X} from 'lucide-react';
import {sliceValue,colors,severityFor,targetsFor} from '../../data/anatomyMap';
import {crossSectionPaths,modelToSlider,AXIS_TO_MODE} from './geometry';
import {useAnatomyAssets} from './AnatomyAssets';

const VB={axial:{w:300,h:230,y0:0,cy:115},coronal:{w:300,h:340,y0:-50,cy:190},sagittal:{w:300,h:340,y0:-50,cy:190}};
const AXES={axial:[0,2],coronal:[0,1],sagittal:[2,1]};

// One axial/coronal/sagittal pane of the DEMO imaging viewer. Crosshair position and the slice
// plane are always derived from the SAME reference-mesh cross-section engine the single-pane
// AnatomyScene clipping uses (geometry.crossSectionPaths / modelToSlider) -- there is no DICOM or
// NIfTI reader here, and this file must never synthesize a lesion.
function Pane({mode,positions,setPositions,hidden,data,onSetActive}){
 const assets=useAnatomyAssets();
 const axes=AXES[mode],vb=VB[mode];
 const value=positions[mode];
 const paths=useMemo(()=>crossSectionPaths(mode,value,assets),[mode,value,assets]);
 const crossX=150+sliceValue(AXIS_TO_MODE[axes[0]],positions[AXIS_TO_MODE[axes[0]]])*54;
 const crossY=vb.cy-sliceValue(AXIS_TO_MODE[axes[1]],positions[AXIS_TO_MODE[axes[1]]])*54;
 function handleClick(e){
  const rect=e.currentTarget.getBoundingClientRect();
  const px=(e.clientX-rect.left)/rect.width*vb.w;
  const py=vb.y0+(e.clientY-rect.top)/rect.height*vb.h;
  const mx=(px-150)/54,my=(vb.cy-py)/54;
  const next={...positions,[AXIS_TO_MODE[axes[0]]]:modelToSlider(axes[0],mx),[AXIS_TO_MODE[axes[1]]]:modelToSlider(axes[1],my)};
  setPositions(next);
  onSetActive(mode,positions[mode]);
 }
 function handleSlider(e){
  const v=Number(e.target.value);
  setPositions({...positions,[mode]:v});
  onSetActive(mode,v);
 }
 return <div className="an-imaging-pane">
  <div className="an-imaging-pane-head"><span>{mode.toUpperCase()}</span></div>
  <svg viewBox={`0 ${vb.y0} ${vb.w} ${vb.h}`} onClick={handleClick} role="img" aria-label={mode+' 데모 참고 단면, 클릭하여 교차선 이동'}>
   <rect x="0" y={vb.y0} width={vb.w} height={vb.h} fill="#08131b"/>
   {paths.filter(x=>!hidden[x.organ.id]&&x.path).map(({organ:o,path})=><path key={o.id} d={path} fill="none" stroke={colors[severityFor(targetsFor(data,o.group))]||o.color} strokeWidth={1.3}/>)}
   <line x1={crossX} y1={vb.y0} x2={crossX} y2={vb.y0+vb.h} stroke="#8ee2d6" strokeWidth="1" strokeDasharray="4 3"/>
   <line x1="0" y1={crossY} x2={vb.w} y2={crossY} stroke="#8ee2d6" strokeWidth="1" strokeDasharray="4 3"/>
  </svg>
  <input aria-label={mode+' 데모 슬라이스 위치'} type="range" min="-100" max="100" value={value} onChange={handleSlider}/>
 </div>;
}

export default function AnatomyImagingPanel({hidden,data,onSyncScene,onClose}){
 const [positions,setPositions]=useState({axial:0,coronal:0,sagittal:0});
 return <section className="an-imaging-panel">
 <div className="an-imaging-head">
  <div><h3>IMAGING STUDIES</h3><span className="an-demo-tag">DEMO IMAGING · REFERENCE ANATOMY — NOT PATIENT-DERIVED IMAGING</span></div>
  <button className="text-button" onClick={onClose}><X size={15}/> 닫기</button>
 </div>
 <p className="an-note">이 뷰는 실제 DICOM/NIfTI를 읽지 않습니다. 3D 모델과 동일한 참고 메시의 단면이며, 슬라이더를 움직이면 위의 3D 모델 절단면도 함께 이동합니다. 한 화면을 클릭하면 다른 두 화면의 교차선이 그 위치로 이동합니다.</p>
 <div className="an-imaging-grid">
  {['axial','coronal','sagittal'].map(m=><Pane key={m} mode={m} positions={positions} setPositions={setPositions} hidden={hidden} data={data} onSetActive={onSyncScene}/>)}
 </div>
 <section className="an-segmentation">
  <h4>SEGMENTATION</h4>
  <p className="an-empty">이 데모 영상에는 실제 segmentation 데이터가 없습니다. 합성 병변(예: 종양)을 생성하지 않습니다. 실제 segmentation 결과가 제공되면 이 자리에 개별 ON/OFF 가능한 항목으로 표시됩니다.</p>
 </section>
 </section>;
}

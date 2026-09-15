import React,{useMemo} from 'react';
import {colors,severityFor,targetsFor} from '../../data/anatomyMap';
import {crossSectionPaths} from './geometry';
import {useAnatomyAssets} from './AnatomyAssets';
// Intersect the SAME procedural surface triangles with the 3D slice plane.
// This is a surface reference, never generated CT pixels or patient imaging.
export default function AnatomySlicePanel({mode,position,selected,choose,hidden,data}){
 const assets=useAnatomyAssets();
 const paths=useMemo(()=>crossSectionPaths(mode,position,assets),[mode,position,assets]);
 return <section className="an-reference"><h3>ANATOMICAL REFERENCE <span>{mode.toUpperCase()}</span></h3><svg viewBox={mode==='axial'?'0 0 300 230':'0 -50 300 340'} role="img" aria-label="3D 모델과 동기화된 참고 단면">
 <path d="M150 -50V290M15 115H285" stroke="#254351" strokeDasharray="3 5"/>
 {paths.filter(x=>!hidden[x.organ.id]&&x.path).map(({organ:o,path})=><path key={o.id} d={path} fill="none" stroke={selected===o.id?'#edffff':colors[severityFor(targetsFor(data,o.group))]||o.color} strokeWidth={selected===o.id?2.3:1.5} onClick={()=>choose(o.id)} style={{cursor:'pointer'}}/>)}
 <text x="9" y="108" fill="#8ba9ad" fontSize="11">{mode==='sagittal'?'P':'R'}</text><text x="280" y="108" fill="#8ba9ad" fontSize="11">{mode==='sagittal'?'A':'L'}</text>
 </svg><p>Reference anatomy · Not patient imaging</p><small>참고 메시 단면 · 위치 {position} / 모델 상대 좌표</small></section>;
}

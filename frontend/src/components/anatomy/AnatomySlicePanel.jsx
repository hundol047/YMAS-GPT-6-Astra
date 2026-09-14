import React,{useMemo} from 'react';
import {organs,colors,severityFor,targetsFor,sliceAxes,sliceValue} from '../../data/anatomyMap';
import {makeGeometry} from './geometry';
import {useAnatomyAssets} from './AnatomyAssets';
// Intersect the SAME procedural surface triangles with the 3D slice plane.
// This is a surface reference, never generated CT pixels or patient imaging.
export default function AnatomySlicePanel({mode,position,selected,choose,hidden,data}){
 const assets=useAnatomyAssets();
 const paths=useMemo(()=>{
  const axis=sliceAxes[mode],axes=mode==='axial'?[0,2]:mode==='coronal'?[0,1]:[2,1],value=sliceValue(mode,position);
  return organs.map(o=>{
   const g=assets[o.id]?.clone()||makeGeometry(o),pos=g.attributes.position,indices=g.index.array,segments=[];
   for(let i=0;i<indices.length;i+=3){
    const vertices=[0,1,2].map(j=>[0,1,2].map(k=>pos.array[indices[i+j]*3+k]*o.s[k]+o.p[k]));
    const hits=[];
    for(let j=0;j<3;j++){const a=vertices[j],b=vertices[(j+1)%3];if((a[axis]<value)===(b[axis]<value))continue;const t=(value-a[axis])/(b[axis]-a[axis]);hits.push(a.map((v,k)=>v+t*(b[k]-v)));}
    if(hits.length===2){const point=v=>`${150+v[axes[0]]*54},${(mode==='axial'?115:190)-v[axes[1]]*54}`;segments.push(`M${point(hits[0])}L${point(hits[1])}`);}
   }
   g.dispose();return {organ:o,path:segments.join(' ')};
  });
 },[mode,position,assets]);
 return <section className="an-reference"><h3>ANATOMICAL REFERENCE <span>{mode.toUpperCase()}</span></h3><svg viewBox={mode==='axial'?'0 0 300 230':'0 -50 300 340'} role="img" aria-label="3D 모델과 동기화된 참고 단면">
 <path d="M150 -50V290M15 115H285" stroke="#254351" strokeDasharray="3 5"/>
 {paths.filter(x=>!hidden[x.organ.id]&&x.path).map(({organ:o,path})=><path key={o.id} d={path} fill="none" stroke={selected===o.id?'#edffff':colors[severityFor(targetsFor(data,o.group))]||o.color} strokeWidth={selected===o.id?2.3:1.5} onClick={()=>choose(o.id)} style={{cursor:'pointer'}}/>)}
 <text x="9" y="108" fill="#8ba9ad" fontSize="11">{mode==='sagittal'?'P':'R'}</text><text x="280" y="108" fill="#8ba9ad" fontSize="11">{mode==='sagittal'?'A':'L'}</text>
 </svg><p>Reference anatomy · Not patient imaging</p><small>참고 메시 단면 · 위치 {position} / 모델 상대 좌표</small></section>;
}

import React,{memo,useMemo,useRef} from 'react';
import {useFrame} from '@react-three/fiber';
import {DoubleSide} from 'three';
import {makeGeometry} from './geometry';
import {useAnatomyAssets} from './AnatomyAssets';
import {Line,Html} from '@react-three/drei';
import {organs,colors,labels,targetsFor,severityFor} from '../../data/anatomyMap';

// Original shaped surfaces: deliberately a reference model, not segmentation.
const Organ=memo(function Organ({organ,selected,choose,severity,planes,reduced,dim}){
 const assets=useAnatomyAssets();
 const geometry=useMemo(()=>assets[organ.id]?.clone()||makeGeometry(organ),[organ,assets]),mat=useRef();
 React.useEffect(()=>()=>geometry.dispose(),[geometry]);
 const color=severity==='none'?organ.color:colors[severity];
 useFrame(({clock})=>{if(mat.current)mat.current.emissiveIntensity=severity==='danger'&&!reduced? .22+.12*Math.sin(clock.elapsedTime*2):severity==='none'?.02:.18;});
 return <group position={organ.p}>
 <mesh name={organ.id} scale={organ.s} geometry={geometry} onClick={e=>{e.stopPropagation();choose(organ.id)}} onDoubleClick={e=>{e.stopPropagation();choose(organ.id)}}>
 <meshStandardMaterial ref={mat} color={color} emissive={color} roughness={.63} transparent opacity={selected?.94:dim?.2:.46} depthWrite={selected} side={DoubleSide} clippingPlanes={planes}/>
 </mesh>
 {(selected||severity==='caution')&&<mesh scale={organ.s.map(v=>v*1.028)} geometry={geometry} raycast={()=>null}><meshBasicMaterial color={selected?'#a8f9ed':colors.caution} transparent opacity={.17} wireframe clippingPlanes={planes}/></mesh>}
 {(selected||severity==='danger')&&<><Line points={[[0,0,0],[.55,.3,.2],[.95,.3,.2]]} color={color} lineWidth={1}/><Html position={[.96,.3,.2]} style={{pointerEvents:'none'}}><div className="an-marker"><b>{organ.en}</b><span>{organ.ko} · {labels[severity]}</span></div></Html></>}
 </group>;
});
export default function AnatomyModel({selected,choose,hidden,data,planes,reduced}){
 return <group>
 <mesh position={[0,.53,-.1]} scale={[1.38,2.36,.7]} raycast={()=>null}><sphereGeometry args={[1,40,32]}/><meshPhysicalMaterial color="#8bc9d0" transparent opacity={.08} roughness={.3} depthWrite={false} clippingPlanes={planes}/></mesh>
 <mesh position={[0,2.92,-.15]} raycast={()=>null}><cylinderGeometry args={[.24,.32,.7,24]}/><meshStandardMaterial color="#a5c3c6" transparent opacity={.12} depthWrite={false} clippingPlanes={planes}/></mesh>
 {organs.filter(o=>!hidden[o.id]).map(o=><Organ key={o.id} organ={o} selected={selected===o.id} dim={!!selected&&selected!==o.id} choose={choose} severity={severityFor(targetsFor(data,o.group))} planes={planes} reduced={reduced}/>)}
 {!hidden.spine&&Array.from({length:18},(_,i)=><mesh key={i} position={[0,-1.49+i*.218,-.56]} raycast={()=>null}><cylinderGeometry args={[.2,.19,.15,12]}/><meshStandardMaterial color="#c2ced0" transparent opacity={selected==='spine'?.9:.25} clippingPlanes={planes}/></mesh>)}
 {!hidden.vascular&&[-1,1].map(side=><Line key={side} points={[[0,-.25,-.1],[side*.3,-.3,-.15],[side*.6,-.36,-.22]]} color={colors[severityFor(targetsFor(data,'systemic'))]} lineWidth={3}/>)}
 </group>;
}

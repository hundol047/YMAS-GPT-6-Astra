import React,{memo,useMemo,useRef,useState} from 'react';
import {useFrame} from '@react-three/fiber';
import {DoubleSide} from 'three';
import {makeGeometry,buildTorsoLathe} from './geometry';
import {useAnatomyAssets} from './AnatomyAssets';
import {useAnatomyExtras} from './AnatomyExtrasAssets';
import {Line,Html} from '@react-three/drei';
import {organs,colors,labels,targetsFor,severityFor,BODY_PROFILES,extrasTransform} from '../../data/anatomyMap';

// Original shaped surfaces: deliberately a reference model, not segmentation.
const Organ=memo(function Organ({organ,selected,choose,severity,targets,planes,reduced,dim,showLabels,onHover,demoImagingOpen}){
 const assets=useAnatomyAssets();
 const geometry=useMemo(()=>assets[organ.id]?.clone()||makeGeometry(organ),[organ,assets]),mat=useRef();
 const [hovered,setHovered]=useState(false);
 React.useEffect(()=>()=>geometry.dispose(),[geometry]);
 const color=severity==='none'?organ.color:colors[severity];
 const primaryMarker=selected||severity==='danger';
 useFrame(({clock})=>{if(mat.current)mat.current.emissiveIntensity=severity==='danger'&&!reduced? .22+.12*Math.sin(clock.elapsedTime*2):severity==='none'?.02:.18;});
 const latestLab=useMemo(()=>{
  const labs=(targets||[]).flatMap(t=>t.sources.filter(s=>s.type==='lab'));
  return [...labs].sort((a,b)=>(a.date||'').localeCompare(b.date||'')).at(-1);
 },[targets]);
 return <group position={organ.p}>
 <mesh name={organ.id} scale={organ.s} geometry={geometry}
  onClick={e=>{e.stopPropagation();choose(organ.id)}}
  onDoubleClick={e=>{e.stopPropagation();choose(organ.id)}}
  onPointerOver={e=>{e.stopPropagation();setHovered(true);onHover?.(organ.id)}}
  onPointerOut={e=>{setHovered(false);onHover?.(null)}}>
 <meshStandardMaterial ref={mat} color={color} emissive={color} roughness={.63} transparent opacity={selected?.94:dim?.2:.46} depthWrite={selected} side={DoubleSide} clippingPlanes={planes}/>
 </mesh>
 {(selected||hovered)&&<mesh scale={organ.s.map(v=>v*1.05)} geometry={geometry} raycast={()=>null}><meshBasicMaterial color={selected?'#a8f9ed':'#eaf6ff'} transparent opacity={selected?.2:.15} wireframe clippingPlanes={planes}/></mesh>}
 {(!selected&&severity==='caution')&&<mesh scale={organ.s.map(v=>v*1.028)} geometry={geometry} raycast={()=>null}><meshBasicMaterial color={colors.caution} transparent opacity={.17} wireframe clippingPlanes={planes}/></mesh>}
 {primaryMarker&&<><Line points={[[0,0,0],[.55,.3,.2],[.95,.3,.2]]} color={color} lineWidth={1}/><Html position={[.96,.3,.2]} style={{pointerEvents:'none'}} distanceFactor={9}><div className="an-marker"><b>{organ.en}</b><span>{organ.ko} · {labels[severity]}</span></div></Html></>}
 {!primaryMarker&&hovered&&<Html position={[0,organ.s[1]*1.2+.12,0]} style={{pointerEvents:'none'}} distanceFactor={9}><div className="an-tooltip"><b>{organ.ko}</b><small>{organ.en}</small><span>Clinical signals: {(targets||[]).length}</span>{latestLab&&<span>Latest related lab: {latestLab.name}</span>}<span>Imaging: {demoImagingOpen?'데모 참고 영상':'참고 영상 없음'}</span></div></Html>}
 {!primaryMarker&&!hovered&&showLabels&&<Html position={[0,organ.s[1]*1.15+.08,0]} style={{pointerEvents:'none'}} distanceFactor={9}><div className="an-label">{organ.ko}</div></Html>}
 </group>;
});

// Translucent humanoid silhouette: a sex-aware body-shaped shell (head/neck/torso/limbs) that
// holds the organ meshes in place. The torso is a single continuous lathed surface through
// anatomyMap.BODY_PROFILES control points so male/female read as genuinely different silhouettes
// (shoulder:hip ratio, waist taper) rather than one primitive scaled by width. This remains an
// original procedural reference figure, not a licensed scan -- see docs/ANATOMY.md for the GLB
// replacement path (frontend/public/models/anatomy/{male,female}/*.glb).
const SKIN='#d9b593',BONE='#eee7d8';
function Shell({shape,args,position,rotation,planes,opacity=.11,color=SKIN}){
 return <mesh position={position} rotation={rotation} raycast={()=>null}>
 {shape==='sphere'&&<sphereGeometry args={args}/>}
 {shape==='cylinder'&&<cylinderGeometry args={args}/>}
 {shape==='box'&&<boxGeometry args={args}/>}
 {shape==='torus'&&<torusGeometry args={args}/>}
 <meshPhysicalMaterial color={color} transparent opacity={opacity} roughness={.38} depthWrite={false} clippingPlanes={planes} side={DoubleSide}/>
 </mesh>;
}
function Torso({profile,planes,opacity}){
 const geometry=useMemo(()=>buildTorsoLathe(profile.torso),[profile]);
 React.useEffect(()=>()=>geometry.dispose(),[geometry]);
 return <mesh geometry={geometry} scale={[1,1,profile.depthRatio]} raycast={()=>null}>
  <meshPhysicalMaterial color={SKIN} transparent opacity={opacity} roughness={.36} depthWrite={false} clippingPlanes={planes} side={DoubleSide}/>
 </mesh>;
}
// Real BodyParts3D whole-body skin surface (single mesh, FMA55665 "Skin", ~203k faces) --
// replaces the whole procedural sphere-head/capsule-limb shell (Torso+head+neck+Limb below) when
// available. It's a single reference-body scan, not sex-differentiated, so BODY_PROFILES stops
// shaping the visible skin once this is loaded; organ placement/logic and the sex-specific torso
// fallback are unaffected either way. Falls back to the procedural shell when extras.glb isn't
// configured or doesn't include a "skinBody" mesh.
function RealBodyShell({planes,opacity}){
 const extras=useAnatomyExtras();
 return <group position={extrasTransform.position} rotation={extrasTransform.rotation} scale={extrasTransform.scale}>
  <mesh name="skinBody" geometry={extras.skinBody} raycast={()=>null}>
   <meshPhysicalMaterial color={SKIN} transparent opacity={opacity} roughness={.36} depthWrite={false} clippingPlanes={planes} side={DoubleSide}/>
  </mesh>
 </group>;
}
function Limb({side,planes,limbScale,shoulderX,hipX}){
 const s=side,k=limbScale,armX=shoulderX/1.22,legX=hipX/.55;
 return <group>
  <Shell shape="sphere" args={[.19*k,16,12]} position={[s*1.22*armX,2.02,-.05]} planes={planes}/>
  <Shell shape="cylinder" args={[.18*k,.15*k,1.05,16]} position={[s*1.28*armX,1.45,-.03]} rotation={[0,0,s*-.09]} planes={planes}/>
  <Shell shape="sphere" args={[.15*k,16,12]} position={[s*1.34*armX,.9,0]} planes={planes}/>
  <Shell shape="cylinder" args={[.14*k,.105*k,1,16]} position={[s*1.3*armX,.35,.02]} rotation={[0,0,s*-.05]} planes={planes}/>
  <Shell shape="sphere" args={[.14*k,16,12]} position={[s*1.27*armX,-.28,.05]} planes={planes}/>
  <Shell shape="sphere" args={[.26*k,16,12]} position={[s*.52*legX,-1.55,-.05]} planes={planes}/>
  <Shell shape="cylinder" args={[.27*k,.21*k,1.55,16]} position={[s*.55*legX,-2.35,-.05]} planes={planes}/>
  <Shell shape="sphere" args={[.19*k,16,12]} position={[s*.56*legX,-3.12,-.03]} planes={planes}/>
  <Shell shape="cylinder" args={[.19*k,.13*k,1.5,16]} position={[s*.57*legX,-3.9,0]} planes={planes}/>
  <Shell shape="box" args={[.28*k,.16*k,.62*k]} position={[s*.58*legX,-4.68,.22]} planes={planes}/>
 </group>;
}
// Simplified skeleton layer (skull outline, ribcage rings, pelvis ring, long bones). A separate
// togglable reference layer -- not a CT-derived skeletal reconstruction. Used only as a fallback
// when the real BodyParts3D full-body skeleton mesh (extras.glb) isn't available.
function ProceduralSkeleton({planes,profile}){
 const armX=profile.shoulderX/1.22,legX=profile.hipX/.55;
 return <group>
  <Shell shape="sphere" args={[.42*profile.headScale,16,12]} position={[0,3.46,.02]} color={BONE} opacity={.5} planes={planes}/>
  {[2.35,2.0,1.65,1.3].map((y,i)=><Shell key={y} shape="torus" args={[.6-i*.03,.045,8,20]} position={[0,y,-.05]} rotation={[Math.PI/2,0,0]} color={BONE} opacity={.55} planes={planes}/>)}
  <Shell shape="torus" args={[.48,.08,8,20]} position={[0,-1.55,-.05]} rotation={[Math.PI/2,0,0]} color={BONE} opacity={.55} planes={planes}/>
  {[-1,1].map(sd=><group key={sd}>
   <Shell shape="cylinder" args={[.055,.05,1.0,10]} position={[sd*1.28*armX,1.45,-.03]} rotation={[0,0,sd*-.09]} color={BONE} opacity={.6} planes={planes}/>
   <Shell shape="cylinder" args={[.045,.04,.95,10]} position={[sd*1.3*armX,.4,.02]} rotation={[0,0,sd*-.05]} color={BONE} opacity={.6} planes={planes}/>
   <Shell shape="cylinder" args={[.09,.07,1.5,10]} position={[sd*.55*legX,-2.35,-.05]} color={BONE} opacity={.6} planes={planes}/>
   <Shell shape="cylinder" args={[.07,.05,1.45,10]} position={[sd*.57*legX,-3.9,0]} color={BONE} opacity={.6} planes={planes}/>
  </group>)}
 </group>;
}
// Real BodyParts3D full-body skeleton, merged (original relative bone positions preserved) into
// a single mesh at build time -- see build_real_anatomy.py / AnatomyExtrasAssets.jsx. Falls back
// to the procedural skeleton above when extras.glb isn't configured or failed to load.
function Skeleton({planes,profile}){
 const extras=useAnatomyExtras();
 if(!extras.skeletonFull)return <ProceduralSkeleton planes={planes} profile={profile}/>;
 return <group position={extrasTransform.position} rotation={extrasTransform.rotation} scale={extrasTransform.scale}>
  <mesh geometry={extras.skeletonFull} raycast={()=>null}>
   <meshStandardMaterial color={BONE} roughness={.55} transparent opacity={.7} depthWrite={false} clippingPlanes={planes} side={DoubleSide}/>
  </mesh>
 </group>;
}
// Real BodyParts3D full-body arterial/venous tree, merged the same way. Optional layer -- only
// rendered when both extras.glb is loaded and the "Vascular (full)" layer is shown; no
// procedural fallback since the existing 'vascular' organ already covers that case.
function VascularFull({planes}){
 const extras=useAnatomyExtras();
 if(!extras.vascularFull)return null;
 return <group position={extrasTransform.position} rotation={extrasTransform.rotation} scale={extrasTransform.scale}>
  <mesh geometry={extras.vascularFull} raycast={()=>null}>
   <meshStandardMaterial color="#a83f4d" roughness={.5} transparent opacity={.4} depthWrite={false} clippingPlanes={planes} side={DoubleSide}/>
  </mesh>
 </group>;
}
export default function AnatomyModel({selected,choose,hidden,data,planes,reduced,sex,bodyOpacity,showLabels,onHoverOrgan,demoImagingOpen}){
 const profile=BODY_PROFILES[sex||'unspecified'];
 const opacity=Math.min(1,Math.max(0,(bodyOpacity??55)/100));
 const extras=useAnatomyExtras();
 return <group>
 {!hidden.body&&(extras.skinBody
  ?<RealBodyShell planes={planes} opacity={opacity}/>
  :<>
   <Torso profile={profile} planes={planes} opacity={opacity}/>
   <Shell shape="sphere" args={[.58*profile.headScale,32,24]} position={[0,3.5,.04]} opacity={opacity} planes={planes}/>
   <Shell shape="cylinder" args={[.2,.28,.5,24]} position={[0,2.92,-.05]} opacity={opacity} planes={planes}/>
   <Limb side={-1} planes={planes} limbScale={profile.limbScale} shoulderX={profile.shoulderX} hipX={profile.hipX}/>
   <Limb side={1} planes={planes} limbScale={profile.limbScale} shoulderX={profile.shoulderX} hipX={profile.hipX}/>
  </>)}
 {!hidden.skeleton&&<Skeleton planes={planes} profile={profile}/>}
 {!hidden.vascularFull&&<VascularFull planes={planes}/>}
 {organs.filter(o=>!hidden[o.id]).map(o=>{
  const targets=targetsFor(data,o.group);
  return <Organ key={o.id} organ={o} selected={selected===o.id} dim={!!selected&&selected!==o.id} choose={choose}
   severity={severityFor(targets)} targets={targets} planes={planes} reduced={reduced}
   showLabels={showLabels} onHover={onHoverOrgan} demoImagingOpen={demoImagingOpen}/>;
 })}
 {!hidden.spine&&Array.from({length:18},(_,i)=><mesh key={i} position={[0,-1.49+i*.218,-.56]} raycast={()=>null}><cylinderGeometry args={[.2,.19,.15,12]}/><meshStandardMaterial color="#c2ced0" transparent opacity={selected==='spine'?.9:.25} clippingPlanes={planes}/></mesh>)}
 {!hidden.vascular&&[-1,1].map(side=><Line key={side} points={[[0,-.25,-.1],[side*.3,-.3,-.15],[side*.6,-.36,-.22]]} color={colors[severityFor(targetsFor(data,'systemic'))]} lineWidth={3}/>)}
 </group>;
}

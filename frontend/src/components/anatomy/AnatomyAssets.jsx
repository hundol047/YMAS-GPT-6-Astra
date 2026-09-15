import React,{createContext,useContext,useMemo,Suspense} from 'react';
import {useGLTF} from '@react-three/drei';
import {Vector3} from 'three';
import {organs} from '../../data/anatomyMap';
const empty=Object.freeze({}),Context=createContext(empty);
export const useAnatomyAssets=()=>useContext(Context);
// 'procedural' = no GLB configured (default demo). 'loaded' = GLB in use. 'fallback' = GLB
// configured but failed to load/validate, showing the procedural model instead.
const StatusContext=createContext('procedural');
export const useAnatomyAssetStatus=()=>useContext(StatusContext);
class AssetBoundary extends React.Component{
 state={failed:false};static getDerivedStateFromError(){return {failed:true}}
 render(){return this.state.failed?<><p role="status" className="an-asset-message">정밀 모델을 불러오지 못했습니다. 기본 참고 모델로 표시합니다.</p><StatusContext.Provider value="fallback">{this.props.fallback}</StatusContext.Provider></>:this.props.children}
}
function Loaded({url,children}){
 const {nodes}=useGLTF(url);
 const geometries=useMemo(()=>{
  const result={};
  for(const organ of organs){
   const node=nodes[organ.id];
   if(!node?.isMesh||!node.geometry.index)continue; // asset may only cover a subset of organs; rest stays procedural
   const g=node.geometry.clone();g.computeBoundingBox();const center=g.boundingBox.getCenter(new Vector3()),size=g.boundingBox.getSize(new Vector3());
   if(Math.min(size.x,size.y,size.z)<=0){g.dispose();continue;}
   g.translate(-center.x,-center.y,-center.z);g.scale(2/size.x,2/size.y,2/size.z);g.computeVertexNormals();result[organ.id]=g;
  }
  if(!Object.keys(result).length)throw new Error('Anatomy GLB has no matching organ meshes');
  return result;
 },[nodes]);
 React.useEffect(()=>()=>Object.values(geometries).forEach(g=>g.dispose()),[geometries]);
 return <Context.Provider value={geometries}><StatusContext.Provider value="loaded">{children}</StatusContext.Provider></Context.Provider>;
}
// Sex-specific GLB first (VITE_ANATOMY_MODEL_URL_MALE / _FEMALE), then the generic single-model
// override, then no GLB (procedural reference figure). See frontend/public/models/anatomy/README.md.
function urlFor(sex){
 const perSex=sex==='male'?import.meta.env.VITE_ANATOMY_MODEL_URL_MALE:sex==='female'?import.meta.env.VITE_ANATOMY_MODEL_URL_FEMALE:undefined;
 return perSex||import.meta.env.VITE_ANATOMY_MODEL_URL;
}
export function AnatomyAssets({sex,children}){
 const modelUrl=urlFor(sex);
 if(!modelUrl)return <StatusContext.Provider value="procedural">{children}</StatusContext.Provider>;
 return <AssetBoundary fallback={children}><Suspense fallback={<div className="an-loading">Loading anatomical model…</div>}><Loaded url={modelUrl}>{children}</Loaded></Suspense></AssetBoundary>;
}

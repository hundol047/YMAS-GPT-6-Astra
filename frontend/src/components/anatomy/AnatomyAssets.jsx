import React,{createContext,useContext,useMemo,Suspense} from 'react';
import {useGLTF} from '@react-three/drei';
import {Vector3} from 'three';
import {organs} from '../../data/anatomyMap';
const empty=Object.freeze({}),Context=createContext(empty);
export const useAnatomyAssets=()=>useContext(Context);
class AssetBoundary extends React.Component{
 state={failed:false};static getDerivedStateFromError(){return {failed:true}}
 render(){return this.state.failed?<><p role="status" className="an-asset-message">정밀 모델을 불러오지 못했습니다. 기본 참고 모델로 표시합니다.</p>{this.props.fallback}</>:this.props.children}
}
function Loaded({url,children}){
 const {nodes}=useGLTF(url);
 const geometries=useMemo(()=>{
  const result={};
  for(const organ of organs){
   const node=nodes[organ.id];
   if(!node?.isMesh||!node.geometry.index)throw new Error('Anatomy GLB must contain indexed organ meshes: '+organ.id);
   const g=node.geometry.clone();g.computeBoundingBox();const center=g.boundingBox.getCenter(new Vector3()),size=g.boundingBox.getSize(new Vector3());
   if(Math.min(size.x,size.y,size.z)<=0){g.dispose();throw new Error('Invalid anatomy mesh dimensions')}
   g.translate(-center.x,-center.y,-center.z);g.scale(2/size.x,2/size.y,2/size.z);g.computeVertexNormals();result[organ.id]=g;
  }
  return result;
 },[nodes]);
 React.useEffect(()=>()=>Object.values(geometries).forEach(g=>g.dispose()),[geometries]);
 return <Context.Provider value={geometries}>{children}</Context.Provider>;
}
const modelUrl=import.meta.env.VITE_ANATOMY_MODEL_URL;
export function AnatomyAssets({children}){
 if(!modelUrl)return children;
 return <AssetBoundary fallback={children}><Suspense fallback={<div className="an-loading">Loading anatomical model…</div>}><Loaded url={modelUrl}>{children}</Loaded></Suspense></AssetBoundary>;
}

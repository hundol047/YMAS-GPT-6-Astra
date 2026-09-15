import React,{createContext,useContext,useMemo,Suspense} from 'react';
import {useGLTF} from '@react-three/drei';

const empty=Object.freeze({}),Context=createContext(empty);
export const useAnatomyExtras=()=>useContext(Context);

class ExtrasBoundary extends React.Component{
 state={failed:false};static getDerivedStateFromError(){return {failed:true}}
 render(){return this.props.children}
 // 실패해도 조용히 없는 채로 계속 진행 (골격/혈관은 선택 사항이라 organ과 달리 fallback UI 안 씀)
}

function Loaded({url,children}){
 const {nodes}=useGLTF(url);
 // organ과 다르게 여기선 개별 정규화(centering/scale)를 하지 않음 — 뼈들의
 // 상대 위치가 유지되어야 전신 골격 모양이 나오기 때문. 화면 배율은
 // AnatomyModel.jsx에서 extrasTransform으로 한 번만 적용.
 const geometries=useMemo(()=>{
  const result={};
  for(const key of ['skeletonFull','vascularFull','skinBody']){
   const node=nodes[key];
   if(node?.isMesh&&node.geometry)result[key]=node.geometry;
  }
  return result;
 },[nodes]);
 return <Context.Provider value={geometries}>{children}</Context.Provider>;
}

const extrasUrl=import.meta.env.VITE_ANATOMY_EXTRAS_URL;
export function AnatomyExtras({children}){
 if(!extrasUrl)return children;
 return <ExtrasBoundary><Suspense fallback={children}><Loaded url={extrasUrl}>{children}</Loaded></Suspense></ExtrasBoundary>;
}

import React,{useMemo,useRef,useEffect,useState} from 'react';
import {Canvas,useFrame,useThree} from '@react-three/fiber';
import {OrbitControls,GizmoHelper,GizmoViewport} from '@react-three/drei';
import {Plane,Vector3,DoubleSide} from 'three';
import AnatomyModel from './AnatomyModel';
import {organs,sliceValue,sliceAxes} from '../../data/anatomyMap';
class RenderBoundary extends React.Component{
 state={failed:false};static getDerivedStateFromError(){return {failed:true}}
 render(){return this.state.failed?<div className="an-fallback">3D rendering is unavailable on this device.<br/>장기 목록에서 관련 근거를 확인할 수 있습니다.</div>:this.props.children}
}
function World(props){
 const {mode,position,clipping,view,selected,reduced}=props,controls=useRef(),transition=useRef(null),{camera,gl}=useThree();
 const axis=sliceAxes[mode],value=sliceValue(mode,position);
 const normal=useMemo(()=>new Vector3(...[0,1,2].map(i=>i===axis?-1:0)),[axis]);
 const planes=useMemo(()=>clipping?[new Plane(normal,value)]:[],[clipping,normal,value]);
 const planePosition=[0,0,0];planePosition[axis]=value;
 const rotation=mode==='axial'?[-Math.PI/2,0,0]:mode==='sagittal'?[0,Math.PI/2,0]:[0,0,0];
 useEffect(()=>{gl.localClippingEnabled=true},[gl]);
 useEffect(()=>{
  const target=new Vector3(...(view.kind==='focus'?(organs.find(o=>o.id===selected)?.p||[0,.8,0]):[0,.8,0]));
  const dirs={front:[0,0,9],back:[0,0,-9],left:[9,0,0],right:[-9,0,0],top:[0,9,.01],reset:[3,1.4,9],focus:[0,.2,4.4]};
  transition.current={target,position:target.clone().add(new Vector3(...(dirs[view.kind]||dirs.reset)))};
 },[view,selected]);
 useFrame((_,delta)=>{const t=transition.current;if(!t||!controls.current)return;const f=reduced?1:1-Math.exp(-delta*7);camera.position.lerp(t.position,f);controls.current.target.lerp(t.target,f);controls.current.update();if(camera.position.distanceTo(t.position)<.01)transition.current=null;});
 return <>
 <color attach="background" args={['#0c1a25']}/><ambientLight intensity={1.1}/><directionalLight position={[3,5,5]} intensity={2}/><directionalLight position={[-4,2,-3]} color="#84cadc" intensity={1.5}/>
 <AnatomyModel {...props} planes={planes}/>
 <mesh position={planePosition} rotation={rotation} raycast={()=>null}><planeGeometry args={mode==='axial'?[3.6,2.2]:[mode==='sagittal'?2.2:3.6,7.6]}/><meshBasicMaterial color="#6bd5ca" transparent opacity={.12} side={DoubleSide} depthWrite={false}/></mesh>
 <gridHelper args={[8,16,'#284452','#182f3b']} position={[0,-1.95,0]}/>
 <OrbitControls ref={controls} makeDefault minDistance={2} maxDistance={16} enableDamping={!reduced} onStart={()=>{transition.current=null}}/>
 <GizmoHelper alignment="bottom-right" margin={[48,48]}><GizmoViewport axisColors={['#7d9ea9','#7d9ea9','#7d9ea9']} labelColor="#07121b"/></GizmoHelper>
 </>;
}
export default function AnatomyScene(props){
 const [lost,setLost]=useState(false);
 return <RenderBoundary>{lost?<div className="an-fallback">3D rendering is unavailable on this device.<button onClick={()=>setLost(false)}>다시 시도</button></div>:<Canvas dpr={[1,1.5]} camera={{position:[3,2.2,9],fov:43}} gl={{antialias:true,localClippingEnabled:true}} fallback={<div className="an-fallback">3D rendering is unavailable on this device.</div>} onCreated={({gl})=>{gl.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();setLost(true)},{once:true})}}><World {...props}/></Canvas>}</RenderBoundary>;
}

var cn=Object.defineProperty;var un=(o,t,n)=>t in o?cn(o,t,{enumerable:!0,configurable:!0,writable:!0,value:n}):o[t]=n;var Mt=(o,t,n)=>un(o,typeof t!="symbol"?t+"":t,n);import{r as l,j as dn,k as fn,R as c,B as mn,o as Gt,t as Pt,s as Ot,a as mt,m as me,l as pn,b as hn,d as gn}from"./index-C_R70_GN.js";import{j as fe,m as yn,e as vn,u as En,a as bn,b as xn,c as wn,d as Sn,i as Mn,E as Pn,B as On,f as Ln,T as An,g as z,h as Me,V as T,D as be,k as q,P as Ne,O as He,v as Vt,S as Lt,Q as Ke,M as Ae,l as _e,R as _n,n as Zt,I as Cn,F as At,o as pt,p as Re,W as Tn,q as gt,r as $t,s as Rn,U as _t,t as Ct,w as Dn,x as De,L as zn,y as qt,z as jn,C as In,A as Bn,H as Un,G as Tt,J as kn,K as Nn,N as Hn,X as Fn,Y as Wn,Z as Yn,_ as Qe,$ as Xn,a0 as Gn,a1 as Vn}from"./AnatomyWorkspace-Dfo9w3uM.js";function V(){return V=Object.assign?Object.assign.bind():function(o){for(var t=1;t<arguments.length;t++){var n=arguments[t];for(var e in n)({}).hasOwnProperty.call(n,e)&&(o[e]=n[e])}return o},V.apply(null,arguments)}function Rt(o,t){let n;return(...e)=>{window.clearTimeout(n),n=window.setTimeout(()=>o(...e),t)}}function Zn({debounce:o,scroll:t,polyfill:n,offsetSize:e}={debounce:0,scroll:!1,offsetSize:!1}){const r=n||(typeof window>"u"?class{}:window.ResizeObserver);if(!r)throw new Error("This browser does not support ResizeObserver out of the box. See: https://github.com/react-spring/react-use-measure/#resize-observer-polyfills");const[a,u]=l.useState({left:0,top:0,width:0,height:0,bottom:0,right:0,x:0,y:0}),s=l.useRef({element:null,scrollContainers:null,resizeObserver:null,lastBounds:a,orientationHandler:null}),d=o?typeof o=="number"?o:o.scroll:null,M=o?typeof o=="number"?o:o.resize:null,f=l.useRef(!1);l.useEffect(()=>(f.current=!0,()=>void(f.current=!1)));const[m,y,v]=l.useMemo(()=>{const S=()=>{if(!s.current.element)return;const{left:C,top:b,width:E,height:A,bottom:x,right:X,x:j,y:_}=s.current.element.getBoundingClientRect(),L={left:C,top:b,width:E,height:A,bottom:x,right:X,x:j,y:_};s.current.element instanceof HTMLElement&&e&&(L.height=s.current.element.offsetHeight,L.width=s.current.element.offsetWidth),Object.freeze(L),f.current&&!Qn(s.current.lastBounds,L)&&u(s.current.lastBounds=L)};return[S,M?Rt(S,M):S,d?Rt(S,d):S]},[u,e,d,M]);function O(){s.current.scrollContainers&&(s.current.scrollContainers.forEach(S=>S.removeEventListener("scroll",v,!0)),s.current.scrollContainers=null),s.current.resizeObserver&&(s.current.resizeObserver.disconnect(),s.current.resizeObserver=null),s.current.orientationHandler&&("orientation"in screen&&"removeEventListener"in screen.orientation?screen.orientation.removeEventListener("change",s.current.orientationHandler):"onorientationchange"in window&&window.removeEventListener("orientationchange",s.current.orientationHandler))}function h(){s.current.element&&(s.current.resizeObserver=new r(v),s.current.resizeObserver.observe(s.current.element),t&&s.current.scrollContainers&&s.current.scrollContainers.forEach(S=>S.addEventListener("scroll",v,{capture:!0,passive:!0})),s.current.orientationHandler=()=>{v()},"orientation"in screen&&"addEventListener"in screen.orientation?screen.orientation.addEventListener("change",s.current.orientationHandler):"onorientationchange"in window&&window.addEventListener("orientationchange",s.current.orientationHandler))}const g=S=>{!S||S===s.current.element||(O(),s.current.element=S,s.current.scrollContainers=Kt(S),h())};return qn(v,!!t),$n(y),l.useEffect(()=>{O(),h()},[t,v,y]),l.useEffect(()=>O,[]),[g,a,m]}function $n(o){l.useEffect(()=>{const t=o;return window.addEventListener("resize",t),()=>void window.removeEventListener("resize",t)},[o])}function qn(o,t){l.useEffect(()=>{if(t){const n=o;return window.addEventListener("scroll",n,{capture:!0,passive:!0}),()=>void window.removeEventListener("scroll",n,!0)}},[o,t])}function Kt(o){const t=[];if(!o||o===document.body)return t;const{overflow:n,overflowX:e,overflowY:r}=window.getComputedStyle(o);return[n,e,r].some(a=>a==="auto"||a==="scroll")&&t.push(o),[...t,...Kt(o.parentElement)]}const Kn=["x","y","top","bottom","left","right","width","height"],Qn=(o,t)=>Kn.every(n=>o[n]===t[n]);function Jn({ref:o,children:t,fallback:n,resize:e,style:r,gl:a,events:u=Sn,eventSource:s,eventPrefix:d,shadows:M,linear:f,flat:m,legacy:y,orthographic:v,frameloop:O,dpr:h,performance:g,raycaster:S,camera:C,scene:b,onPointerMissed:E,onCreated:A,...x}){l.useMemo(()=>vn(An),[]);const X=En(),[j,_]=Zn({scroll:!0,debounce:{scroll:50,resize:0},...e}),L=l.useRef(null),I=l.useRef(null);l.useImperativeHandle(o,()=>L.current);const Pe=bn(E),[K,xe]=l.useState(!1),[B,pe]=l.useState(!1);if(K)throw K;if(B)throw B;const U=l.useRef(null);xn(()=>{const Z=L.current;if(_.width>0&&_.height>0&&Z){U.current||(U.current=wn(Z));async function Q(){await U.current.configure({gl:a,scene:b,events:u,shadows:M,linear:f,flat:m,legacy:y,orthographic:v,frameloop:O,dpr:h,performance:g,raycaster:S,camera:C,size:_,onPointerMissed:(...$)=>Pe.current==null?void 0:Pe.current(...$),onCreated:$=>{$.events.connect==null||$.events.connect(s?Mn(s)?s.current:s:I.current),d&&$.setEvents({compute:(J,k)=>{const le=J[d+"X"],he=J[d+"Y"];k.pointer.set(le/k.size.width*2-1,-(he/k.size.height)*2+1),k.raycaster.setFromCamera(k.pointer,k.camera)}}),A==null||A($)}}),U.current.render(fe.jsx(X,{children:fe.jsx(Pn,{set:pe,children:fe.jsx(l.Suspense,{fallback:fe.jsx(On,{set:xe}),children:t??null})})}))}Q()}}),l.useEffect(()=>{const Z=L.current;if(Z)return()=>Ln(Z)},[]);const te=s?"none":"auto";return fe.jsx("div",{ref:I,style:{position:"relative",width:"100%",height:"100%",overflow:"hidden",pointerEvents:te,...r},...x,children:fe.jsx("div",{ref:j,style:{width:"100%",height:"100%"},children:fe.jsx("canvas",{ref:L,style:{display:"block"},children:n})})})}function eo(o){return fe.jsx(yn,{children:fe.jsx(Jn,{...o})})}const Fe=new T,yt=new T,to=new T,Dt=new q;function no(o,t,n){const e=Fe.setFromMatrixPosition(o.matrixWorld);e.project(t);const r=n.width/2,a=n.height/2;return[e.x*r+r,-(e.y*a)+a]}function oo(o,t){const n=Fe.setFromMatrixPosition(o.matrixWorld),e=yt.setFromMatrixPosition(t.matrixWorld),r=n.sub(e),a=t.getWorldDirection(to);return r.angleTo(a)>Math.PI/2}function io(o,t,n,e){const r=Fe.setFromMatrixPosition(o.matrixWorld),a=r.clone();a.project(t),Dt.set(a.x,a.y),n.setFromCamera(Dt,t);const u=n.intersectObjects(e,!0);if(u.length){const s=u[0].distance;return r.distanceTo(n.ray.origin)<s}return!0}function ro(o,t){if(t instanceof He)return t.zoom;if(t instanceof Ne){const n=Fe.setFromMatrixPosition(o.matrixWorld),e=yt.setFromMatrixPosition(t.matrixWorld),r=t.fov*Math.PI/180,a=n.distanceTo(e);return 1/(2*Math.tan(r/2)*a)}else return 1}function so(o,t,n){if(t instanceof Ne||t instanceof He){const e=Fe.setFromMatrixPosition(o.matrixWorld),r=yt.setFromMatrixPosition(t.matrixWorld),a=e.distanceTo(r),u=(n[1]-n[0])/(t.far-t.near),s=n[1]-u*t.far;return Math.round(u*a+s)}}const ht=o=>Math.abs(o)<1e-10?0:o;function Qt(o,t,n=""){let e="matrix3d(";for(let r=0;r!==16;r++)e+=ht(t[r]*o.elements[r])+(r!==15?",":")");return n+e}const ao=(o=>t=>Qt(t,o))([1,-1,1,1,1,-1,1,1,1,-1,1,1,1,-1,1,1]),lo=(o=>(t,n)=>Qt(t,o(n),"translate(-50%,-50%)"))(o=>[1/o,1/o,1/o,1,-1/o,-1/o,-1/o,-1,1/o,1/o,1/o,1,1,1,1,1]);function co(o){return o&&typeof o=="object"&&"current"in o}const st=l.forwardRef(({children:o,eps:t=.001,style:n,className:e,prepend:r,center:a,fullscreen:u,portal:s,distanceFactor:d,sprite:M=!1,transform:f=!1,occlude:m,onOcclude:y,castShadow:v,receiveShadow:O,material:h,geometry:g,zIndexRange:S=[16777271,0],calculatePosition:C=no,as:b="div",wrapperClass:E,pointerEvents:A="auto",...x},X)=>{const{gl:j,camera:_,scene:L,size:I,raycaster:Pe,events:K,viewport:xe}=z(),[B]=l.useState(()=>document.createElement(b)),pe=l.useRef(null),U=l.useRef(null),te=l.useRef(0),Z=l.useRef([0,0]),Q=l.useRef(null),$=l.useRef(null),J=(s==null?void 0:s.current)||K.connected||j.domElement.parentNode,k=l.useRef(null),le=l.useRef(!1),he=l.useMemo(()=>m&&m!=="blending"||Array.isArray(m)&&m.length&&co(m[0]),[m]);l.useLayoutEffect(()=>{const G=j.domElement;m&&m==="blending"?(G.style.zIndex=`${Math.floor(S[0]/2)}`,G.style.position="absolute",G.style.pointerEvents="none"):(G.style.zIndex=null,G.style.position=null,G.style.pointerEvents=null)},[m]),l.useLayoutEffect(()=>{if(U.current){const G=pe.current=dn.createRoot(B);if(L.updateMatrixWorld(),f)B.style.cssText="position:absolute;top:0;left:0;pointer-events:none;overflow:hidden;";else{const D=C(U.current,_,I);B.style.cssText=`position:absolute;top:0;left:0;transform:translate3d(${D[0]}px,${D[1]}px,0);transform-origin:0 0;`}return J&&(r?J.prepend(B):J.appendChild(B)),()=>{J&&J.removeChild(B),G.unmount()}}},[J,f]),l.useLayoutEffect(()=>{E&&(B.className=E)},[E]);const ze=l.useMemo(()=>f?{position:"absolute",top:0,left:0,width:I.width,height:I.height,transformStyle:"preserve-3d",pointerEvents:"none"}:{position:"absolute",transform:a?"translate3d(-50%,-50%,0)":"none",...u&&{top:-I.height/2,left:-I.width/2,width:I.width,height:I.height},...n},[n,a,u,I,f]),Je=l.useMemo(()=>({position:"absolute",pointerEvents:A}),[A]);l.useLayoutEffect(()=>{if(le.current=!1,f){var G;(G=pe.current)==null||G.render(l.createElement("div",{ref:Q,style:ze},l.createElement("div",{ref:$,style:Je},l.createElement("div",{ref:X,className:e,style:n,children:o}))))}else{var D;(D=pe.current)==null||D.render(l.createElement("div",{ref:X,style:ze,className:e,children:o}))}});const ge=l.useRef(!0);Me(G=>{if(U.current){_.updateMatrixWorld(),U.current.updateWorldMatrix(!0,!1);const D=f?Z.current:C(U.current,_,I);if(f||Math.abs(te.current-_.zoom)>t||Math.abs(Z.current[0]-D[0])>t||Math.abs(Z.current[1]-D[1])>t){const ne=oo(U.current,_);let ee=!1;he&&(Array.isArray(m)?ee=m.map(oe=>oe.current):m!=="blending"&&(ee=[L]));const ye=ge.current;if(ee){const oe=io(U.current,_,Pe,ee);ge.current=oe&&!ne}else ge.current=!ne;ye!==ge.current&&(y?y(!ge.current):B.style.display=ge.current?"block":"none");const Oe=Math.floor(S[0]/2),et=m?he?[S[0],Oe]:[Oe-1,0]:S;if(B.style.zIndex=`${so(U.current,_,et)}`,f){const[oe,je]=[I.width/2,I.height/2],Le=_.projectionMatrix.elements[5]*je,{isOrthographicCamera:Ye,top:tt,left:Xe,bottom:Ie,right:we}=_,nt=ao(_.matrixWorldInverse),ot=Ye?`scale(${Le})translate(${ht(-(we+Xe)/2)}px,${ht((tt+Ie)/2)}px)`:`translateZ(${Le}px)`;let ie=U.current.matrixWorld;M&&(ie=_.matrixWorldInverse.clone().transpose().copyPosition(ie).scale(U.current.scale),ie.elements[3]=ie.elements[7]=ie.elements[11]=0,ie.elements[15]=1),B.style.width=I.width+"px",B.style.height=I.height+"px",B.style.perspective=Ye?"":`${Le}px`,Q.current&&$.current&&(Q.current.style.transform=`${ot}${nt}translate(${oe}px,${je}px)`,$.current.style.transform=lo(ie,1/((d||10)/400)))}else{const oe=d===void 0?1:ro(U.current,_)*d;B.style.transform=`translate3d(${D[0]}px,${D[1]}px,0) scale(${oe})`}Z.current=D,te.current=_.zoom}}if(!he&&k.current&&!le.current)if(f){if(Q.current){const D=Q.current.children[0];if(D!=null&&D.clientWidth&&D!=null&&D.clientHeight){const{isOrthographicCamera:ne}=_;if(ne||g)x.scale&&(Array.isArray(x.scale)?x.scale instanceof T?k.current.scale.copy(x.scale.clone().divideScalar(1)):k.current.scale.set(1/x.scale[0],1/x.scale[1],1/x.scale[2]):k.current.scale.setScalar(1/x.scale));else{const ee=(d||10)/400,ye=D.clientWidth*ee,Oe=D.clientHeight*ee;k.current.scale.set(ye,Oe,1)}le.current=!0}}}else{const D=B.children[0];if(D!=null&&D.clientWidth&&D!=null&&D.clientHeight){const ne=1/xe.factor,ee=D.clientWidth*ne,ye=D.clientHeight*ne;k.current.scale.set(ee,ye,1),le.current=!0}k.current.lookAt(G.camera.position)}});const We=l.useMemo(()=>({vertexShader:f?void 0:`
          /*
            This shader is from the THREE's SpriteMaterial.
            We need to turn the backing plane into a Sprite
            (make it always face the camera) if "transfrom"
            is false.
          */
          #include <common>

          void main() {
            vec2 center = vec2(0., 1.);
            float rotation = 0.0;

            // This is somewhat arbitrary, but it seems to work well
            // Need to figure out how to derive this dynamically if it even matters
            float size = 0.03;

            vec4 mvPosition = modelViewMatrix * vec4( 0.0, 0.0, 0.0, 1.0 );
            vec2 scale;
            scale.x = length( vec3( modelMatrix[ 0 ].x, modelMatrix[ 0 ].y, modelMatrix[ 0 ].z ) );
            scale.y = length( vec3( modelMatrix[ 1 ].x, modelMatrix[ 1 ].y, modelMatrix[ 1 ].z ) );

            bool isPerspective = isPerspectiveMatrix( projectionMatrix );
            if ( isPerspective ) scale *= - mvPosition.z;

            vec2 alignedPosition = ( position.xy - ( center - vec2( 0.5 ) ) ) * scale * size;
            vec2 rotatedPosition;
            rotatedPosition.x = cos( rotation ) * alignedPosition.x - sin( rotation ) * alignedPosition.y;
            rotatedPosition.y = sin( rotation ) * alignedPosition.x + cos( rotation ) * alignedPosition.y;
            mvPosition.xy += rotatedPosition;

            gl_Position = projectionMatrix * mvPosition;
          }
      `,fragmentShader:`
        void main() {
          gl_FragColor = vec4(0.0, 0.0, 0.0, 0.0);
        }
      `}),[f]);return l.createElement("group",V({},x,{ref:U}),m&&!he&&l.createElement("mesh",{castShadow:v,receiveShadow:O,ref:k},g||l.createElement("planeGeometry",null),h||l.createElement("shaderMaterial",{side:be,vertexShader:We.vertexShader,fragmentShader:We.fragmentShader})))}),Jt=Vt>=125?"uv1":"uv2";var uo=Object.defineProperty,fo=(o,t,n)=>t in o?uo(o,t,{enumerable:!0,configurable:!0,writable:!0,value:n}):o[t]=n,mo=(o,t,n)=>(fo(o,t+"",n),n);class po{constructor(){mo(this,"_listeners")}addEventListener(t,n){this._listeners===void 0&&(this._listeners={});const e=this._listeners;e[t]===void 0&&(e[t]=[]),e[t].indexOf(n)===-1&&e[t].push(n)}hasEventListener(t,n){if(this._listeners===void 0)return!1;const e=this._listeners;return e[t]!==void 0&&e[t].indexOf(n)!==-1}removeEventListener(t,n){if(this._listeners===void 0)return;const r=this._listeners[t];if(r!==void 0){const a=r.indexOf(n);a!==-1&&r.splice(a,1)}}dispatchEvent(t){if(this._listeners===void 0)return;const e=this._listeners[t.type];if(e!==void 0){t.target=this;const r=e.slice(0);for(let a=0,u=r.length;a<u;a++)r[a].call(this,t);t.target=null}}}var ho=Object.defineProperty,go=(o,t,n)=>t in o?ho(o,t,{enumerable:!0,configurable:!0,writable:!0,value:n}):o[t]=n,w=(o,t,n)=>(go(o,typeof t!="symbol"?t+"":t,n),n);const Ve=new _n,zt=new Zt,yo=Math.cos(70*(Math.PI/180)),jt=(o,t)=>(o%t+t)%t;let vo=class extends po{constructor(t,n){super(),w(this,"object"),w(this,"domElement"),w(this,"enabled",!0),w(this,"target",new T),w(this,"minDistance",0),w(this,"maxDistance",1/0),w(this,"minZoom",0),w(this,"maxZoom",1/0),w(this,"minPolarAngle",0),w(this,"maxPolarAngle",Math.PI),w(this,"minAzimuthAngle",-1/0),w(this,"maxAzimuthAngle",1/0),w(this,"enableDamping",!1),w(this,"dampingFactor",.05),w(this,"enableZoom",!0),w(this,"zoomSpeed",1),w(this,"enableRotate",!0),w(this,"rotateSpeed",1),w(this,"enablePan",!0),w(this,"panSpeed",1),w(this,"screenSpacePanning",!0),w(this,"keyPanSpeed",7),w(this,"zoomToCursor",!1),w(this,"autoRotate",!1),w(this,"autoRotateSpeed",2),w(this,"reverseOrbit",!1),w(this,"reverseHorizontalOrbit",!1),w(this,"reverseVerticalOrbit",!1),w(this,"keys",{LEFT:"ArrowLeft",UP:"ArrowUp",RIGHT:"ArrowRight",BOTTOM:"ArrowDown"}),w(this,"mouseButtons",{LEFT:Ae.ROTATE,MIDDLE:Ae.DOLLY,RIGHT:Ae.PAN}),w(this,"touches",{ONE:_e.ROTATE,TWO:_e.DOLLY_PAN}),w(this,"target0"),w(this,"position0"),w(this,"zoom0"),w(this,"_domElementKeyEvents",null),w(this,"getPolarAngle"),w(this,"getAzimuthalAngle"),w(this,"setPolarAngle"),w(this,"setAzimuthalAngle"),w(this,"getDistance"),w(this,"getZoomScale"),w(this,"listenToKeyEvents"),w(this,"stopListenToKeyEvents"),w(this,"saveState"),w(this,"reset"),w(this,"update"),w(this,"connect"),w(this,"dispose"),w(this,"dollyIn"),w(this,"dollyOut"),w(this,"getScale"),w(this,"setScale"),this.object=t,this.domElement=n,this.target0=this.target.clone(),this.position0=this.object.position.clone(),this.zoom0=this.object.zoom,this.getPolarAngle=()=>f.phi,this.getAzimuthalAngle=()=>f.theta,this.setPolarAngle=i=>{let p=jt(i,2*Math.PI),P=f.phi;P<0&&(P+=2*Math.PI),p<0&&(p+=2*Math.PI);let R=Math.abs(p-P);2*Math.PI-R<R&&(p<P?p+=2*Math.PI:P+=2*Math.PI),m.phi=p-P,e.update()},this.setAzimuthalAngle=i=>{let p=jt(i,2*Math.PI),P=f.theta;P<0&&(P+=2*Math.PI),p<0&&(p+=2*Math.PI);let R=Math.abs(p-P);2*Math.PI-R<R&&(p<P?p+=2*Math.PI:P+=2*Math.PI),m.theta=p-P,e.update()},this.getDistance=()=>e.object.position.distanceTo(e.target),this.listenToKeyEvents=i=>{i.addEventListener("keydown",it),this._domElementKeyEvents=i},this.stopListenToKeyEvents=()=>{this._domElementKeyEvents.removeEventListener("keydown",it),this._domElementKeyEvents=null},this.saveState=()=>{e.target0.copy(e.target),e.position0.copy(e.object.position),e.zoom0=e.object.zoom},this.reset=()=>{e.target.copy(e.target0),e.object.position.copy(e.position0),e.object.zoom=e.zoom0,e.object.updateProjectionMatrix(),e.dispatchEvent(r),e.update(),d=s.NONE},this.update=(()=>{const i=new T,p=new T(0,1,0),P=new Ke().setFromUnitVectors(t.up,p),R=P.clone().invert(),H=new T,ce=new Ke,ve=2*Math.PI;return function(){const St=e.object.position;P.setFromUnitVectors(t.up,p),R.copy(P).invert(),i.copy(St).sub(e.target),i.applyQuaternion(P),f.setFromVector3(i),e.autoRotate&&d===s.NONE&&xe(Pe()),e.enableDamping?(f.theta+=m.theta*e.dampingFactor,f.phi+=m.phi*e.dampingFactor):(f.theta+=m.theta,f.phi+=m.phi);let ue=e.minAzimuthAngle,de=e.maxAzimuthAngle;isFinite(ue)&&isFinite(de)&&(ue<-Math.PI?ue+=ve:ue>Math.PI&&(ue-=ve),de<-Math.PI?de+=ve:de>Math.PI&&(de-=ve),ue<=de?f.theta=Math.max(ue,Math.min(de,f.theta)):f.theta=f.theta>(ue+de)/2?Math.max(ue,f.theta):Math.min(de,f.theta)),f.phi=Math.max(e.minPolarAngle,Math.min(e.maxPolarAngle,f.phi)),f.makeSafe(),e.enableDamping===!0?e.target.addScaledVector(v,e.dampingFactor):e.target.add(v),e.zoomToCursor&&_||e.object.isOrthographicCamera?f.radius=k(f.radius):f.radius=k(f.radius*y),i.setFromSpherical(f),i.applyQuaternion(R),St.copy(e.target).add(i),e.object.matrixAutoUpdate||e.object.updateMatrix(),e.object.lookAt(e.target),e.enableDamping===!0?(m.theta*=1-e.dampingFactor,m.phi*=1-e.dampingFactor,v.multiplyScalar(1-e.dampingFactor)):(m.set(0,0,0),v.set(0,0,0));let Be=!1;if(e.zoomToCursor&&_){let Ue=null;if(e.object instanceof Ne&&e.object.isPerspectiveCamera){const ke=i.length();Ue=k(ke*y);const Ge=ke-Ue;e.object.position.addScaledVector(X,Ge),e.object.updateMatrixWorld()}else if(e.object.isOrthographicCamera){const ke=new T(j.x,j.y,0);ke.unproject(e.object),e.object.zoom=Math.max(e.minZoom,Math.min(e.maxZoom,e.object.zoom/y)),e.object.updateProjectionMatrix(),Be=!0;const Ge=new T(j.x,j.y,0);Ge.unproject(e.object),e.object.position.sub(Ge).add(ke),e.object.updateMatrixWorld(),Ue=i.length()}else console.warn("WARNING: OrbitControls.js encountered an unknown camera type - zoom to cursor disabled."),e.zoomToCursor=!1;Ue!==null&&(e.screenSpacePanning?e.target.set(0,0,-1).transformDirection(e.object.matrix).multiplyScalar(Ue).add(e.object.position):(Ve.origin.copy(e.object.position),Ve.direction.set(0,0,-1).transformDirection(e.object.matrix),Math.abs(e.object.up.dot(Ve.direction))<yo?t.lookAt(e.target):(zt.setFromNormalAndCoplanarPoint(e.object.up,e.target),Ve.intersectPlane(zt,e.target))))}else e.object instanceof He&&e.object.isOrthographicCamera&&(Be=y!==1,Be&&(e.object.zoom=Math.max(e.minZoom,Math.min(e.maxZoom,e.object.zoom/y)),e.object.updateProjectionMatrix()));return y=1,_=!1,Be||H.distanceToSquared(e.object.position)>M||8*(1-ce.dot(e.object.quaternion))>M?(e.dispatchEvent(r),H.copy(e.object.position),ce.copy(e.object.quaternion),Be=!1,!0):!1}})(),this.connect=i=>{e.domElement=i,e.domElement.style.touchAction="none",e.domElement.addEventListener("contextmenu",xt),e.domElement.addEventListener("pointerdown",Xe),e.domElement.addEventListener("pointercancel",we),e.domElement.addEventListener("wheel",ie)},this.dispose=()=>{var i,p,P,R,H,ce;e.domElement&&(e.domElement.style.touchAction="auto"),(i=e.domElement)==null||i.removeEventListener("contextmenu",xt),(p=e.domElement)==null||p.removeEventListener("pointerdown",Xe),(P=e.domElement)==null||P.removeEventListener("pointercancel",we),(R=e.domElement)==null||R.removeEventListener("wheel",ie),(H=e.domElement)==null||H.ownerDocument.removeEventListener("pointermove",Ie),(ce=e.domElement)==null||ce.ownerDocument.removeEventListener("pointerup",we),e._domElementKeyEvents!==null&&e._domElementKeyEvents.removeEventListener("keydown",it)};const e=this,r={type:"change"},a={type:"start"},u={type:"end"},s={NONE:-1,ROTATE:0,DOLLY:1,PAN:2,TOUCH_ROTATE:3,TOUCH_PAN:4,TOUCH_DOLLY_PAN:5,TOUCH_DOLLY_ROTATE:6};let d=s.NONE;const M=1e-6,f=new Lt,m=new Lt;let y=1;const v=new T,O=new q,h=new q,g=new q,S=new q,C=new q,b=new q,E=new q,A=new q,x=new q,X=new T,j=new q;let _=!1;const L=[],I={};function Pe(){return 2*Math.PI/60/60*e.autoRotateSpeed}function K(){return Math.pow(.95,e.zoomSpeed)}function xe(i){e.reverseOrbit||e.reverseHorizontalOrbit?m.theta+=i:m.theta-=i}function B(i){e.reverseOrbit||e.reverseVerticalOrbit?m.phi+=i:m.phi-=i}const pe=(()=>{const i=new T;return function(P,R){i.setFromMatrixColumn(R,0),i.multiplyScalar(-P),v.add(i)}})(),U=(()=>{const i=new T;return function(P,R){e.screenSpacePanning===!0?i.setFromMatrixColumn(R,1):(i.setFromMatrixColumn(R,0),i.crossVectors(e.object.up,i)),i.multiplyScalar(P),v.add(i)}})(),te=(()=>{const i=new T;return function(P,R){const H=e.domElement;if(H&&e.object instanceof Ne&&e.object.isPerspectiveCamera){const ce=e.object.position;i.copy(ce).sub(e.target);let ve=i.length();ve*=Math.tan(e.object.fov/2*Math.PI/180),pe(2*P*ve/H.clientHeight,e.object.matrix),U(2*R*ve/H.clientHeight,e.object.matrix)}else H&&e.object instanceof He&&e.object.isOrthographicCamera?(pe(P*(e.object.right-e.object.left)/e.object.zoom/H.clientWidth,e.object.matrix),U(R*(e.object.top-e.object.bottom)/e.object.zoom/H.clientHeight,e.object.matrix)):(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - pan disabled."),e.enablePan=!1)}})();function Z(i){e.object instanceof Ne&&e.object.isPerspectiveCamera||e.object instanceof He&&e.object.isOrthographicCamera?y=i:(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled."),e.enableZoom=!1)}function Q(i){Z(y/i)}function $(i){Z(y*i)}function J(i){if(!e.zoomToCursor||!e.domElement)return;_=!0;const p=e.domElement.getBoundingClientRect(),P=i.clientX-p.left,R=i.clientY-p.top,H=p.width,ce=p.height;j.x=P/H*2-1,j.y=-(R/ce)*2+1,X.set(j.x,j.y,1).unproject(e.object).sub(e.object.position).normalize()}function k(i){return Math.max(e.minDistance,Math.min(e.maxDistance,i))}function le(i){O.set(i.clientX,i.clientY)}function he(i){J(i),E.set(i.clientX,i.clientY)}function ze(i){S.set(i.clientX,i.clientY)}function Je(i){h.set(i.clientX,i.clientY),g.subVectors(h,O).multiplyScalar(e.rotateSpeed);const p=e.domElement;p&&(xe(2*Math.PI*g.x/p.clientHeight),B(2*Math.PI*g.y/p.clientHeight)),O.copy(h),e.update()}function ge(i){A.set(i.clientX,i.clientY),x.subVectors(A,E),x.y>0?Q(K()):x.y<0&&$(K()),E.copy(A),e.update()}function We(i){C.set(i.clientX,i.clientY),b.subVectors(C,S).multiplyScalar(e.panSpeed),te(b.x,b.y),S.copy(C),e.update()}function G(i){J(i),i.deltaY<0?$(K()):i.deltaY>0&&Q(K()),e.update()}function D(i){let p=!1;switch(i.code){case e.keys.UP:te(0,e.keyPanSpeed),p=!0;break;case e.keys.BOTTOM:te(0,-e.keyPanSpeed),p=!0;break;case e.keys.LEFT:te(e.keyPanSpeed,0),p=!0;break;case e.keys.RIGHT:te(-e.keyPanSpeed,0),p=!0;break}p&&(i.preventDefault(),e.update())}function ne(){if(L.length==1)O.set(L[0].pageX,L[0].pageY);else{const i=.5*(L[0].pageX+L[1].pageX),p=.5*(L[0].pageY+L[1].pageY);O.set(i,p)}}function ee(){if(L.length==1)S.set(L[0].pageX,L[0].pageY);else{const i=.5*(L[0].pageX+L[1].pageX),p=.5*(L[0].pageY+L[1].pageY);S.set(i,p)}}function ye(){const i=L[0].pageX-L[1].pageX,p=L[0].pageY-L[1].pageY,P=Math.sqrt(i*i+p*p);E.set(0,P)}function Oe(){e.enableZoom&&ye(),e.enablePan&&ee()}function et(){e.enableZoom&&ye(),e.enableRotate&&ne()}function oe(i){if(L.length==1)h.set(i.pageX,i.pageY);else{const P=rt(i),R=.5*(i.pageX+P.x),H=.5*(i.pageY+P.y);h.set(R,H)}g.subVectors(h,O).multiplyScalar(e.rotateSpeed);const p=e.domElement;p&&(xe(2*Math.PI*g.x/p.clientHeight),B(2*Math.PI*g.y/p.clientHeight)),O.copy(h)}function je(i){if(L.length==1)C.set(i.pageX,i.pageY);else{const p=rt(i),P=.5*(i.pageX+p.x),R=.5*(i.pageY+p.y);C.set(P,R)}b.subVectors(C,S).multiplyScalar(e.panSpeed),te(b.x,b.y),S.copy(C)}function Le(i){const p=rt(i),P=i.pageX-p.x,R=i.pageY-p.y,H=Math.sqrt(P*P+R*R);A.set(0,H),x.set(0,Math.pow(A.y/E.y,e.zoomSpeed)),Q(x.y),E.copy(A)}function Ye(i){e.enableZoom&&Le(i),e.enablePan&&je(i)}function tt(i){e.enableZoom&&Le(i),e.enableRotate&&oe(i)}function Xe(i){var p,P;e.enabled!==!1&&(L.length===0&&((p=e.domElement)==null||p.ownerDocument.addEventListener("pointermove",Ie),(P=e.domElement)==null||P.ownerDocument.addEventListener("pointerup",we)),an(i),i.pointerType==="touch"?rn(i):nt(i))}function Ie(i){e.enabled!==!1&&(i.pointerType==="touch"?sn(i):ot(i))}function we(i){var p,P,R;ln(i),L.length===0&&((p=e.domElement)==null||p.releasePointerCapture(i.pointerId),(P=e.domElement)==null||P.ownerDocument.removeEventListener("pointermove",Ie),(R=e.domElement)==null||R.ownerDocument.removeEventListener("pointerup",we)),e.dispatchEvent(u),d=s.NONE}function nt(i){let p;switch(i.button){case 0:p=e.mouseButtons.LEFT;break;case 1:p=e.mouseButtons.MIDDLE;break;case 2:p=e.mouseButtons.RIGHT;break;default:p=-1}switch(p){case Ae.DOLLY:if(e.enableZoom===!1)return;he(i),d=s.DOLLY;break;case Ae.ROTATE:if(i.ctrlKey||i.metaKey||i.shiftKey){if(e.enablePan===!1)return;ze(i),d=s.PAN}else{if(e.enableRotate===!1)return;le(i),d=s.ROTATE}break;case Ae.PAN:if(i.ctrlKey||i.metaKey||i.shiftKey){if(e.enableRotate===!1)return;le(i),d=s.ROTATE}else{if(e.enablePan===!1)return;ze(i),d=s.PAN}break;default:d=s.NONE}d!==s.NONE&&e.dispatchEvent(a)}function ot(i){if(e.enabled!==!1)switch(d){case s.ROTATE:if(e.enableRotate===!1)return;Je(i);break;case s.DOLLY:if(e.enableZoom===!1)return;ge(i);break;case s.PAN:if(e.enablePan===!1)return;We(i);break}}function ie(i){e.enabled===!1||e.enableZoom===!1||d!==s.NONE&&d!==s.ROTATE||(i.preventDefault(),e.dispatchEvent(a),G(i),e.dispatchEvent(u))}function it(i){e.enabled===!1||e.enablePan===!1||D(i)}function rn(i){switch(wt(i),L.length){case 1:switch(e.touches.ONE){case _e.ROTATE:if(e.enableRotate===!1)return;ne(),d=s.TOUCH_ROTATE;break;case _e.PAN:if(e.enablePan===!1)return;ee(),d=s.TOUCH_PAN;break;default:d=s.NONE}break;case 2:switch(e.touches.TWO){case _e.DOLLY_PAN:if(e.enableZoom===!1&&e.enablePan===!1)return;Oe(),d=s.TOUCH_DOLLY_PAN;break;case _e.DOLLY_ROTATE:if(e.enableZoom===!1&&e.enableRotate===!1)return;et(),d=s.TOUCH_DOLLY_ROTATE;break;default:d=s.NONE}break;default:d=s.NONE}d!==s.NONE&&e.dispatchEvent(a)}function sn(i){switch(wt(i),d){case s.TOUCH_ROTATE:if(e.enableRotate===!1)return;oe(i),e.update();break;case s.TOUCH_PAN:if(e.enablePan===!1)return;je(i),e.update();break;case s.TOUCH_DOLLY_PAN:if(e.enableZoom===!1&&e.enablePan===!1)return;Ye(i),e.update();break;case s.TOUCH_DOLLY_ROTATE:if(e.enableZoom===!1&&e.enableRotate===!1)return;tt(i),e.update();break;default:d=s.NONE}}function xt(i){e.enabled!==!1&&i.preventDefault()}function an(i){L.push(i)}function ln(i){delete I[i.pointerId];for(let p=0;p<L.length;p++)if(L[p].pointerId==i.pointerId){L.splice(p,1);return}}function wt(i){let p=I[i.pointerId];p===void 0&&(p=new q,I[i.pointerId]=p),p.set(i.pageX,i.pageY)}function rt(i){const p=i.pointerId===L[0].pointerId?L[1]:L[0];return I[p.pointerId]}this.dollyIn=(i=K())=>{$(i),e.update()},this.dollyOut=(i=K())=>{Q(i),e.update()},this.getScale=()=>y,this.setScale=i=>{Z(i),e.update()},this.getZoomScale=()=>K(),n!==void 0&&this.connect(n),this.update()}};const It=new gt,Ze=new T;class vt extends Cn{constructor(){super(),this.isLineSegmentsGeometry=!0,this.type="LineSegmentsGeometry";const t=[-1,2,0,1,2,0,-1,1,0,1,1,0,-1,0,0,1,0,0,-1,-1,0,1,-1,0],n=[-1,2,1,2,-1,1,1,1,-1,-1,1,-1,-1,-2,1,-2],e=[0,2,1,2,3,1,2,4,3,4,5,3,4,6,5,6,7,5];this.setIndex(e),this.setAttribute("position",new At(t,3)),this.setAttribute("uv",new At(n,2))}applyMatrix4(t){const n=this.attributes.instanceStart,e=this.attributes.instanceEnd;return n!==void 0&&(n.applyMatrix4(t),e.applyMatrix4(t),n.needsUpdate=!0),this.boundingBox!==null&&this.computeBoundingBox(),this.boundingSphere!==null&&this.computeBoundingSphere(),this}setPositions(t){let n;t instanceof Float32Array?n=t:Array.isArray(t)&&(n=new Float32Array(t));const e=new pt(n,6,1);return this.setAttribute("instanceStart",new Re(e,3,0)),this.setAttribute("instanceEnd",new Re(e,3,3)),this.computeBoundingBox(),this.computeBoundingSphere(),this}setColors(t,n=3){let e;t instanceof Float32Array?e=t:Array.isArray(t)&&(e=new Float32Array(t));const r=new pt(e,n*2,1);return this.setAttribute("instanceColorStart",new Re(r,n,0)),this.setAttribute("instanceColorEnd",new Re(r,n,n)),this}fromWireframeGeometry(t){return this.setPositions(t.attributes.position.array),this}fromEdgesGeometry(t){return this.setPositions(t.attributes.position.array),this}fromMesh(t){return this.fromWireframeGeometry(new Tn(t.geometry)),this}fromLineSegments(t){const n=t.geometry;return this.setPositions(n.attributes.position.array),this}computeBoundingBox(){this.boundingBox===null&&(this.boundingBox=new gt);const t=this.attributes.instanceStart,n=this.attributes.instanceEnd;t!==void 0&&n!==void 0&&(this.boundingBox.setFromBufferAttribute(t),It.setFromBufferAttribute(n),this.boundingBox.union(It))}computeBoundingSphere(){this.boundingSphere===null&&(this.boundingSphere=new $t),this.boundingBox===null&&this.computeBoundingBox();const t=this.attributes.instanceStart,n=this.attributes.instanceEnd;if(t!==void 0&&n!==void 0){const e=this.boundingSphere.center;this.boundingBox.getCenter(e);let r=0;for(let a=0,u=t.count;a<u;a++)Ze.fromBufferAttribute(t,a),r=Math.max(r,e.distanceToSquared(Ze)),Ze.fromBufferAttribute(n,a),r=Math.max(r,e.distanceToSquared(Ze));this.boundingSphere.radius=Math.sqrt(r),isNaN(this.boundingSphere.radius)&&console.error("THREE.LineSegmentsGeometry.computeBoundingSphere(): Computed radius is NaN. The instanced position data is likely to have NaN values.",this)}}toJSON(){}applyMatrix(t){return console.warn("THREE.LineSegmentsGeometry: applyMatrix() has been renamed to applyMatrix4()."),this.applyMatrix4(t)}}class en extends vt{constructor(){super(),this.isLineGeometry=!0,this.type="LineGeometry"}setPositions(t){const n=t.length-3,e=new Float32Array(2*n);for(let r=0;r<n;r+=3)e[2*r]=t[r],e[2*r+1]=t[r+1],e[2*r+2]=t[r+2],e[2*r+3]=t[r+3],e[2*r+4]=t[r+4],e[2*r+5]=t[r+5];return super.setPositions(e),this}setColors(t,n=3){const e=t.length-n,r=new Float32Array(2*e);if(n===3)for(let a=0;a<e;a+=n)r[2*a]=t[a],r[2*a+1]=t[a+1],r[2*a+2]=t[a+2],r[2*a+3]=t[a+3],r[2*a+4]=t[a+4],r[2*a+5]=t[a+5];else for(let a=0;a<e;a+=n)r[2*a]=t[a],r[2*a+1]=t[a+1],r[2*a+2]=t[a+2],r[2*a+3]=t[a+3],r[2*a+4]=t[a+4],r[2*a+5]=t[a+5],r[2*a+6]=t[a+6],r[2*a+7]=t[a+7];return super.setColors(r,n),this}fromLine(t){const n=t.geometry;return this.setPositions(n.attributes.position.array),this}}class Et extends Rn{constructor(t){super({type:"LineMaterial",uniforms:_t.clone(_t.merge([Ct.common,Ct.fog,{worldUnits:{value:1},linewidth:{value:1},resolution:{value:new q(1,1)},dashOffset:{value:0},dashScale:{value:1},dashSize:{value:1},gapSize:{value:1}}])),vertexShader:`
				#include <common>
				#include <fog_pars_vertex>
				#include <logdepthbuf_pars_vertex>
				#include <clipping_planes_pars_vertex>

				uniform float linewidth;
				uniform vec2 resolution;

				attribute vec3 instanceStart;
				attribute vec3 instanceEnd;

				#ifdef USE_COLOR
					#ifdef USE_LINE_COLOR_ALPHA
						varying vec4 vLineColor;
						attribute vec4 instanceColorStart;
						attribute vec4 instanceColorEnd;
					#else
						varying vec3 vLineColor;
						attribute vec3 instanceColorStart;
						attribute vec3 instanceColorEnd;
					#endif
				#endif

				#ifdef WORLD_UNITS

					varying vec4 worldPos;
					varying vec3 worldStart;
					varying vec3 worldEnd;

					#ifdef USE_DASH

						varying vec2 vUv;

					#endif

				#else

					varying vec2 vUv;

				#endif

				#ifdef USE_DASH

					uniform float dashScale;
					attribute float instanceDistanceStart;
					attribute float instanceDistanceEnd;
					varying float vLineDistance;

				#endif

				void trimSegment( const in vec4 start, inout vec4 end ) {

					// trim end segment so it terminates between the camera plane and the near plane

					// conservative estimate of the near plane
					float a = projectionMatrix[ 2 ][ 2 ]; // 3nd entry in 3th column
					float b = projectionMatrix[ 3 ][ 2 ]; // 3nd entry in 4th column
					float nearEstimate = - 0.5 * b / a;

					float alpha = ( nearEstimate - start.z ) / ( end.z - start.z );

					end.xyz = mix( start.xyz, end.xyz, alpha );

				}

				void main() {

					#ifdef USE_COLOR

						vLineColor = ( position.y < 0.5 ) ? instanceColorStart : instanceColorEnd;

					#endif

					#ifdef USE_DASH

						vLineDistance = ( position.y < 0.5 ) ? dashScale * instanceDistanceStart : dashScale * instanceDistanceEnd;
						vUv = uv;

					#endif

					float aspect = resolution.x / resolution.y;

					// camera space
					vec4 start = modelViewMatrix * vec4( instanceStart, 1.0 );
					vec4 end = modelViewMatrix * vec4( instanceEnd, 1.0 );

					#ifdef WORLD_UNITS

						worldStart = start.xyz;
						worldEnd = end.xyz;

					#else

						vUv = uv;

					#endif

					// special case for perspective projection, and segments that terminate either in, or behind, the camera plane
					// clearly the gpu firmware has a way of addressing this issue when projecting into ndc space
					// but we need to perform ndc-space calculations in the shader, so we must address this issue directly
					// perhaps there is a more elegant solution -- WestLangley

					bool perspective = ( projectionMatrix[ 2 ][ 3 ] == - 1.0 ); // 4th entry in the 3rd column

					if ( perspective ) {

						if ( start.z < 0.0 && end.z >= 0.0 ) {

							trimSegment( start, end );

						} else if ( end.z < 0.0 && start.z >= 0.0 ) {

							trimSegment( end, start );

						}

					}

					// clip space
					vec4 clipStart = projectionMatrix * start;
					vec4 clipEnd = projectionMatrix * end;

					// ndc space
					vec3 ndcStart = clipStart.xyz / clipStart.w;
					vec3 ndcEnd = clipEnd.xyz / clipEnd.w;

					// direction
					vec2 dir = ndcEnd.xy - ndcStart.xy;

					// account for clip-space aspect ratio
					dir.x *= aspect;
					dir = normalize( dir );

					#ifdef WORLD_UNITS

						// get the offset direction as perpendicular to the view vector
						vec3 worldDir = normalize( end.xyz - start.xyz );
						vec3 offset;
						if ( position.y < 0.5 ) {

							offset = normalize( cross( start.xyz, worldDir ) );

						} else {

							offset = normalize( cross( end.xyz, worldDir ) );

						}

						// sign flip
						if ( position.x < 0.0 ) offset *= - 1.0;

						float forwardOffset = dot( worldDir, vec3( 0.0, 0.0, 1.0 ) );

						// don't extend the line if we're rendering dashes because we
						// won't be rendering the endcaps
						#ifndef USE_DASH

							// extend the line bounds to encompass  endcaps
							start.xyz += - worldDir * linewidth * 0.5;
							end.xyz += worldDir * linewidth * 0.5;

							// shift the position of the quad so it hugs the forward edge of the line
							offset.xy -= dir * forwardOffset;
							offset.z += 0.5;

						#endif

						// endcaps
						if ( position.y > 1.0 || position.y < 0.0 ) {

							offset.xy += dir * 2.0 * forwardOffset;

						}

						// adjust for linewidth
						offset *= linewidth * 0.5;

						// set the world position
						worldPos = ( position.y < 0.5 ) ? start : end;
						worldPos.xyz += offset;

						// project the worldpos
						vec4 clip = projectionMatrix * worldPos;

						// shift the depth of the projected points so the line
						// segments overlap neatly
						vec3 clipPose = ( position.y < 0.5 ) ? ndcStart : ndcEnd;
						clip.z = clipPose.z * clip.w;

					#else

						vec2 offset = vec2( dir.y, - dir.x );
						// undo aspect ratio adjustment
						dir.x /= aspect;
						offset.x /= aspect;

						// sign flip
						if ( position.x < 0.0 ) offset *= - 1.0;

						// endcaps
						if ( position.y < 0.0 ) {

							offset += - dir;

						} else if ( position.y > 1.0 ) {

							offset += dir;

						}

						// adjust for linewidth
						offset *= linewidth;

						// adjust for clip-space to screen-space conversion // maybe resolution should be based on viewport ...
						offset /= resolution.y;

						// select end
						vec4 clip = ( position.y < 0.5 ) ? clipStart : clipEnd;

						// back to clip space
						offset *= clip.w;

						clip.xy += offset;

					#endif

					gl_Position = clip;

					vec4 mvPosition = ( position.y < 0.5 ) ? start : end; // this is an approximation

					#include <logdepthbuf_vertex>
					#include <clipping_planes_vertex>
					#include <fog_vertex>

				}
			`,fragmentShader:`
				uniform vec3 diffuse;
				uniform float opacity;
				uniform float linewidth;

				#ifdef USE_DASH

					uniform float dashOffset;
					uniform float dashSize;
					uniform float gapSize;

				#endif

				varying float vLineDistance;

				#ifdef WORLD_UNITS

					varying vec4 worldPos;
					varying vec3 worldStart;
					varying vec3 worldEnd;

					#ifdef USE_DASH

						varying vec2 vUv;

					#endif

				#else

					varying vec2 vUv;

				#endif

				#include <common>
				#include <fog_pars_fragment>
				#include <logdepthbuf_pars_fragment>
				#include <clipping_planes_pars_fragment>

				#ifdef USE_COLOR
					#ifdef USE_LINE_COLOR_ALPHA
						varying vec4 vLineColor;
					#else
						varying vec3 vLineColor;
					#endif
				#endif

				vec2 closestLineToLine(vec3 p1, vec3 p2, vec3 p3, vec3 p4) {

					float mua;
					float mub;

					vec3 p13 = p1 - p3;
					vec3 p43 = p4 - p3;

					vec3 p21 = p2 - p1;

					float d1343 = dot( p13, p43 );
					float d4321 = dot( p43, p21 );
					float d1321 = dot( p13, p21 );
					float d4343 = dot( p43, p43 );
					float d2121 = dot( p21, p21 );

					float denom = d2121 * d4343 - d4321 * d4321;

					float numer = d1343 * d4321 - d1321 * d4343;

					mua = numer / denom;
					mua = clamp( mua, 0.0, 1.0 );
					mub = ( d1343 + d4321 * ( mua ) ) / d4343;
					mub = clamp( mub, 0.0, 1.0 );

					return vec2( mua, mub );

				}

				void main() {

					#include <clipping_planes_fragment>

					#ifdef USE_DASH

						if ( vUv.y < - 1.0 || vUv.y > 1.0 ) discard; // discard endcaps

						if ( mod( vLineDistance + dashOffset, dashSize + gapSize ) > dashSize ) discard; // todo - FIX

					#endif

					float alpha = opacity;

					#ifdef WORLD_UNITS

						// Find the closest points on the view ray and the line segment
						vec3 rayEnd = normalize( worldPos.xyz ) * 1e5;
						vec3 lineDir = worldEnd - worldStart;
						vec2 params = closestLineToLine( worldStart, worldEnd, vec3( 0.0, 0.0, 0.0 ), rayEnd );

						vec3 p1 = worldStart + lineDir * params.x;
						vec3 p2 = rayEnd * params.y;
						vec3 delta = p1 - p2;
						float len = length( delta );
						float norm = len / linewidth;

						#ifndef USE_DASH

							#ifdef USE_ALPHA_TO_COVERAGE

								float dnorm = fwidth( norm );
								alpha = 1.0 - smoothstep( 0.5 - dnorm, 0.5 + dnorm, norm );

							#else

								if ( norm > 0.5 ) {

									discard;

								}

							#endif

						#endif

					#else

						#ifdef USE_ALPHA_TO_COVERAGE

							// artifacts appear on some hardware if a derivative is taken within a conditional
							float a = vUv.x;
							float b = ( vUv.y > 0.0 ) ? vUv.y - 1.0 : vUv.y + 1.0;
							float len2 = a * a + b * b;
							float dlen = fwidth( len2 );

							if ( abs( vUv.y ) > 1.0 ) {

								alpha = 1.0 - smoothstep( 1.0 - dlen, 1.0 + dlen, len2 );

							}

						#else

							if ( abs( vUv.y ) > 1.0 ) {

								float a = vUv.x;
								float b = ( vUv.y > 0.0 ) ? vUv.y - 1.0 : vUv.y + 1.0;
								float len2 = a * a + b * b;

								if ( len2 > 1.0 ) discard;

							}

						#endif

					#endif

					vec4 diffuseColor = vec4( diffuse, alpha );
					#ifdef USE_COLOR
						#ifdef USE_LINE_COLOR_ALPHA
							diffuseColor *= vLineColor;
						#else
							diffuseColor.rgb *= vLineColor;
						#endif
					#endif

					#include <logdepthbuf_fragment>

					gl_FragColor = diffuseColor;

					#include <tonemapping_fragment>
					#include <${Vt>=154?"colorspace_fragment":"encodings_fragment"}>
					#include <fog_fragment>
					#include <premultiplied_alpha_fragment>

				}
			`,clipping:!0}),this.isLineMaterial=!0,this.onBeforeCompile=function(){this.transparent?this.defines.USE_LINE_COLOR_ALPHA="1":delete this.defines.USE_LINE_COLOR_ALPHA},Object.defineProperties(this,{color:{enumerable:!0,get:function(){return this.uniforms.diffuse.value},set:function(n){this.uniforms.diffuse.value=n}},worldUnits:{enumerable:!0,get:function(){return"WORLD_UNITS"in this.defines},set:function(n){n===!0?this.defines.WORLD_UNITS="":delete this.defines.WORLD_UNITS}},linewidth:{enumerable:!0,get:function(){return this.uniforms.linewidth.value},set:function(n){this.uniforms.linewidth.value=n}},dashed:{enumerable:!0,get:function(){return"USE_DASH"in this.defines},set(n){!!n!="USE_DASH"in this.defines&&(this.needsUpdate=!0),n===!0?this.defines.USE_DASH="":delete this.defines.USE_DASH}},dashScale:{enumerable:!0,get:function(){return this.uniforms.dashScale.value},set:function(n){this.uniforms.dashScale.value=n}},dashSize:{enumerable:!0,get:function(){return this.uniforms.dashSize.value},set:function(n){this.uniforms.dashSize.value=n}},dashOffset:{enumerable:!0,get:function(){return this.uniforms.dashOffset.value},set:function(n){this.uniforms.dashOffset.value=n}},gapSize:{enumerable:!0,get:function(){return this.uniforms.gapSize.value},set:function(n){this.uniforms.gapSize.value=n}},opacity:{enumerable:!0,get:function(){return this.uniforms.opacity.value},set:function(n){this.uniforms.opacity.value=n}},resolution:{enumerable:!0,get:function(){return this.uniforms.resolution.value},set:function(n){this.uniforms.resolution.value.copy(n)}},alphaToCoverage:{enumerable:!0,get:function(){return"USE_ALPHA_TO_COVERAGE"in this.defines},set:function(n){!!n!="USE_ALPHA_TO_COVERAGE"in this.defines&&(this.needsUpdate=!0),n===!0?(this.defines.USE_ALPHA_TO_COVERAGE="",this.extensions.derivatives=!0):(delete this.defines.USE_ALPHA_TO_COVERAGE,this.extensions.derivatives=!1)}}}),this.setValues(t)}}const at=new De,Bt=new T,Ut=new T,F=new De,W=new De,re=new De,lt=new T,ct=new qt,Y=new zn,kt=new T,$e=new gt,qe=new $t,se=new De;let ae,Se;function Nt(o,t,n){return se.set(0,0,-t,1).applyMatrix4(o.projectionMatrix),se.multiplyScalar(1/se.w),se.x=Se/n.width,se.y=Se/n.height,se.applyMatrix4(o.projectionMatrixInverse),se.multiplyScalar(1/se.w),Math.abs(Math.max(se.x,se.y))}function Eo(o,t){const n=o.matrixWorld,e=o.geometry,r=e.attributes.instanceStart,a=e.attributes.instanceEnd,u=Math.min(e.instanceCount,r.count);for(let s=0,d=u;s<d;s++){Y.start.fromBufferAttribute(r,s),Y.end.fromBufferAttribute(a,s),Y.applyMatrix4(n);const M=new T,f=new T;ae.distanceSqToSegment(Y.start,Y.end,f,M),f.distanceTo(M)<Se*.5&&t.push({point:f,pointOnLine:M,distance:ae.origin.distanceTo(f),object:o,face:null,faceIndex:s,uv:null,[Jt]:null})}}function bo(o,t,n){const e=t.projectionMatrix,a=o.material.resolution,u=o.matrixWorld,s=o.geometry,d=s.attributes.instanceStart,M=s.attributes.instanceEnd,f=Math.min(s.instanceCount,d.count),m=-t.near;ae.at(1,re),re.w=1,re.applyMatrix4(t.matrixWorldInverse),re.applyMatrix4(e),re.multiplyScalar(1/re.w),re.x*=a.x/2,re.y*=a.y/2,re.z=0,lt.copy(re),ct.multiplyMatrices(t.matrixWorldInverse,u);for(let y=0,v=f;y<v;y++){if(F.fromBufferAttribute(d,y),W.fromBufferAttribute(M,y),F.w=1,W.w=1,F.applyMatrix4(ct),W.applyMatrix4(ct),F.z>m&&W.z>m)continue;if(F.z>m){const b=F.z-W.z,E=(F.z-m)/b;F.lerp(W,E)}else if(W.z>m){const b=W.z-F.z,E=(W.z-m)/b;W.lerp(F,E)}F.applyMatrix4(e),W.applyMatrix4(e),F.multiplyScalar(1/F.w),W.multiplyScalar(1/W.w),F.x*=a.x/2,F.y*=a.y/2,W.x*=a.x/2,W.y*=a.y/2,Y.start.copy(F),Y.start.z=0,Y.end.copy(W),Y.end.z=0;const h=Y.closestPointToPointParameter(lt,!0);Y.at(h,kt);const g=jn.lerp(F.z,W.z,h),S=g>=-1&&g<=1,C=lt.distanceTo(kt)<Se*.5;if(S&&C){Y.start.fromBufferAttribute(d,y),Y.end.fromBufferAttribute(M,y),Y.start.applyMatrix4(u),Y.end.applyMatrix4(u);const b=new T,E=new T;ae.distanceSqToSegment(Y.start,Y.end,E,b),n.push({point:E,pointOnLine:b,distance:ae.origin.distanceTo(E),object:o,face:null,faceIndex:y,uv:null,[Jt]:null})}}}class tn extends Dn{constructor(t=new vt,n=new Et({color:Math.random()*16777215})){super(t,n),this.isLineSegments2=!0,this.type="LineSegments2"}computeLineDistances(){const t=this.geometry,n=t.attributes.instanceStart,e=t.attributes.instanceEnd,r=new Float32Array(2*n.count);for(let u=0,s=0,d=n.count;u<d;u++,s+=2)Bt.fromBufferAttribute(n,u),Ut.fromBufferAttribute(e,u),r[s]=s===0?0:r[s-1],r[s+1]=r[s]+Bt.distanceTo(Ut);const a=new pt(r,2,1);return t.setAttribute("instanceDistanceStart",new Re(a,1,0)),t.setAttribute("instanceDistanceEnd",new Re(a,1,1)),this}raycast(t,n){const e=this.material.worldUnits,r=t.camera;r===null&&!e&&console.error('LineSegments2: "Raycaster.camera" needs to be set in order to raycast against LineSegments2 while worldUnits is set to false.');const a=t.params.Line2!==void 0&&t.params.Line2.threshold||0;ae=t.ray;const u=this.matrixWorld,s=this.geometry,d=this.material;Se=d.linewidth+a,s.boundingSphere===null&&s.computeBoundingSphere(),qe.copy(s.boundingSphere).applyMatrix4(u);let M;if(e)M=Se*.5;else{const m=Math.max(r.near,qe.distanceToPoint(ae.origin));M=Nt(r,m,d.resolution)}if(qe.radius+=M,ae.intersectsSphere(qe)===!1)return;s.boundingBox===null&&s.computeBoundingBox(),$e.copy(s.boundingBox).applyMatrix4(u);let f;if(e)f=Se*.5;else{const m=Math.max(r.near,$e.distanceToPoint(ae.origin));f=Nt(r,m,d.resolution)}$e.expandByScalar(f),ae.intersectsBox($e)!==!1&&(e?Eo(this,n):bo(this,r,n))}onBeforeRender(t){const n=this.material.uniforms;n&&n.resolution&&(t.getViewport(at),this.material.uniforms.resolution.value.set(at.z,at.w))}}class xo extends tn{constructor(t=new en,n=new Et({color:Math.random()*16777215})){super(t,n),this.isLine2=!0,this.type="Line2"}}const nn=l.forwardRef(function({points:t,color:n=16777215,vertexColors:e,linewidth:r,lineWidth:a,segments:u,dashed:s,...d},M){var f,m;const y=z(S=>S.size),v=l.useMemo(()=>u?new tn:new xo,[u]),[O]=l.useState(()=>new Et),h=(e==null||(f=e[0])==null?void 0:f.length)===4?4:3,g=l.useMemo(()=>{const S=u?new vt:new en,C=t.map(b=>{const E=Array.isArray(b);return b instanceof T||b instanceof De?[b.x,b.y,b.z]:b instanceof q?[b.x,b.y,0]:E&&b.length===3?[b[0],b[1],b[2]]:E&&b.length===2?[b[0],b[1],0]:b});if(S.setPositions(C.flat()),e){n=16777215;const b=e.map(E=>E instanceof In?E.toArray():E);S.setColors(b.flat(),h)}return S},[t,u,e,h]);return l.useLayoutEffect(()=>{v.computeLineDistances()},[t,v]),l.useLayoutEffect(()=>{s?O.defines.USE_DASH="":delete O.defines.USE_DASH,O.needsUpdate=!0},[s,O]),l.useEffect(()=>()=>{g.dispose(),O.dispose()},[g]),l.createElement("primitive",V({object:v,ref:M},d),l.createElement("primitive",{object:g,attach:"geometry"}),l.createElement("primitive",V({object:O,attach:"material",color:n,vertexColors:!!e,resolution:[y.width,y.height],linewidth:(m=r??a)!==null&&m!==void 0?m:1,dashed:s,transparent:h===4},d)))});function wo(o,t,n){const e=z(v=>v.size),r=z(v=>v.viewport),a=typeof o=="number"?o:e.width*r.dpr,u=e.height*r.dpr,s=(typeof o=="number"?n:o)||{},{samples:d=0,depth:M,...f}=s,m=M??s.depthBuffer,y=l.useMemo(()=>{const v=new Bn(a,u,{minFilter:Tt,magFilter:Tt,type:Un,...f});return m&&(v.depthTexture=new kn(a,u,Nn)),v.samples=d,v},[]);return l.useLayoutEffect(()=>{y.setSize(a,u),d&&(y.samples=d)},[d,y,a,u]),l.useEffect(()=>()=>y.dispose(),[]),y}const So=o=>typeof o=="function",Mo=l.forwardRef(({envMap:o,resolution:t=256,frames:n=1/0,children:e,makeDefault:r,...a},u)=>{const s=z(({set:g})=>g),d=z(({camera:g})=>g),M=z(({size:g})=>g),f=l.useRef(null);l.useImperativeHandle(u,()=>f.current,[]);const m=l.useRef(null),y=wo(t);l.useLayoutEffect(()=>{a.manual||f.current.updateProjectionMatrix()},[M,a]),l.useLayoutEffect(()=>{f.current.updateProjectionMatrix()}),l.useLayoutEffect(()=>{if(r){const g=d;return s(()=>({camera:f.current})),()=>s(()=>({camera:g}))}},[f,r,s]);let v=0,O=null;const h=So(e);return Me(g=>{h&&(n===1/0||v<n)&&(m.current.visible=!1,g.gl.setRenderTarget(y),O=g.scene.background,o&&(g.scene.background=o),g.gl.render(g.scene,f.current),g.scene.background=O,g.gl.setRenderTarget(null),m.current.visible=!0,v++)}),l.createElement(l.Fragment,null,l.createElement("orthographicCamera",V({left:M.width/-2,right:M.width/2,top:M.height/2,bottom:M.height/-2,ref:f},a),!h&&e),l.createElement("group",{ref:m},h&&e(y.texture)))}),Po=l.forwardRef(({makeDefault:o,camera:t,regress:n,domElement:e,enableDamping:r=!0,keyEvents:a=!1,onChange:u,onStart:s,onEnd:d,...M},f)=>{const m=z(x=>x.invalidate),y=z(x=>x.camera),v=z(x=>x.gl),O=z(x=>x.events),h=z(x=>x.setEvents),g=z(x=>x.set),S=z(x=>x.get),C=z(x=>x.performance),b=t||y,E=e||O.connected||v.domElement,A=l.useMemo(()=>new vo(b),[b]);return Me(()=>{A.enabled&&A.update()},-1),l.useEffect(()=>(a&&A.connect(a===!0?E:a),A.connect(E),()=>void A.dispose()),[a,E,n,A,m]),l.useEffect(()=>{const x=_=>{m(),n&&C.regress(),u&&u(_)},X=_=>{s&&s(_)},j=_=>{d&&d(_)};return A.addEventListener("change",x),A.addEventListener("start",X),A.addEventListener("end",j),()=>{A.removeEventListener("start",X),A.removeEventListener("end",j),A.removeEventListener("change",x)}},[u,s,d,A,m,h]),l.useEffect(()=>{if(o){const x=S().controls;return g({controls:A}),()=>g({controls:x})}},[o,A]),l.createElement("primitive",V({ref:f,object:A,enableDamping:r},M))});function Oo({defaultScene:o,defaultCamera:t,renderPriority:n=1}){const{gl:e,scene:r,camera:a}=z();let u;return Me(()=>{u=e.autoClear,n===1&&(e.autoClear=!0,e.render(o,t)),e.autoClear=!1,e.clearDepth(),e.render(r,a),e.autoClear=u},n),l.createElement("group",{onPointerOver:()=>null})}function Lo({children:o,renderPriority:t=1}){const{scene:n,camera:e}=z(),[r]=l.useState(()=>new Hn);return l.createElement(l.Fragment,null,Fn(l.createElement(l.Fragment,null,o,l.createElement(Oo,{defaultScene:n,defaultCamera:e,renderPriority:t})),r,{events:{priority:t+1}}))}const on=l.createContext({}),Ao=()=>l.useContext(on),_o=2*Math.PI,ut=new Wn,Ht=new qt,[Ce,dt]=[new Ke,new Ke],Ft=new T,Wt=new T,Co=o=>"minPolarAngle"in o,Yt=o=>"getTarget"in o,To=({alignment:o="bottom-right",margin:t=[80,80],renderPriority:n=1,onUpdate:e,onTarget:r,children:a})=>{const u=z(x=>x.size),s=z(x=>x.camera),d=z(x=>x.controls),M=z(x=>x.invalidate),f=l.useRef(null),m=l.useRef(null),y=l.useRef(!1),v=l.useRef(0),O=l.useRef(new T(0,0,0)),h=l.useRef(new T(0,0,0));l.useEffect(()=>{h.current.copy(s.up),ut.up.copy(s.up)},[s]);const g=l.useCallback(x=>{y.current=!0,(d||r)&&(O.current=(r==null?void 0:r())||(Yt(d)?d.getTarget(O.current):d==null?void 0:d.target)),v.current=s.position.distanceTo(Ft),Ce.copy(s.quaternion),Wt.copy(x).multiplyScalar(v.current).add(Ft),ut.lookAt(Wt),dt.copy(ut.quaternion),M()},[d,s,r,M]);Me((x,X)=>{if(m.current&&f.current){var j;if(y.current)if(Ce.angleTo(dt)<.01)y.current=!1,Co(d)&&s.up.copy(h.current);else{const _=X*_o;Ce.rotateTowards(dt,_),s.position.set(0,0,1).applyQuaternion(Ce).multiplyScalar(v.current).add(O.current),s.up.set(0,1,0).applyQuaternion(Ce).normalize(),s.quaternion.copy(Ce),Yt(d)&&d.setPosition(s.position.x,s.position.y,s.position.z),e?e():d&&d.update(X),M()}Ht.copy(s.matrix).invert(),(j=f.current)==null||j.quaternion.setFromRotationMatrix(Ht)}});const S=l.useMemo(()=>({tweenCamera:g}),[g]),[C,b]=t,E=o.endsWith("-center")?0:o.endsWith("-left")?-u.width/2+C:u.width/2-C,A=o.startsWith("center-")?0:o.startsWith("top-")?u.height/2-b:-u.height/2+b;return l.createElement(Lo,{renderPriority:n},l.createElement(on.Provider,{value:S},l.createElement(Mo,{makeDefault:!0,ref:m,position:[0,0,200]}),l.createElement("group",{ref:f,position:[E,A,0]},a)))};function ft({scale:o=[.8,.05,.05],color:t,rotation:n}){return l.createElement("group",{rotation:n},l.createElement("mesh",{position:[.4,0,0]},l.createElement("boxGeometry",{args:o}),l.createElement("meshBasicMaterial",{color:t,toneMapped:!1})))}function Te({onClick:o,font:t,disabled:n,arcStyle:e,label:r,labelColor:a,axisHeadScale:u=1,...s}){const d=z(h=>h.gl),M=l.useMemo(()=>{const h=document.createElement("canvas");h.width=64,h.height=64;const g=h.getContext("2d");return g.beginPath(),g.arc(32,32,16,0,2*Math.PI),g.closePath(),g.fillStyle=e,g.fill(),r&&(g.font=t,g.textAlign="center",g.fillStyle=a,g.fillText(r,32,41)),new Yn(h)},[e,r,a,t]),[f,m]=l.useState(!1),y=(r?1:.75)*(f?1.2:1)*u,v=h=>{h.stopPropagation(),m(!0)},O=h=>{h.stopPropagation(),m(!1)};return l.createElement("sprite",V({scale:y,onPointerOver:n?void 0:v,onPointerOut:n?void 0:o||O},s),l.createElement("spriteMaterial",{map:M,"map-anisotropy":d.capabilities.getMaxAnisotropy()||1,alphaTest:.3,opacity:r?1:.75,toneMapped:!1}))}const Ro=({hideNegativeAxes:o,hideAxisHeads:t,disabled:n,font:e="18px Inter var, Arial, sans-serif",axisColors:r=["#ff2060","#20df80","#2080ff"],axisHeadScale:a=1,axisScale:u,labels:s=["X","Y","Z"],labelColor:d="#000",onClick:M,...f})=>{const[m,y,v]=r,{tweenCamera:O}=Ao(),h={font:e,disabled:n,labelColor:d,onClick:M,axisHeadScale:a,onPointerDown:n?void 0:g=>{O(g.object.position),g.stopPropagation()}};return l.createElement("group",V({scale:40},f),l.createElement(ft,{color:m,rotation:[0,0,0],scale:u}),l.createElement(ft,{color:y,rotation:[0,0,Math.PI/2],scale:u}),l.createElement(ft,{color:v,rotation:[0,-Math.PI/2,0],scale:u}),!t&&l.createElement(l.Fragment,null,l.createElement(Te,V({arcStyle:m,position:[1,0,0],label:s[0]},h)),l.createElement(Te,V({arcStyle:y,position:[0,1,0],label:s[1]},h)),l.createElement(Te,V({arcStyle:v,position:[0,0,1],label:s[2]},h)),!o&&l.createElement(l.Fragment,null,l.createElement(Te,V({arcStyle:m,position:[-1,0,0]},h)),l.createElement(Te,V({arcStyle:y,position:[0,-1,0]},h)),l.createElement(Te,V({arcStyle:v,position:[0,0,-1]},h)))))},Do=-4.9,zo=l.memo(function({organ:t,selected:n,choose:e,severity:r,targets:a,planes:u,reduced:s,dim:d,showLabels:M,onHover:f,demoImagingOpen:m}){const y=Gn(),v=l.useMemo(()=>{var E;return((E=y[t.id])==null?void 0:E.clone())||Vn(t)},[t,y]),O=l.useRef(),[h,g]=l.useState(!1);c.useEffect(()=>()=>v.dispose(),[v]);const S=r==="none"?t.color:mt[r],C=n||r==="danger";Me(({clock:E})=>{O.current&&(O.current.emissiveIntensity=r==="danger"&&!s?.22+.12*Math.sin(E.elapsedTime*2):r==="none"?.02:.18)});const b=l.useMemo(()=>[...(a||[]).flatMap(A=>A.sources.filter(x=>x.type==="lab"))].sort((A,x)=>(A.date||"").localeCompare(x.date||"")).at(-1),[a]);return c.createElement("group",{position:t.p},c.createElement("mesh",{name:t.id,scale:t.s,geometry:v,onClick:E=>{E.stopPropagation(),e(t.id)},onDoubleClick:E=>{E.stopPropagation(),e(t.id)},onPointerOver:E=>{E.stopPropagation(),g(!0),f==null||f(t.id)},onPointerOut:E=>{g(!1),f==null||f(null)}},c.createElement("meshStandardMaterial",{ref:O,color:S,emissive:S,roughness:.63,transparent:!0,opacity:n?.94:d?.2:.46,depthWrite:n,side:be,clippingPlanes:u})),(n||h)&&c.createElement("mesh",{scale:t.s.map(E=>E*1.05),geometry:v,raycast:()=>null},c.createElement("meshBasicMaterial",{color:n?"#a8f9ed":"#eaf6ff",transparent:!0,opacity:n?.2:.15,wireframe:!0,clippingPlanes:u})),!n&&r==="caution"&&c.createElement("mesh",{scale:t.s.map(E=>E*1.028),geometry:v,raycast:()=>null},c.createElement("meshBasicMaterial",{color:mt.caution,transparent:!0,opacity:.17,wireframe:!0,clippingPlanes:u})),C&&c.createElement(c.Fragment,null,c.createElement(nn,{points:[[0,0,0],[.55,.3,.2],[.95,.3,.2]],color:S,lineWidth:1}),c.createElement(st,{position:[.96,.3,.2],style:{pointerEvents:"none"},distanceFactor:9},c.createElement("div",{className:"an-marker"},c.createElement("b",null,t.en),c.createElement("span",null,t.ko," · ",pn[r])))),!C&&h&&c.createElement(st,{position:[0,t.s[1]*1.2+.12,0],style:{pointerEvents:"none"},distanceFactor:9},c.createElement("div",{className:"an-tooltip"},c.createElement("b",null,t.ko),c.createElement("small",null,t.en),c.createElement("span",null,"Clinical signals: ",(a||[]).length),b&&c.createElement("span",null,"Latest related lab: ",b.name),c.createElement("span",null,"Imaging: ",m?"데모 참고 영상":"참고 영상 없음"))),!C&&!h&&M&&c.createElement(st,{position:[0,t.s[1]*1.15+.08,0],style:{pointerEvents:"none"},distanceFactor:9},c.createElement("div",{className:"an-label"},t.ko)))}),bt="#d9b593",Ee="#eee7d8";function N({shape:o,args:t,position:n,rotation:e,planes:r,opacity:a=.11,color:u=bt}){return c.createElement("mesh",{position:n,rotation:e,raycast:()=>null},o==="sphere"&&c.createElement("sphereGeometry",{args:t}),o==="cylinder"&&c.createElement("cylinderGeometry",{args:t}),o==="box"&&c.createElement("boxGeometry",{args:t}),o==="torus"&&c.createElement("torusGeometry",{args:t}),c.createElement("meshPhysicalMaterial",{color:u,transparent:!0,opacity:a,roughness:.38,depthWrite:!1,clippingPlanes:r,side:be}))}function jo({profile:o,planes:t,opacity:n}){const e=l.useMemo(()=>Xn(o.torso),[o]);return c.useEffect(()=>()=>e.dispose(),[e]),c.createElement("mesh",{geometry:e,scale:[1,1,o.depthRatio],raycast:()=>null},c.createElement("meshPhysicalMaterial",{color:bt,transparent:!0,opacity:n,roughness:.36,depthWrite:!1,clippingPlanes:t,side:be}))}function Io({planes:o,opacity:t}){const n=Qe();return c.createElement("group",{position:me.position,rotation:me.rotation,scale:me.scale},c.createElement("mesh",{name:"skinBody",geometry:n.skinBody,raycast:()=>null},c.createElement("meshPhysicalMaterial",{color:bt,transparent:!0,opacity:t,roughness:.36,depthWrite:!1,clippingPlanes:o,side:be})))}function Xt({side:o,planes:t,limbScale:n,shoulderX:e,hipX:r}){const a=o,u=n,s=e/1.22,d=r/.55;return c.createElement("group",null,c.createElement(N,{shape:"sphere",args:[.19*u,16,12],position:[a*1.22*s,2.02,-.05],planes:t}),c.createElement(N,{shape:"cylinder",args:[.18*u,.15*u,1.05,16],position:[a*1.28*s,1.45,-.03],rotation:[0,0,a*-.09],planes:t}),c.createElement(N,{shape:"sphere",args:[.15*u,16,12],position:[a*1.34*s,.9,0],planes:t}),c.createElement(N,{shape:"cylinder",args:[.14*u,.105*u,1,16],position:[a*1.3*s,.35,.02],rotation:[0,0,a*-.05],planes:t}),c.createElement(N,{shape:"sphere",args:[.14*u,16,12],position:[a*1.27*s,-.28,.05],planes:t}),c.createElement(N,{shape:"sphere",args:[.26*u,16,12],position:[a*.52*d,-1.55,-.05],planes:t}),c.createElement(N,{shape:"cylinder",args:[.27*u,.21*u,1.55,16],position:[a*.55*d,-2.35,-.05],planes:t}),c.createElement(N,{shape:"sphere",args:[.19*u,16,12],position:[a*.56*d,-3.12,-.03],planes:t}),c.createElement(N,{shape:"cylinder",args:[.19*u,.13*u,1.5,16],position:[a*.57*d,-3.9,0],planes:t}),c.createElement(N,{shape:"box",args:[.28*u,.16*u,.62*u],position:[a*.58*d,-4.68,.22],planes:t}))}function Bo({planes:o,profile:t}){const n=t.shoulderX/1.22,e=t.hipX/.55;return c.createElement("group",null,c.createElement(N,{shape:"sphere",args:[.42*t.headScale,16,12],position:[0,3.46,.02],color:Ee,opacity:.5,planes:o}),[2.35,2,1.65,1.3].map((r,a)=>c.createElement(N,{key:r,shape:"torus",args:[.6-a*.03,.045,8,20],position:[0,r,-.05],rotation:[Math.PI/2,0,0],color:Ee,opacity:.55,planes:o})),c.createElement(N,{shape:"torus",args:[.48,.08,8,20],position:[0,-1.55,-.05],rotation:[Math.PI/2,0,0],color:Ee,opacity:.55,planes:o}),[-1,1].map(r=>c.createElement("group",{key:r},c.createElement(N,{shape:"cylinder",args:[.055,.05,1,10],position:[r*1.28*n,1.45,-.03],rotation:[0,0,r*-.09],color:Ee,opacity:.6,planes:o}),c.createElement(N,{shape:"cylinder",args:[.045,.04,.95,10],position:[r*1.3*n,.4,.02],rotation:[0,0,r*-.05],color:Ee,opacity:.6,planes:o}),c.createElement(N,{shape:"cylinder",args:[.09,.07,1.5,10],position:[r*.55*e,-2.35,-.05],color:Ee,opacity:.6,planes:o}),c.createElement(N,{shape:"cylinder",args:[.07,.05,1.45,10],position:[r*.57*e,-3.9,0],color:Ee,opacity:.6,planes:o}))))}function Uo({planes:o,profile:t}){const n=Qe();return n.skeletonFull?c.createElement("group",{position:me.position,rotation:me.rotation,scale:me.scale},c.createElement("mesh",{geometry:n.skeletonFull,raycast:()=>null},c.createElement("meshStandardMaterial",{color:Ee,roughness:.55,transparent:!0,opacity:.7,depthWrite:!1,clippingPlanes:o,side:be}))):c.createElement(Bo,{planes:o,profile:t})}function ko({planes:o}){const t=Qe();return t.vascularFull?c.createElement("group",{position:me.position,rotation:me.rotation,scale:me.scale},c.createElement("mesh",{geometry:t.vascularFull,raycast:()=>null},c.createElement("meshStandardMaterial",{color:"#a83f4d",roughness:.5,transparent:!0,opacity:.4,depthWrite:!1,clippingPlanes:o,side:be}))):null}function No({selected:o,choose:t,hidden:n,data:e,planes:r,reduced:a,sex:u,bodyOpacity:s,showLabels:d,onHoverOrgan:M,demoImagingOpen:f}){const m=mn[u||"unspecified"],y=Math.min(1,Math.max(0,(s??55)/100)),v=Qe(),O=v.skinBody?fn[u||"unspecified"]:1;return c.createElement("group",{position:[0,Do*(1-O),0],scale:O},!n.body&&(v.skinBody?c.createElement(Io,{planes:r,opacity:y}):c.createElement(c.Fragment,null,c.createElement(jo,{profile:m,planes:r,opacity:y}),c.createElement(N,{shape:"sphere",args:[.58*m.headScale,32,24],position:[0,3.5,.04],opacity:y,planes:r}),c.createElement(N,{shape:"cylinder",args:[.2,.28,.5,24],position:[0,2.92,-.05],opacity:y,planes:r}),c.createElement(Xt,{side:-1,planes:r,limbScale:m.limbScale,shoulderX:m.shoulderX,hipX:m.hipX}),c.createElement(Xt,{side:1,planes:r,limbScale:m.limbScale,shoulderX:m.shoulderX,hipX:m.hipX}))),!n.skeleton&&c.createElement(Uo,{planes:r,profile:m}),!n.vascularFull&&c.createElement(ko,{planes:r}),Gt.filter(h=>!n[h.id]).map(h=>{const g=Pt(e,h.group);return c.createElement(zo,{key:h.id,organ:h,selected:o===h.id,dim:!!o&&o!==h.id,choose:t,severity:Ot(g),targets:g,planes:r,reduced:a,showLabels:d,onHover:M,demoImagingOpen:f})}),!n.spine&&Array.from({length:18},(h,g)=>c.createElement("mesh",{key:g,position:[0,-1.49+g*.218,-.56],raycast:()=>null},c.createElement("cylinderGeometry",{args:[.2,.19,.15,12]}),c.createElement("meshStandardMaterial",{color:"#c2ced0",transparent:!0,opacity:o==="spine"?.9:.25,clippingPlanes:r}))),!n.vascular&&[-1,1].map(h=>c.createElement(nn,{key:h,points:[[0,-.25,-.1],[h*.3,-.3,-.15],[h*.6,-.36,-.22]],color:mt[Ot(Pt(e,"systemic"))],lineWidth:3})))}class Ho extends c.Component{constructor(){super(...arguments);Mt(this,"state",{failed:!1})}static getDerivedStateFromError(){return{failed:!0}}render(){return this.state.failed?c.createElement("div",{className:"an-fallback"},"3D rendering is unavailable on this device.",c.createElement("br",null),"장기 목록에서 관련 근거를 확인할 수 있습니다."):this.props.children}}function Fo(o){const{mode:t,position:n,clipping:e,view:r,selected:a,reduced:u}=o,s=l.useRef(),d=l.useRef(null),{camera:M,gl:f}=z(),m=hn[t],y=gn(t,n),v=l.useMemo(()=>new T(...[0,1,2].map(S=>S===m?-1:0)),[m]),O=l.useMemo(()=>e?[new Zt(v,y)]:[],[e,v,y]),h=[0,0,0];h[m]=y;const g=t==="axial"?[-Math.PI/2,0,0]:t==="sagittal"?[0,Math.PI/2,0]:[0,0,0];return l.useEffect(()=>{f.localClippingEnabled=!0},[f]),l.useEffect(()=>{var b;const S=new T(...r.kind==="focus"?((b=Gt.find(E=>E.id===a))==null?void 0:b.p)||[0,.8,0]:[0,.8,0]),C={front:[0,0,9],back:[0,0,-9],left:[9,0,0],right:[-9,0,0],top:[0,9,.01],reset:[3,1.4,9],focus:[0,.2,4.4]};d.current={target:S,position:S.clone().add(new T(...C[r.kind]||C.reset))}},[r,a]),Me((S,C)=>{const b=d.current;if(!b||!s.current)return;const E=u?1:1-Math.exp(-C*7);M.position.lerp(b.position,E),s.current.target.lerp(b.target,E),s.current.update(),M.position.distanceTo(b.position)<.01&&(d.current=null)}),c.createElement(c.Fragment,null,c.createElement("color",{attach:"background",args:["#0c1a25"]}),c.createElement("ambientLight",{intensity:1.1}),c.createElement("directionalLight",{position:[3,5,5],intensity:2}),c.createElement("directionalLight",{position:[-4,2,-3],color:"#84cadc",intensity:1.5}),c.createElement(No,{...o,planes:O}),c.createElement("mesh",{position:h,rotation:g,raycast:()=>null},c.createElement("planeGeometry",{args:t==="axial"?[3.6,2.2]:[t==="sagittal"?2.2:3.6,7.6]}),c.createElement("meshBasicMaterial",{color:"#6bd5ca",transparent:!0,opacity:.12,side:be,depthWrite:!1})),c.createElement("gridHelper",{args:[8,16,"#284452","#182f3b"],position:[0,-1.95,0]}),c.createElement(Po,{ref:s,makeDefault:!0,minDistance:2,maxDistance:16,enableDamping:!u,onStart:()=>{d.current=null}}),c.createElement(To,{alignment:"bottom-right",margin:[48,48]},c.createElement(Ro,{axisColors:["#7d9ea9","#7d9ea9","#7d9ea9"],labelColor:"#07121b"})))}function Zo(o){const[t,n]=l.useState(!1);return c.createElement(Ho,null,t?c.createElement("div",{className:"an-fallback"},"3D rendering is unavailable on this device.",c.createElement("button",{onClick:()=>n(!1)},"다시 시도")):c.createElement(eo,{dpr:[1,1.5],camera:{position:[3,2.2,9],fov:43},gl:{antialias:!0,localClippingEnabled:!0},fallback:c.createElement("div",{className:"an-fallback"},"3D rendering is unavailable on this device."),onCreated:({gl:e})=>{e.domElement.addEventListener("webglcontextlost",r=>{r.preventDefault(),n(!0)},{once:!0})}},c.createElement(Fo,{...o})))}export{Zo as default};

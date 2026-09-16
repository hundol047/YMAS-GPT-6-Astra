var cn=Object.defineProperty;var un=(o,t,n)=>t in o?cn(o,t,{enumerable:!0,configurable:!0,writable:!0,value:n}):o[t]=n;var Mt=(o,t,n)=>un(o,typeof t!="symbol"?t+"":t,n);import{r as l,k as dn,m as fn,R as c,B as mn,o as Xt,t as Pt,s as Ot,b as mt,n as me,a as pn,l as hn,d as gn,e as yn}from"./index-BPmYeoGM.js";import{j as fe,m as vn,e as En,u as bn,a as xn,b as wn,c as Sn,d as Mn,i as Pn,E as On,B as Ln,f as An,T as _n,g as j,h as Me,V as C,D as be,k as q,P as Ne,O as Fe,v as Vt,S as Lt,Q as Ke,M as Ae,l as _e,R as Tn,n as Zt,I as Cn,F as At,o as pt,p as Re,W as Rn,q as gt,r as $t,s as Dn,U as _t,t as Tt,w as zn,x as De,L as jn,y as qt,z as In,C as Un,A as Bn,H as kn,G as Ct,J as Nn,K as Fn,N as Hn,X as Wn,Y as Yn,Z as Gn,_ as Qe,$ as Xn,a0 as Vn,a1 as Zn}from"./AnatomyWorkspace-C67XdoEw.js";function V(){return V=Object.assign?Object.assign.bind():function(o){for(var t=1;t<arguments.length;t++){var n=arguments[t];for(var e in n)({}).hasOwnProperty.call(n,e)&&(o[e]=n[e])}return o},V.apply(null,arguments)}function Rt(o,t){let n;return(...e)=>{window.clearTimeout(n),n=window.setTimeout(()=>o(...e),t)}}function $n({debounce:o,scroll:t,polyfill:n,offsetSize:e}={debounce:0,scroll:!1,offsetSize:!1}){const r=n||(typeof window>"u"?class{}:window.ResizeObserver);if(!r)throw new Error("This browser does not support ResizeObserver out of the box. See: https://github.com/react-spring/react-use-measure/#resize-observer-polyfills");const[a,u]=l.useState({left:0,top:0,width:0,height:0,bottom:0,right:0,x:0,y:0}),s=l.useRef({element:null,scrollContainers:null,resizeObserver:null,lastBounds:a,orientationHandler:null}),d=o?typeof o=="number"?o:o.scroll:null,S=o?typeof o=="number"?o:o.resize:null,f=l.useRef(!1);l.useEffect(()=>(f.current=!0,()=>void(f.current=!1)));const[p,E,g]=l.useMemo(()=>{const v=()=>{if(!s.current.element)return;const{left:A,top:x,width:P,height:_,bottom:h,right:k,x:z,y:T}=s.current.element.getBoundingClientRect(),L={left:A,top:x,width:P,height:_,bottom:h,right:k,x:z,y:T};s.current.element instanceof HTMLElement&&e&&(L.height=s.current.element.offsetHeight,L.width=s.current.element.offsetWidth),Object.freeze(L),f.current&&!Jn(s.current.lastBounds,L)&&u(s.current.lastBounds=L)};return[v,S?Rt(v,S):v,d?Rt(v,d):v]},[u,e,d,S]);function M(){s.current.scrollContainers&&(s.current.scrollContainers.forEach(v=>v.removeEventListener("scroll",g,!0)),s.current.scrollContainers=null),s.current.resizeObserver&&(s.current.resizeObserver.disconnect(),s.current.resizeObserver=null),s.current.orientationHandler&&("orientation"in screen&&"removeEventListener"in screen.orientation?screen.orientation.removeEventListener("change",s.current.orientationHandler):"onorientationchange"in window&&window.removeEventListener("orientationchange",s.current.orientationHandler))}function b(){s.current.element&&(s.current.resizeObserver=new r(g),s.current.resizeObserver.observe(s.current.element),t&&s.current.scrollContainers&&s.current.scrollContainers.forEach(v=>v.addEventListener("scroll",g,{capture:!0,passive:!0})),s.current.orientationHandler=()=>{g()},"orientation"in screen&&"addEventListener"in screen.orientation?screen.orientation.addEventListener("change",s.current.orientationHandler):"onorientationchange"in window&&window.addEventListener("orientationchange",s.current.orientationHandler))}const y=v=>{!v||v===s.current.element||(M(),s.current.element=v,s.current.scrollContainers=Kt(v),b())};return Kn(g,!!t),qn(E),l.useEffect(()=>{M(),b()},[t,g,E]),l.useEffect(()=>M,[]),[y,a,p]}function qn(o){l.useEffect(()=>{const t=o;return window.addEventListener("resize",t),()=>void window.removeEventListener("resize",t)},[o])}function Kn(o,t){l.useEffect(()=>{if(t){const n=o;return window.addEventListener("scroll",n,{capture:!0,passive:!0}),()=>void window.removeEventListener("scroll",n,!0)}},[o,t])}function Kt(o){const t=[];if(!o||o===document.body)return t;const{overflow:n,overflowX:e,overflowY:r}=window.getComputedStyle(o);return[n,e,r].some(a=>a==="auto"||a==="scroll")&&t.push(o),[...t,...Kt(o.parentElement)]}const Qn=["x","y","top","bottom","left","right","width","height"],Jn=(o,t)=>Qn.every(n=>o[n]===t[n]);function eo({ref:o,children:t,fallback:n,resize:e,style:r,gl:a,events:u=Mn,eventSource:s,eventPrefix:d,shadows:S,linear:f,flat:p,legacy:E,orthographic:g,frameloop:M,dpr:b,performance:y,raycaster:v,camera:A,scene:x,onPointerMissed:P,onCreated:_,...h}){l.useMemo(()=>En(_n),[]);const k=bn(),[z,T]=$n({scroll:!0,debounce:{scroll:50,resize:0},...e}),L=l.useRef(null),I=l.useRef(null);l.useImperativeHandle(o,()=>L.current);const Pe=xn(P),[K,xe]=l.useState(!1),[U,pe]=l.useState(!1);if(K)throw K;if(U)throw U;const B=l.useRef(null);wn(()=>{const Z=L.current;if(T.width>0&&T.height>0&&Z){B.current||(B.current=Sn(Z));async function Q(){await B.current.configure({gl:a,scene:x,events:u,shadows:S,linear:f,flat:p,legacy:E,orthographic:g,frameloop:M,dpr:b,performance:y,raycaster:v,camera:A,size:T,onPointerMissed:(...$)=>Pe.current==null?void 0:Pe.current(...$),onCreated:$=>{$.events.connect==null||$.events.connect(s?Pn(s)?s.current:s:I.current),d&&$.setEvents({compute:(J,N)=>{const le=J[d+"X"],he=J[d+"Y"];N.pointer.set(le/N.size.width*2-1,-(he/N.size.height)*2+1),N.raycaster.setFromCamera(N.pointer,N.camera)}}),_==null||_($)}}),B.current.render(fe.jsx(k,{children:fe.jsx(On,{set:pe,children:fe.jsx(l.Suspense,{fallback:fe.jsx(Ln,{set:xe}),children:t??null})})}))}Q()}}),l.useEffect(()=>{const Z=L.current;if(Z)return()=>An(Z)},[]);const te=s?"none":"auto";return fe.jsx("div",{ref:I,style:{position:"relative",width:"100%",height:"100%",overflow:"hidden",pointerEvents:te,...r},...h,children:fe.jsx("div",{ref:z,style:{width:"100%",height:"100%"},children:fe.jsx("canvas",{ref:L,style:{display:"block"},children:n})})})}function to(o){return fe.jsx(vn,{children:fe.jsx(eo,{...o})})}const He=new C,yt=new C,no=new C,Dt=new q;function oo(o,t,n){const e=He.setFromMatrixPosition(o.matrixWorld);e.project(t);const r=n.width/2,a=n.height/2;return[e.x*r+r,-(e.y*a)+a]}function io(o,t){const n=He.setFromMatrixPosition(o.matrixWorld),e=yt.setFromMatrixPosition(t.matrixWorld),r=n.sub(e),a=t.getWorldDirection(no);return r.angleTo(a)>Math.PI/2}function ro(o,t,n,e){const r=He.setFromMatrixPosition(o.matrixWorld),a=r.clone();a.project(t),Dt.set(a.x,a.y),n.setFromCamera(Dt,t);const u=n.intersectObjects(e,!0);if(u.length){const s=u[0].distance;return r.distanceTo(n.ray.origin)<s}return!0}function so(o,t){if(t instanceof Fe)return t.zoom;if(t instanceof Ne){const n=He.setFromMatrixPosition(o.matrixWorld),e=yt.setFromMatrixPosition(t.matrixWorld),r=t.fov*Math.PI/180,a=n.distanceTo(e);return 1/(2*Math.tan(r/2)*a)}else return 1}function ao(o,t,n){if(t instanceof Ne||t instanceof Fe){const e=He.setFromMatrixPosition(o.matrixWorld),r=yt.setFromMatrixPosition(t.matrixWorld),a=e.distanceTo(r),u=(n[1]-n[0])/(t.far-t.near),s=n[1]-u*t.far;return Math.round(u*a+s)}}const ht=o=>Math.abs(o)<1e-10?0:o;function Qt(o,t,n=""){let e="matrix3d(";for(let r=0;r!==16;r++)e+=ht(t[r]*o.elements[r])+(r!==15?",":")");return n+e}const lo=(o=>t=>Qt(t,o))([1,-1,1,1,1,-1,1,1,1,-1,1,1,1,-1,1,1]),co=(o=>(t,n)=>Qt(t,o(n),"translate(-50%,-50%)"))(o=>[1/o,1/o,1/o,1,-1/o,-1/o,-1/o,-1,1/o,1/o,1/o,1,1,1,1,1]);function uo(o){return o&&typeof o=="object"&&"current"in o}const st=l.forwardRef(({children:o,eps:t=.001,style:n,className:e,prepend:r,center:a,fullscreen:u,portal:s,distanceFactor:d,sprite:S=!1,transform:f=!1,occlude:p,onOcclude:E,castShadow:g,receiveShadow:M,material:b,geometry:y,zIndexRange:v=[16777271,0],calculatePosition:A=oo,as:x="div",wrapperClass:P,pointerEvents:_="auto",...h},k)=>{const{gl:z,camera:T,scene:L,size:I,raycaster:Pe,events:K,viewport:xe}=j(),[U]=l.useState(()=>document.createElement(x)),pe=l.useRef(null),B=l.useRef(null),te=l.useRef(0),Z=l.useRef([0,0]),Q=l.useRef(null),$=l.useRef(null),J=(s==null?void 0:s.current)||K.connected||z.domElement.parentNode,N=l.useRef(null),le=l.useRef(!1),he=l.useMemo(()=>p&&p!=="blending"||Array.isArray(p)&&p.length&&uo(p[0]),[p]);l.useLayoutEffect(()=>{const X=z.domElement;p&&p==="blending"?(X.style.zIndex=`${Math.floor(v[0]/2)}`,X.style.position="absolute",X.style.pointerEvents="none"):(X.style.zIndex=null,X.style.position=null,X.style.pointerEvents=null)},[p]),l.useLayoutEffect(()=>{if(B.current){const X=pe.current=dn.createRoot(U);if(L.updateMatrixWorld(),f)U.style.cssText="position:absolute;top:0;left:0;pointer-events:none;overflow:hidden;";else{const D=A(B.current,T,I);U.style.cssText=`position:absolute;top:0;left:0;transform:translate3d(${D[0]}px,${D[1]}px,0);transform-origin:0 0;`}return J&&(r?J.prepend(U):J.appendChild(U)),()=>{J&&J.removeChild(U),X.unmount()}}},[J,f]),l.useLayoutEffect(()=>{P&&(U.className=P)},[P]);const ze=l.useMemo(()=>f?{position:"absolute",top:0,left:0,width:I.width,height:I.height,transformStyle:"preserve-3d",pointerEvents:"none"}:{position:"absolute",transform:a?"translate3d(-50%,-50%,0)":"none",...u&&{top:-I.height/2,left:-I.width/2,width:I.width,height:I.height},...n},[n,a,u,I,f]),Je=l.useMemo(()=>({position:"absolute",pointerEvents:_}),[_]);l.useLayoutEffect(()=>{if(le.current=!1,f){var X;(X=pe.current)==null||X.render(l.createElement("div",{ref:Q,style:ze},l.createElement("div",{ref:$,style:Je},l.createElement("div",{ref:k,className:e,style:n,children:o}))))}else{var D;(D=pe.current)==null||D.render(l.createElement("div",{ref:k,style:ze,className:e,children:o}))}});const ge=l.useRef(!0);Me(X=>{if(B.current){T.updateMatrixWorld(),B.current.updateWorldMatrix(!0,!1);const D=f?Z.current:A(B.current,T,I);if(f||Math.abs(te.current-T.zoom)>t||Math.abs(Z.current[0]-D[0])>t||Math.abs(Z.current[1]-D[1])>t){const ne=io(B.current,T);let ee=!1;he&&(Array.isArray(p)?ee=p.map(oe=>oe.current):p!=="blending"&&(ee=[L]));const ye=ge.current;if(ee){const oe=ro(B.current,T,Pe,ee);ge.current=oe&&!ne}else ge.current=!ne;ye!==ge.current&&(E?E(!ge.current):U.style.display=ge.current?"block":"none");const Oe=Math.floor(v[0]/2),et=p?he?[v[0],Oe]:[Oe-1,0]:v;if(U.style.zIndex=`${ao(B.current,T,et)}`,f){const[oe,je]=[I.width/2,I.height/2],Le=T.projectionMatrix.elements[5]*je,{isOrthographicCamera:Ye,top:tt,left:Ge,bottom:Ie,right:we}=T,nt=lo(T.matrixWorldInverse),ot=Ye?`scale(${Le})translate(${ht(-(we+Ge)/2)}px,${ht((tt+Ie)/2)}px)`:`translateZ(${Le}px)`;let ie=B.current.matrixWorld;S&&(ie=T.matrixWorldInverse.clone().transpose().copyPosition(ie).scale(B.current.scale),ie.elements[3]=ie.elements[7]=ie.elements[11]=0,ie.elements[15]=1),U.style.width=I.width+"px",U.style.height=I.height+"px",U.style.perspective=Ye?"":`${Le}px`,Q.current&&$.current&&(Q.current.style.transform=`${ot}${nt}translate(${oe}px,${je}px)`,$.current.style.transform=co(ie,1/((d||10)/400)))}else{const oe=d===void 0?1:so(B.current,T)*d;U.style.transform=`translate3d(${D[0]}px,${D[1]}px,0) scale(${oe})`}Z.current=D,te.current=T.zoom}}if(!he&&N.current&&!le.current)if(f){if(Q.current){const D=Q.current.children[0];if(D!=null&&D.clientWidth&&D!=null&&D.clientHeight){const{isOrthographicCamera:ne}=T;if(ne||y)h.scale&&(Array.isArray(h.scale)?h.scale instanceof C?N.current.scale.copy(h.scale.clone().divideScalar(1)):N.current.scale.set(1/h.scale[0],1/h.scale[1],1/h.scale[2]):N.current.scale.setScalar(1/h.scale));else{const ee=(d||10)/400,ye=D.clientWidth*ee,Oe=D.clientHeight*ee;N.current.scale.set(ye,Oe,1)}le.current=!0}}}else{const D=U.children[0];if(D!=null&&D.clientWidth&&D!=null&&D.clientHeight){const ne=1/xe.factor,ee=D.clientWidth*ne,ye=D.clientHeight*ne;N.current.scale.set(ee,ye,1),le.current=!0}N.current.lookAt(X.camera.position)}});const We=l.useMemo(()=>({vertexShader:f?void 0:`
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
      `}),[f]);return l.createElement("group",V({},h,{ref:B}),p&&!he&&l.createElement("mesh",{castShadow:g,receiveShadow:M,ref:N},y||l.createElement("planeGeometry",null),b||l.createElement("shaderMaterial",{side:be,vertexShader:We.vertexShader,fragmentShader:We.fragmentShader})))}),Jt=Vt>=125?"uv1":"uv2";var fo=Object.defineProperty,mo=(o,t,n)=>t in o?fo(o,t,{enumerable:!0,configurable:!0,writable:!0,value:n}):o[t]=n,po=(o,t,n)=>(mo(o,t+"",n),n);class ho{constructor(){po(this,"_listeners")}addEventListener(t,n){this._listeners===void 0&&(this._listeners={});const e=this._listeners;e[t]===void 0&&(e[t]=[]),e[t].indexOf(n)===-1&&e[t].push(n)}hasEventListener(t,n){if(this._listeners===void 0)return!1;const e=this._listeners;return e[t]!==void 0&&e[t].indexOf(n)!==-1}removeEventListener(t,n){if(this._listeners===void 0)return;const r=this._listeners[t];if(r!==void 0){const a=r.indexOf(n);a!==-1&&r.splice(a,1)}}dispatchEvent(t){if(this._listeners===void 0)return;const e=this._listeners[t.type];if(e!==void 0){t.target=this;const r=e.slice(0);for(let a=0,u=r.length;a<u;a++)r[a].call(this,t);t.target=null}}}var go=Object.defineProperty,yo=(o,t,n)=>t in o?go(o,t,{enumerable:!0,configurable:!0,writable:!0,value:n}):o[t]=n,w=(o,t,n)=>(yo(o,typeof t!="symbol"?t+"":t,n),n);const Ve=new Tn,zt=new Zt,vo=Math.cos(70*(Math.PI/180)),jt=(o,t)=>(o%t+t)%t;let Eo=class extends ho{constructor(t,n){super(),w(this,"object"),w(this,"domElement"),w(this,"enabled",!0),w(this,"target",new C),w(this,"minDistance",0),w(this,"maxDistance",1/0),w(this,"minZoom",0),w(this,"maxZoom",1/0),w(this,"minPolarAngle",0),w(this,"maxPolarAngle",Math.PI),w(this,"minAzimuthAngle",-1/0),w(this,"maxAzimuthAngle",1/0),w(this,"enableDamping",!1),w(this,"dampingFactor",.05),w(this,"enableZoom",!0),w(this,"zoomSpeed",1),w(this,"enableRotate",!0),w(this,"rotateSpeed",1),w(this,"enablePan",!0),w(this,"panSpeed",1),w(this,"screenSpacePanning",!0),w(this,"keyPanSpeed",7),w(this,"zoomToCursor",!1),w(this,"autoRotate",!1),w(this,"autoRotateSpeed",2),w(this,"reverseOrbit",!1),w(this,"reverseHorizontalOrbit",!1),w(this,"reverseVerticalOrbit",!1),w(this,"keys",{LEFT:"ArrowLeft",UP:"ArrowUp",RIGHT:"ArrowRight",BOTTOM:"ArrowDown"}),w(this,"mouseButtons",{LEFT:Ae.ROTATE,MIDDLE:Ae.DOLLY,RIGHT:Ae.PAN}),w(this,"touches",{ONE:_e.ROTATE,TWO:_e.DOLLY_PAN}),w(this,"target0"),w(this,"position0"),w(this,"zoom0"),w(this,"_domElementKeyEvents",null),w(this,"getPolarAngle"),w(this,"getAzimuthalAngle"),w(this,"setPolarAngle"),w(this,"setAzimuthalAngle"),w(this,"getDistance"),w(this,"getZoomScale"),w(this,"listenToKeyEvents"),w(this,"stopListenToKeyEvents"),w(this,"saveState"),w(this,"reset"),w(this,"update"),w(this,"connect"),w(this,"dispose"),w(this,"dollyIn"),w(this,"dollyOut"),w(this,"getScale"),w(this,"setScale"),this.object=t,this.domElement=n,this.target0=this.target.clone(),this.position0=this.object.position.clone(),this.zoom0=this.object.zoom,this.getPolarAngle=()=>f.phi,this.getAzimuthalAngle=()=>f.theta,this.setPolarAngle=i=>{let m=jt(i,2*Math.PI),O=f.phi;O<0&&(O+=2*Math.PI),m<0&&(m+=2*Math.PI);let R=Math.abs(m-O);2*Math.PI-R<R&&(m<O?m+=2*Math.PI:O+=2*Math.PI),p.phi=m-O,e.update()},this.setAzimuthalAngle=i=>{let m=jt(i,2*Math.PI),O=f.theta;O<0&&(O+=2*Math.PI),m<0&&(m+=2*Math.PI);let R=Math.abs(m-O);2*Math.PI-R<R&&(m<O?m+=2*Math.PI:O+=2*Math.PI),p.theta=m-O,e.update()},this.getDistance=()=>e.object.position.distanceTo(e.target),this.listenToKeyEvents=i=>{i.addEventListener("keydown",it),this._domElementKeyEvents=i},this.stopListenToKeyEvents=()=>{this._domElementKeyEvents.removeEventListener("keydown",it),this._domElementKeyEvents=null},this.saveState=()=>{e.target0.copy(e.target),e.position0.copy(e.object.position),e.zoom0=e.object.zoom},this.reset=()=>{e.target.copy(e.target0),e.object.position.copy(e.position0),e.object.zoom=e.zoom0,e.object.updateProjectionMatrix(),e.dispatchEvent(r),e.update(),d=s.NONE},this.update=(()=>{const i=new C,m=new C(0,1,0),O=new Ke().setFromUnitVectors(t.up,m),R=O.clone().invert(),H=new C,ce=new Ke,ve=2*Math.PI;return function(){const St=e.object.position;O.setFromUnitVectors(t.up,m),R.copy(O).invert(),i.copy(St).sub(e.target),i.applyQuaternion(O),f.setFromVector3(i),e.autoRotate&&d===s.NONE&&xe(Pe()),e.enableDamping?(f.theta+=p.theta*e.dampingFactor,f.phi+=p.phi*e.dampingFactor):(f.theta+=p.theta,f.phi+=p.phi);let ue=e.minAzimuthAngle,de=e.maxAzimuthAngle;isFinite(ue)&&isFinite(de)&&(ue<-Math.PI?ue+=ve:ue>Math.PI&&(ue-=ve),de<-Math.PI?de+=ve:de>Math.PI&&(de-=ve),ue<=de?f.theta=Math.max(ue,Math.min(de,f.theta)):f.theta=f.theta>(ue+de)/2?Math.max(ue,f.theta):Math.min(de,f.theta)),f.phi=Math.max(e.minPolarAngle,Math.min(e.maxPolarAngle,f.phi)),f.makeSafe(),e.enableDamping===!0?e.target.addScaledVector(g,e.dampingFactor):e.target.add(g),e.zoomToCursor&&T||e.object.isOrthographicCamera?f.radius=N(f.radius):f.radius=N(f.radius*E),i.setFromSpherical(f),i.applyQuaternion(R),St.copy(e.target).add(i),e.object.matrixAutoUpdate||e.object.updateMatrix(),e.object.lookAt(e.target),e.enableDamping===!0?(p.theta*=1-e.dampingFactor,p.phi*=1-e.dampingFactor,g.multiplyScalar(1-e.dampingFactor)):(p.set(0,0,0),g.set(0,0,0));let Ue=!1;if(e.zoomToCursor&&T){let Be=null;if(e.object instanceof Ne&&e.object.isPerspectiveCamera){const ke=i.length();Be=N(ke*E);const Xe=ke-Be;e.object.position.addScaledVector(k,Xe),e.object.updateMatrixWorld()}else if(e.object.isOrthographicCamera){const ke=new C(z.x,z.y,0);ke.unproject(e.object),e.object.zoom=Math.max(e.minZoom,Math.min(e.maxZoom,e.object.zoom/E)),e.object.updateProjectionMatrix(),Ue=!0;const Xe=new C(z.x,z.y,0);Xe.unproject(e.object),e.object.position.sub(Xe).add(ke),e.object.updateMatrixWorld(),Be=i.length()}else console.warn("WARNING: OrbitControls.js encountered an unknown camera type - zoom to cursor disabled."),e.zoomToCursor=!1;Be!==null&&(e.screenSpacePanning?e.target.set(0,0,-1).transformDirection(e.object.matrix).multiplyScalar(Be).add(e.object.position):(Ve.origin.copy(e.object.position),Ve.direction.set(0,0,-1).transformDirection(e.object.matrix),Math.abs(e.object.up.dot(Ve.direction))<vo?t.lookAt(e.target):(zt.setFromNormalAndCoplanarPoint(e.object.up,e.target),Ve.intersectPlane(zt,e.target))))}else e.object instanceof Fe&&e.object.isOrthographicCamera&&(Ue=E!==1,Ue&&(e.object.zoom=Math.max(e.minZoom,Math.min(e.maxZoom,e.object.zoom/E)),e.object.updateProjectionMatrix()));return E=1,T=!1,Ue||H.distanceToSquared(e.object.position)>S||8*(1-ce.dot(e.object.quaternion))>S?(e.dispatchEvent(r),H.copy(e.object.position),ce.copy(e.object.quaternion),Ue=!1,!0):!1}})(),this.connect=i=>{e.domElement=i,e.domElement.style.touchAction="none",e.domElement.addEventListener("contextmenu",xt),e.domElement.addEventListener("pointerdown",Ge),e.domElement.addEventListener("pointercancel",we),e.domElement.addEventListener("wheel",ie)},this.dispose=()=>{var i,m,O,R,H,ce;e.domElement&&(e.domElement.style.touchAction="auto"),(i=e.domElement)==null||i.removeEventListener("contextmenu",xt),(m=e.domElement)==null||m.removeEventListener("pointerdown",Ge),(O=e.domElement)==null||O.removeEventListener("pointercancel",we),(R=e.domElement)==null||R.removeEventListener("wheel",ie),(H=e.domElement)==null||H.ownerDocument.removeEventListener("pointermove",Ie),(ce=e.domElement)==null||ce.ownerDocument.removeEventListener("pointerup",we),e._domElementKeyEvents!==null&&e._domElementKeyEvents.removeEventListener("keydown",it)};const e=this,r={type:"change"},a={type:"start"},u={type:"end"},s={NONE:-1,ROTATE:0,DOLLY:1,PAN:2,TOUCH_ROTATE:3,TOUCH_PAN:4,TOUCH_DOLLY_PAN:5,TOUCH_DOLLY_ROTATE:6};let d=s.NONE;const S=1e-6,f=new Lt,p=new Lt;let E=1;const g=new C,M=new q,b=new q,y=new q,v=new q,A=new q,x=new q,P=new q,_=new q,h=new q,k=new C,z=new q;let T=!1;const L=[],I={};function Pe(){return 2*Math.PI/60/60*e.autoRotateSpeed}function K(){return Math.pow(.95,e.zoomSpeed)}function xe(i){e.reverseOrbit||e.reverseHorizontalOrbit?p.theta+=i:p.theta-=i}function U(i){e.reverseOrbit||e.reverseVerticalOrbit?p.phi+=i:p.phi-=i}const pe=(()=>{const i=new C;return function(O,R){i.setFromMatrixColumn(R,0),i.multiplyScalar(-O),g.add(i)}})(),B=(()=>{const i=new C;return function(O,R){e.screenSpacePanning===!0?i.setFromMatrixColumn(R,1):(i.setFromMatrixColumn(R,0),i.crossVectors(e.object.up,i)),i.multiplyScalar(O),g.add(i)}})(),te=(()=>{const i=new C;return function(O,R){const H=e.domElement;if(H&&e.object instanceof Ne&&e.object.isPerspectiveCamera){const ce=e.object.position;i.copy(ce).sub(e.target);let ve=i.length();ve*=Math.tan(e.object.fov/2*Math.PI/180),pe(2*O*ve/H.clientHeight,e.object.matrix),B(2*R*ve/H.clientHeight,e.object.matrix)}else H&&e.object instanceof Fe&&e.object.isOrthographicCamera?(pe(O*(e.object.right-e.object.left)/e.object.zoom/H.clientWidth,e.object.matrix),B(R*(e.object.top-e.object.bottom)/e.object.zoom/H.clientHeight,e.object.matrix)):(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - pan disabled."),e.enablePan=!1)}})();function Z(i){e.object instanceof Ne&&e.object.isPerspectiveCamera||e.object instanceof Fe&&e.object.isOrthographicCamera?E=i:(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled."),e.enableZoom=!1)}function Q(i){Z(E/i)}function $(i){Z(E*i)}function J(i){if(!e.zoomToCursor||!e.domElement)return;T=!0;const m=e.domElement.getBoundingClientRect(),O=i.clientX-m.left,R=i.clientY-m.top,H=m.width,ce=m.height;z.x=O/H*2-1,z.y=-(R/ce)*2+1,k.set(z.x,z.y,1).unproject(e.object).sub(e.object.position).normalize()}function N(i){return Math.max(e.minDistance,Math.min(e.maxDistance,i))}function le(i){M.set(i.clientX,i.clientY)}function he(i){J(i),P.set(i.clientX,i.clientY)}function ze(i){v.set(i.clientX,i.clientY)}function Je(i){b.set(i.clientX,i.clientY),y.subVectors(b,M).multiplyScalar(e.rotateSpeed);const m=e.domElement;m&&(xe(2*Math.PI*y.x/m.clientHeight),U(2*Math.PI*y.y/m.clientHeight)),M.copy(b),e.update()}function ge(i){_.set(i.clientX,i.clientY),h.subVectors(_,P),h.y>0?Q(K()):h.y<0&&$(K()),P.copy(_),e.update()}function We(i){A.set(i.clientX,i.clientY),x.subVectors(A,v).multiplyScalar(e.panSpeed),te(x.x,x.y),v.copy(A),e.update()}function X(i){J(i),i.deltaY<0?$(K()):i.deltaY>0&&Q(K()),e.update()}function D(i){let m=!1;switch(i.code){case e.keys.UP:te(0,e.keyPanSpeed),m=!0;break;case e.keys.BOTTOM:te(0,-e.keyPanSpeed),m=!0;break;case e.keys.LEFT:te(e.keyPanSpeed,0),m=!0;break;case e.keys.RIGHT:te(-e.keyPanSpeed,0),m=!0;break}m&&(i.preventDefault(),e.update())}function ne(){if(L.length==1)M.set(L[0].pageX,L[0].pageY);else{const i=.5*(L[0].pageX+L[1].pageX),m=.5*(L[0].pageY+L[1].pageY);M.set(i,m)}}function ee(){if(L.length==1)v.set(L[0].pageX,L[0].pageY);else{const i=.5*(L[0].pageX+L[1].pageX),m=.5*(L[0].pageY+L[1].pageY);v.set(i,m)}}function ye(){const i=L[0].pageX-L[1].pageX,m=L[0].pageY-L[1].pageY,O=Math.sqrt(i*i+m*m);P.set(0,O)}function Oe(){e.enableZoom&&ye(),e.enablePan&&ee()}function et(){e.enableZoom&&ye(),e.enableRotate&&ne()}function oe(i){if(L.length==1)b.set(i.pageX,i.pageY);else{const O=rt(i),R=.5*(i.pageX+O.x),H=.5*(i.pageY+O.y);b.set(R,H)}y.subVectors(b,M).multiplyScalar(e.rotateSpeed);const m=e.domElement;m&&(xe(2*Math.PI*y.x/m.clientHeight),U(2*Math.PI*y.y/m.clientHeight)),M.copy(b)}function je(i){if(L.length==1)A.set(i.pageX,i.pageY);else{const m=rt(i),O=.5*(i.pageX+m.x),R=.5*(i.pageY+m.y);A.set(O,R)}x.subVectors(A,v).multiplyScalar(e.panSpeed),te(x.x,x.y),v.copy(A)}function Le(i){const m=rt(i),O=i.pageX-m.x,R=i.pageY-m.y,H=Math.sqrt(O*O+R*R);_.set(0,H),h.set(0,Math.pow(_.y/P.y,e.zoomSpeed)),Q(h.y),P.copy(_)}function Ye(i){e.enableZoom&&Le(i),e.enablePan&&je(i)}function tt(i){e.enableZoom&&Le(i),e.enableRotate&&oe(i)}function Ge(i){var m,O;e.enabled!==!1&&(L.length===0&&((m=e.domElement)==null||m.ownerDocument.addEventListener("pointermove",Ie),(O=e.domElement)==null||O.ownerDocument.addEventListener("pointerup",we)),an(i),i.pointerType==="touch"?rn(i):nt(i))}function Ie(i){e.enabled!==!1&&(i.pointerType==="touch"?sn(i):ot(i))}function we(i){var m,O,R;ln(i),L.length===0&&((m=e.domElement)==null||m.releasePointerCapture(i.pointerId),(O=e.domElement)==null||O.ownerDocument.removeEventListener("pointermove",Ie),(R=e.domElement)==null||R.ownerDocument.removeEventListener("pointerup",we)),e.dispatchEvent(u),d=s.NONE}function nt(i){let m;switch(i.button){case 0:m=e.mouseButtons.LEFT;break;case 1:m=e.mouseButtons.MIDDLE;break;case 2:m=e.mouseButtons.RIGHT;break;default:m=-1}switch(m){case Ae.DOLLY:if(e.enableZoom===!1)return;he(i),d=s.DOLLY;break;case Ae.ROTATE:if(i.ctrlKey||i.metaKey||i.shiftKey){if(e.enablePan===!1)return;ze(i),d=s.PAN}else{if(e.enableRotate===!1)return;le(i),d=s.ROTATE}break;case Ae.PAN:if(i.ctrlKey||i.metaKey||i.shiftKey){if(e.enableRotate===!1)return;le(i),d=s.ROTATE}else{if(e.enablePan===!1)return;ze(i),d=s.PAN}break;default:d=s.NONE}d!==s.NONE&&e.dispatchEvent(a)}function ot(i){if(e.enabled!==!1)switch(d){case s.ROTATE:if(e.enableRotate===!1)return;Je(i);break;case s.DOLLY:if(e.enableZoom===!1)return;ge(i);break;case s.PAN:if(e.enablePan===!1)return;We(i);break}}function ie(i){e.enabled===!1||e.enableZoom===!1||d!==s.NONE&&d!==s.ROTATE||(i.preventDefault(),e.dispatchEvent(a),X(i),e.dispatchEvent(u))}function it(i){e.enabled===!1||e.enablePan===!1||D(i)}function rn(i){switch(wt(i),L.length){case 1:switch(e.touches.ONE){case _e.ROTATE:if(e.enableRotate===!1)return;ne(),d=s.TOUCH_ROTATE;break;case _e.PAN:if(e.enablePan===!1)return;ee(),d=s.TOUCH_PAN;break;default:d=s.NONE}break;case 2:switch(e.touches.TWO){case _e.DOLLY_PAN:if(e.enableZoom===!1&&e.enablePan===!1)return;Oe(),d=s.TOUCH_DOLLY_PAN;break;case _e.DOLLY_ROTATE:if(e.enableZoom===!1&&e.enableRotate===!1)return;et(),d=s.TOUCH_DOLLY_ROTATE;break;default:d=s.NONE}break;default:d=s.NONE}d!==s.NONE&&e.dispatchEvent(a)}function sn(i){switch(wt(i),d){case s.TOUCH_ROTATE:if(e.enableRotate===!1)return;oe(i),e.update();break;case s.TOUCH_PAN:if(e.enablePan===!1)return;je(i),e.update();break;case s.TOUCH_DOLLY_PAN:if(e.enableZoom===!1&&e.enablePan===!1)return;Ye(i),e.update();break;case s.TOUCH_DOLLY_ROTATE:if(e.enableZoom===!1&&e.enableRotate===!1)return;tt(i),e.update();break;default:d=s.NONE}}function xt(i){e.enabled!==!1&&i.preventDefault()}function an(i){L.push(i)}function ln(i){delete I[i.pointerId];for(let m=0;m<L.length;m++)if(L[m].pointerId==i.pointerId){L.splice(m,1);return}}function wt(i){let m=I[i.pointerId];m===void 0&&(m=new q,I[i.pointerId]=m),m.set(i.pageX,i.pageY)}function rt(i){const m=i.pointerId===L[0].pointerId?L[1]:L[0];return I[m.pointerId]}this.dollyIn=(i=K())=>{$(i),e.update()},this.dollyOut=(i=K())=>{Q(i),e.update()},this.getScale=()=>E,this.setScale=i=>{Z(i),e.update()},this.getZoomScale=()=>K(),n!==void 0&&this.connect(n),this.update()}};const It=new gt,Ze=new C;class vt extends Cn{constructor(){super(),this.isLineSegmentsGeometry=!0,this.type="LineSegmentsGeometry";const t=[-1,2,0,1,2,0,-1,1,0,1,1,0,-1,0,0,1,0,0,-1,-1,0,1,-1,0],n=[-1,2,1,2,-1,1,1,1,-1,-1,1,-1,-1,-2,1,-2],e=[0,2,1,2,3,1,2,4,3,4,5,3,4,6,5,6,7,5];this.setIndex(e),this.setAttribute("position",new At(t,3)),this.setAttribute("uv",new At(n,2))}applyMatrix4(t){const n=this.attributes.instanceStart,e=this.attributes.instanceEnd;return n!==void 0&&(n.applyMatrix4(t),e.applyMatrix4(t),n.needsUpdate=!0),this.boundingBox!==null&&this.computeBoundingBox(),this.boundingSphere!==null&&this.computeBoundingSphere(),this}setPositions(t){let n;t instanceof Float32Array?n=t:Array.isArray(t)&&(n=new Float32Array(t));const e=new pt(n,6,1);return this.setAttribute("instanceStart",new Re(e,3,0)),this.setAttribute("instanceEnd",new Re(e,3,3)),this.computeBoundingBox(),this.computeBoundingSphere(),this}setColors(t,n=3){let e;t instanceof Float32Array?e=t:Array.isArray(t)&&(e=new Float32Array(t));const r=new pt(e,n*2,1);return this.setAttribute("instanceColorStart",new Re(r,n,0)),this.setAttribute("instanceColorEnd",new Re(r,n,n)),this}fromWireframeGeometry(t){return this.setPositions(t.attributes.position.array),this}fromEdgesGeometry(t){return this.setPositions(t.attributes.position.array),this}fromMesh(t){return this.fromWireframeGeometry(new Rn(t.geometry)),this}fromLineSegments(t){const n=t.geometry;return this.setPositions(n.attributes.position.array),this}computeBoundingBox(){this.boundingBox===null&&(this.boundingBox=new gt);const t=this.attributes.instanceStart,n=this.attributes.instanceEnd;t!==void 0&&n!==void 0&&(this.boundingBox.setFromBufferAttribute(t),It.setFromBufferAttribute(n),this.boundingBox.union(It))}computeBoundingSphere(){this.boundingSphere===null&&(this.boundingSphere=new $t),this.boundingBox===null&&this.computeBoundingBox();const t=this.attributes.instanceStart,n=this.attributes.instanceEnd;if(t!==void 0&&n!==void 0){const e=this.boundingSphere.center;this.boundingBox.getCenter(e);let r=0;for(let a=0,u=t.count;a<u;a++)Ze.fromBufferAttribute(t,a),r=Math.max(r,e.distanceToSquared(Ze)),Ze.fromBufferAttribute(n,a),r=Math.max(r,e.distanceToSquared(Ze));this.boundingSphere.radius=Math.sqrt(r),isNaN(this.boundingSphere.radius)&&console.error("THREE.LineSegmentsGeometry.computeBoundingSphere(): Computed radius is NaN. The instanced position data is likely to have NaN values.",this)}}toJSON(){}applyMatrix(t){return console.warn("THREE.LineSegmentsGeometry: applyMatrix() has been renamed to applyMatrix4()."),this.applyMatrix4(t)}}class en extends vt{constructor(){super(),this.isLineGeometry=!0,this.type="LineGeometry"}setPositions(t){const n=t.length-3,e=new Float32Array(2*n);for(let r=0;r<n;r+=3)e[2*r]=t[r],e[2*r+1]=t[r+1],e[2*r+2]=t[r+2],e[2*r+3]=t[r+3],e[2*r+4]=t[r+4],e[2*r+5]=t[r+5];return super.setPositions(e),this}setColors(t,n=3){const e=t.length-n,r=new Float32Array(2*e);if(n===3)for(let a=0;a<e;a+=n)r[2*a]=t[a],r[2*a+1]=t[a+1],r[2*a+2]=t[a+2],r[2*a+3]=t[a+3],r[2*a+4]=t[a+4],r[2*a+5]=t[a+5];else for(let a=0;a<e;a+=n)r[2*a]=t[a],r[2*a+1]=t[a+1],r[2*a+2]=t[a+2],r[2*a+3]=t[a+3],r[2*a+4]=t[a+4],r[2*a+5]=t[a+5],r[2*a+6]=t[a+6],r[2*a+7]=t[a+7];return super.setColors(r,n),this}fromLine(t){const n=t.geometry;return this.setPositions(n.attributes.position.array),this}}class Et extends Dn{constructor(t){super({type:"LineMaterial",uniforms:_t.clone(_t.merge([Tt.common,Tt.fog,{worldUnits:{value:1},linewidth:{value:1},resolution:{value:new q(1,1)},dashOffset:{value:0},dashScale:{value:1},dashSize:{value:1},gapSize:{value:1}}])),vertexShader:`
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
			`,clipping:!0}),this.isLineMaterial=!0,this.onBeforeCompile=function(){this.transparent?this.defines.USE_LINE_COLOR_ALPHA="1":delete this.defines.USE_LINE_COLOR_ALPHA},Object.defineProperties(this,{color:{enumerable:!0,get:function(){return this.uniforms.diffuse.value},set:function(n){this.uniforms.diffuse.value=n}},worldUnits:{enumerable:!0,get:function(){return"WORLD_UNITS"in this.defines},set:function(n){n===!0?this.defines.WORLD_UNITS="":delete this.defines.WORLD_UNITS}},linewidth:{enumerable:!0,get:function(){return this.uniforms.linewidth.value},set:function(n){this.uniforms.linewidth.value=n}},dashed:{enumerable:!0,get:function(){return"USE_DASH"in this.defines},set(n){!!n!="USE_DASH"in this.defines&&(this.needsUpdate=!0),n===!0?this.defines.USE_DASH="":delete this.defines.USE_DASH}},dashScale:{enumerable:!0,get:function(){return this.uniforms.dashScale.value},set:function(n){this.uniforms.dashScale.value=n}},dashSize:{enumerable:!0,get:function(){return this.uniforms.dashSize.value},set:function(n){this.uniforms.dashSize.value=n}},dashOffset:{enumerable:!0,get:function(){return this.uniforms.dashOffset.value},set:function(n){this.uniforms.dashOffset.value=n}},gapSize:{enumerable:!0,get:function(){return this.uniforms.gapSize.value},set:function(n){this.uniforms.gapSize.value=n}},opacity:{enumerable:!0,get:function(){return this.uniforms.opacity.value},set:function(n){this.uniforms.opacity.value=n}},resolution:{enumerable:!0,get:function(){return this.uniforms.resolution.value},set:function(n){this.uniforms.resolution.value.copy(n)}},alphaToCoverage:{enumerable:!0,get:function(){return"USE_ALPHA_TO_COVERAGE"in this.defines},set:function(n){!!n!="USE_ALPHA_TO_COVERAGE"in this.defines&&(this.needsUpdate=!0),n===!0?(this.defines.USE_ALPHA_TO_COVERAGE="",this.extensions.derivatives=!0):(delete this.defines.USE_ALPHA_TO_COVERAGE,this.extensions.derivatives=!1)}}}),this.setValues(t)}}const at=new De,Ut=new C,Bt=new C,W=new De,Y=new De,re=new De,lt=new C,ct=new qt,G=new jn,kt=new C,$e=new gt,qe=new $t,se=new De;let ae,Se;function Nt(o,t,n){return se.set(0,0,-t,1).applyMatrix4(o.projectionMatrix),se.multiplyScalar(1/se.w),se.x=Se/n.width,se.y=Se/n.height,se.applyMatrix4(o.projectionMatrixInverse),se.multiplyScalar(1/se.w),Math.abs(Math.max(se.x,se.y))}function bo(o,t){const n=o.matrixWorld,e=o.geometry,r=e.attributes.instanceStart,a=e.attributes.instanceEnd,u=Math.min(e.instanceCount,r.count);for(let s=0,d=u;s<d;s++){G.start.fromBufferAttribute(r,s),G.end.fromBufferAttribute(a,s),G.applyMatrix4(n);const S=new C,f=new C;ae.distanceSqToSegment(G.start,G.end,f,S),f.distanceTo(S)<Se*.5&&t.push({point:f,pointOnLine:S,distance:ae.origin.distanceTo(f),object:o,face:null,faceIndex:s,uv:null,[Jt]:null})}}function xo(o,t,n){const e=t.projectionMatrix,a=o.material.resolution,u=o.matrixWorld,s=o.geometry,d=s.attributes.instanceStart,S=s.attributes.instanceEnd,f=Math.min(s.instanceCount,d.count),p=-t.near;ae.at(1,re),re.w=1,re.applyMatrix4(t.matrixWorldInverse),re.applyMatrix4(e),re.multiplyScalar(1/re.w),re.x*=a.x/2,re.y*=a.y/2,re.z=0,lt.copy(re),ct.multiplyMatrices(t.matrixWorldInverse,u);for(let E=0,g=f;E<g;E++){if(W.fromBufferAttribute(d,E),Y.fromBufferAttribute(S,E),W.w=1,Y.w=1,W.applyMatrix4(ct),Y.applyMatrix4(ct),W.z>p&&Y.z>p)continue;if(W.z>p){const x=W.z-Y.z,P=(W.z-p)/x;W.lerp(Y,P)}else if(Y.z>p){const x=Y.z-W.z,P=(Y.z-p)/x;Y.lerp(W,P)}W.applyMatrix4(e),Y.applyMatrix4(e),W.multiplyScalar(1/W.w),Y.multiplyScalar(1/Y.w),W.x*=a.x/2,W.y*=a.y/2,Y.x*=a.x/2,Y.y*=a.y/2,G.start.copy(W),G.start.z=0,G.end.copy(Y),G.end.z=0;const b=G.closestPointToPointParameter(lt,!0);G.at(b,kt);const y=In.lerp(W.z,Y.z,b),v=y>=-1&&y<=1,A=lt.distanceTo(kt)<Se*.5;if(v&&A){G.start.fromBufferAttribute(d,E),G.end.fromBufferAttribute(S,E),G.start.applyMatrix4(u),G.end.applyMatrix4(u);const x=new C,P=new C;ae.distanceSqToSegment(G.start,G.end,P,x),n.push({point:P,pointOnLine:x,distance:ae.origin.distanceTo(P),object:o,face:null,faceIndex:E,uv:null,[Jt]:null})}}}class tn extends zn{constructor(t=new vt,n=new Et({color:Math.random()*16777215})){super(t,n),this.isLineSegments2=!0,this.type="LineSegments2"}computeLineDistances(){const t=this.geometry,n=t.attributes.instanceStart,e=t.attributes.instanceEnd,r=new Float32Array(2*n.count);for(let u=0,s=0,d=n.count;u<d;u++,s+=2)Ut.fromBufferAttribute(n,u),Bt.fromBufferAttribute(e,u),r[s]=s===0?0:r[s-1],r[s+1]=r[s]+Ut.distanceTo(Bt);const a=new pt(r,2,1);return t.setAttribute("instanceDistanceStart",new Re(a,1,0)),t.setAttribute("instanceDistanceEnd",new Re(a,1,1)),this}raycast(t,n){const e=this.material.worldUnits,r=t.camera;r===null&&!e&&console.error('LineSegments2: "Raycaster.camera" needs to be set in order to raycast against LineSegments2 while worldUnits is set to false.');const a=t.params.Line2!==void 0&&t.params.Line2.threshold||0;ae=t.ray;const u=this.matrixWorld,s=this.geometry,d=this.material;Se=d.linewidth+a,s.boundingSphere===null&&s.computeBoundingSphere(),qe.copy(s.boundingSphere).applyMatrix4(u);let S;if(e)S=Se*.5;else{const p=Math.max(r.near,qe.distanceToPoint(ae.origin));S=Nt(r,p,d.resolution)}if(qe.radius+=S,ae.intersectsSphere(qe)===!1)return;s.boundingBox===null&&s.computeBoundingBox(),$e.copy(s.boundingBox).applyMatrix4(u);let f;if(e)f=Se*.5;else{const p=Math.max(r.near,$e.distanceToPoint(ae.origin));f=Nt(r,p,d.resolution)}$e.expandByScalar(f),ae.intersectsBox($e)!==!1&&(e?bo(this,n):xo(this,r,n))}onBeforeRender(t){const n=this.material.uniforms;n&&n.resolution&&(t.getViewport(at),this.material.uniforms.resolution.value.set(at.z,at.w))}}class wo extends tn{constructor(t=new en,n=new Et({color:Math.random()*16777215})){super(t,n),this.isLine2=!0,this.type="Line2"}}const nn=l.forwardRef(function({points:t,color:n=16777215,vertexColors:e,linewidth:r,lineWidth:a,segments:u,dashed:s,...d},S){var f,p;const E=j(v=>v.size),g=l.useMemo(()=>u?new tn:new wo,[u]),[M]=l.useState(()=>new Et),b=(e==null||(f=e[0])==null?void 0:f.length)===4?4:3,y=l.useMemo(()=>{const v=u?new vt:new en,A=t.map(x=>{const P=Array.isArray(x);return x instanceof C||x instanceof De?[x.x,x.y,x.z]:x instanceof q?[x.x,x.y,0]:P&&x.length===3?[x[0],x[1],x[2]]:P&&x.length===2?[x[0],x[1],0]:x});if(v.setPositions(A.flat()),e){n=16777215;const x=e.map(P=>P instanceof Un?P.toArray():P);v.setColors(x.flat(),b)}return v},[t,u,e,b]);return l.useLayoutEffect(()=>{g.computeLineDistances()},[t,g]),l.useLayoutEffect(()=>{s?M.defines.USE_DASH="":delete M.defines.USE_DASH,M.needsUpdate=!0},[s,M]),l.useEffect(()=>()=>{y.dispose(),M.dispose()},[y]),l.createElement("primitive",V({object:g,ref:S},d),l.createElement("primitive",{object:y,attach:"geometry"}),l.createElement("primitive",V({object:M,attach:"material",color:n,vertexColors:!!e,resolution:[E.width,E.height],linewidth:(p=r??a)!==null&&p!==void 0?p:1,dashed:s,transparent:b===4},d)))});function So(o,t,n){const e=j(g=>g.size),r=j(g=>g.viewport),a=typeof o=="number"?o:e.width*r.dpr,u=e.height*r.dpr,s=(typeof o=="number"?n:o)||{},{samples:d=0,depth:S,...f}=s,p=S??s.depthBuffer,E=l.useMemo(()=>{const g=new Bn(a,u,{minFilter:Ct,magFilter:Ct,type:kn,...f});return p&&(g.depthTexture=new Nn(a,u,Fn)),g.samples=d,g},[]);return l.useLayoutEffect(()=>{E.setSize(a,u),d&&(E.samples=d)},[d,E,a,u]),l.useEffect(()=>()=>E.dispose(),[]),E}const Mo=o=>typeof o=="function",Po=l.forwardRef(({envMap:o,resolution:t=256,frames:n=1/0,children:e,makeDefault:r,...a},u)=>{const s=j(({set:y})=>y),d=j(({camera:y})=>y),S=j(({size:y})=>y),f=l.useRef(null);l.useImperativeHandle(u,()=>f.current,[]);const p=l.useRef(null),E=So(t);l.useLayoutEffect(()=>{a.manual||f.current.updateProjectionMatrix()},[S,a]),l.useLayoutEffect(()=>{f.current.updateProjectionMatrix()}),l.useLayoutEffect(()=>{if(r){const y=d;return s(()=>({camera:f.current})),()=>s(()=>({camera:y}))}},[f,r,s]);let g=0,M=null;const b=Mo(e);return Me(y=>{b&&(n===1/0||g<n)&&(p.current.visible=!1,y.gl.setRenderTarget(E),M=y.scene.background,o&&(y.scene.background=o),y.gl.render(y.scene,f.current),y.scene.background=M,y.gl.setRenderTarget(null),p.current.visible=!0,g++)}),l.createElement(l.Fragment,null,l.createElement("orthographicCamera",V({left:S.width/-2,right:S.width/2,top:S.height/2,bottom:S.height/-2,ref:f},a),!b&&e),l.createElement("group",{ref:p},b&&e(E.texture)))}),Oo=l.forwardRef(({makeDefault:o,camera:t,regress:n,domElement:e,enableDamping:r=!0,keyEvents:a=!1,onChange:u,onStart:s,onEnd:d,...S},f)=>{const p=j(h=>h.invalidate),E=j(h=>h.camera),g=j(h=>h.gl),M=j(h=>h.events),b=j(h=>h.setEvents),y=j(h=>h.set),v=j(h=>h.get),A=j(h=>h.performance),x=t||E,P=e||M.connected||g.domElement,_=l.useMemo(()=>new Eo(x),[x]);return Me(()=>{_.enabled&&_.update()},-1),l.useEffect(()=>(a&&_.connect(a===!0?P:a),_.connect(P),()=>void _.dispose()),[a,P,n,_,p]),l.useEffect(()=>{const h=T=>{p(),n&&A.regress(),u&&u(T)},k=T=>{s&&s(T)},z=T=>{d&&d(T)};return _.addEventListener("change",h),_.addEventListener("start",k),_.addEventListener("end",z),()=>{_.removeEventListener("start",k),_.removeEventListener("end",z),_.removeEventListener("change",h)}},[u,s,d,_,p,b]),l.useEffect(()=>{if(o){const h=v().controls;return y({controls:_}),()=>y({controls:h})}},[o,_]),l.createElement("primitive",V({ref:f,object:_,enableDamping:r},S))});function Lo({defaultScene:o,defaultCamera:t,renderPriority:n=1}){const{gl:e,scene:r,camera:a}=j();let u;return Me(()=>{u=e.autoClear,n===1&&(e.autoClear=!0,e.render(o,t)),e.autoClear=!1,e.clearDepth(),e.render(r,a),e.autoClear=u},n),l.createElement("group",{onPointerOver:()=>null})}function Ao({children:o,renderPriority:t=1}){const{scene:n,camera:e}=j(),[r]=l.useState(()=>new Hn);return l.createElement(l.Fragment,null,Wn(l.createElement(l.Fragment,null,o,l.createElement(Lo,{defaultScene:n,defaultCamera:e,renderPriority:t})),r,{events:{priority:t+1}}))}const on=l.createContext({}),_o=()=>l.useContext(on),To=2*Math.PI,ut=new Yn,Ft=new qt,[Te,dt]=[new Ke,new Ke],Ht=new C,Wt=new C,Co=o=>"minPolarAngle"in o,Yt=o=>"getTarget"in o,Ro=({alignment:o="bottom-right",margin:t=[80,80],renderPriority:n=1,onUpdate:e,onTarget:r,children:a})=>{const u=j(h=>h.size),s=j(h=>h.camera),d=j(h=>h.controls),S=j(h=>h.invalidate),f=l.useRef(null),p=l.useRef(null),E=l.useRef(!1),g=l.useRef(0),M=l.useRef(new C(0,0,0)),b=l.useRef(new C(0,0,0));l.useEffect(()=>{b.current.copy(s.up),ut.up.copy(s.up)},[s]);const y=l.useCallback(h=>{E.current=!0,(d||r)&&(M.current=(r==null?void 0:r())||(Yt(d)?d.getTarget(M.current):d==null?void 0:d.target)),g.current=s.position.distanceTo(Ht),Te.copy(s.quaternion),Wt.copy(h).multiplyScalar(g.current).add(Ht),ut.lookAt(Wt),dt.copy(ut.quaternion),S()},[d,s,r,S]);Me((h,k)=>{if(p.current&&f.current){var z;if(E.current)if(Te.angleTo(dt)<.01)E.current=!1,Co(d)&&s.up.copy(b.current);else{const T=k*To;Te.rotateTowards(dt,T),s.position.set(0,0,1).applyQuaternion(Te).multiplyScalar(g.current).add(M.current),s.up.set(0,1,0).applyQuaternion(Te).normalize(),s.quaternion.copy(Te),Yt(d)&&d.setPosition(s.position.x,s.position.y,s.position.z),e?e():d&&d.update(k),S()}Ft.copy(s.matrix).invert(),(z=f.current)==null||z.quaternion.setFromRotationMatrix(Ft)}});const v=l.useMemo(()=>({tweenCamera:y}),[y]),[A,x]=t,P=o.endsWith("-center")?0:o.endsWith("-left")?-u.width/2+A:u.width/2-A,_=o.startsWith("center-")?0:o.startsWith("top-")?u.height/2-x:-u.height/2+x;return l.createElement(Ao,{renderPriority:n},l.createElement(on.Provider,{value:v},l.createElement(Po,{makeDefault:!0,ref:p,position:[0,0,200]}),l.createElement("group",{ref:f,position:[P,_,0]},a)))};function ft({scale:o=[.8,.05,.05],color:t,rotation:n}){return l.createElement("group",{rotation:n},l.createElement("mesh",{position:[.4,0,0]},l.createElement("boxGeometry",{args:o}),l.createElement("meshBasicMaterial",{color:t,toneMapped:!1})))}function Ce({onClick:o,font:t,disabled:n,arcStyle:e,label:r,labelColor:a,axisHeadScale:u=1,...s}){const d=j(b=>b.gl),S=l.useMemo(()=>{const b=document.createElement("canvas");b.width=64,b.height=64;const y=b.getContext("2d");return y.beginPath(),y.arc(32,32,16,0,2*Math.PI),y.closePath(),y.fillStyle=e,y.fill(),r&&(y.font=t,y.textAlign="center",y.fillStyle=a,y.fillText(r,32,41)),new Gn(b)},[e,r,a,t]),[f,p]=l.useState(!1),E=(r?1:.75)*(f?1.2:1)*u,g=b=>{b.stopPropagation(),p(!0)},M=b=>{b.stopPropagation(),p(!1)};return l.createElement("sprite",V({scale:E,onPointerOver:n?void 0:g,onPointerOut:n?void 0:o||M},s),l.createElement("spriteMaterial",{map:S,"map-anisotropy":d.capabilities.getMaxAnisotropy()||1,alphaTest:.3,opacity:r?1:.75,toneMapped:!1}))}const Do=({hideNegativeAxes:o,hideAxisHeads:t,disabled:n,font:e="18px Inter var, Arial, sans-serif",axisColors:r=["#ff2060","#20df80","#2080ff"],axisHeadScale:a=1,axisScale:u,labels:s=["X","Y","Z"],labelColor:d="#000",onClick:S,...f})=>{const[p,E,g]=r,{tweenCamera:M}=_o(),b={font:e,disabled:n,labelColor:d,onClick:S,axisHeadScale:a,onPointerDown:n?void 0:y=>{M(y.object.position),y.stopPropagation()}};return l.createElement("group",V({scale:40},f),l.createElement(ft,{color:p,rotation:[0,0,0],scale:u}),l.createElement(ft,{color:E,rotation:[0,0,Math.PI/2],scale:u}),l.createElement(ft,{color:g,rotation:[0,-Math.PI/2,0],scale:u}),!t&&l.createElement(l.Fragment,null,l.createElement(Ce,V({arcStyle:p,position:[1,0,0],label:s[0]},b)),l.createElement(Ce,V({arcStyle:E,position:[0,1,0],label:s[1]},b)),l.createElement(Ce,V({arcStyle:g,position:[0,0,1],label:s[2]},b)),!o&&l.createElement(l.Fragment,null,l.createElement(Ce,V({arcStyle:p,position:[-1,0,0]},b)),l.createElement(Ce,V({arcStyle:E,position:[0,-1,0]},b)),l.createElement(Ce,V({arcStyle:g,position:[0,0,-1]},b)))))},zo=-4.9,jo=l.memo(function({organ:t,selected:n,choose:e,severity:r,targets:a,planes:u,reduced:s,dim:d,showLabels:S,onHover:f,demoImagingOpen:p}){const E=Vn(),g=l.useMemo(()=>{var h;return((h=E[t.id])==null?void 0:h.clone())||Zn(t)},[t,E]),M=l.useRef(),[b,y]=l.useState(!1);c.useEffect(()=>()=>g.dispose(),[g]);const v=r==="none"?t.color:mt[r],A=n||r==="danger";Me(({clock:h})=>{M.current&&(M.current.emissiveIntensity=r==="danger"&&!s?.22+.12*Math.sin(h.elapsedTime*2):r==="none"?.02:.18)});const x=l.useMemo(()=>[...(a||[]).flatMap(k=>k.sources.filter(z=>z.type==="lab"))].sort((k,z)=>(k.date||"").localeCompare(z.date||"")).at(-1),[a]),P=l.useMemo(()=>pn(a),[a]),_=Math.max(0,((a==null?void 0:a.length)||0)-1);return c.createElement("group",{position:t.p},c.createElement("mesh",{name:t.id,scale:t.s,geometry:g,onClick:h=>{h.stopPropagation(),e(t.id)},onDoubleClick:h=>{h.stopPropagation(),e(t.id)},onPointerOver:h=>{h.stopPropagation(),y(!0),f==null||f(t.id)},onPointerOut:h=>{y(!1),f==null||f(null)}},c.createElement("meshStandardMaterial",{ref:M,color:v,emissive:v,roughness:.63,transparent:!0,opacity:n?.94:d?.2:.46,depthWrite:n,side:be,clippingPlanes:u})),(n||b)&&c.createElement("mesh",{scale:t.s.map(h=>h*1.05),geometry:g,raycast:()=>null},c.createElement("meshBasicMaterial",{color:n?"#a8f9ed":"#eaf6ff",transparent:!0,opacity:n?.2:.15,wireframe:!0,clippingPlanes:u})),!n&&r==="caution"&&c.createElement("mesh",{scale:t.s.map(h=>h*1.028),geometry:g,raycast:()=>null},c.createElement("meshBasicMaterial",{color:mt.caution,transparent:!0,opacity:.17,wireframe:!0,clippingPlanes:u})),A&&c.createElement(c.Fragment,null,c.createElement(nn,{points:[[0,0,0],[.55,.3,.2],[.95,.3,.2]],color:v,lineWidth:1}),c.createElement(st,{position:[.96,.3,.2],style:{pointerEvents:"none"},distanceFactor:9},c.createElement("div",{className:"an-marker"},c.createElement("b",null,t.en),c.createElement("span",null,t.ko," · ",hn[r]),P&&c.createElement(c.Fragment,null,c.createElement("em",null,P.title),c.createElement("small",null,P.reason)),_>0&&c.createElement("small",{className:"an-marker-more"},"+",_,"건 더 · 상세 패널 참고")))),!A&&b&&c.createElement(st,{position:[0,t.s[1]*1.2+.12,0],style:{pointerEvents:"none"},distanceFactor:9},c.createElement("div",{className:"an-tooltip"},c.createElement("b",null,t.ko),c.createElement("small",null,t.en),P?c.createElement(c.Fragment,null,c.createElement("span",null,P.title),c.createElement("small",null,P.reason)):c.createElement("span",null,"Clinical signals: ",(a||[]).length),_>0&&c.createElement("small",{className:"an-marker-more"},"+",_,"건 더"),x&&c.createElement("span",null,"Latest related lab: ",x.name),c.createElement("span",null,"Imaging: ",p?"데모 참고 영상":"참고 영상 없음"))),!A&&!b&&S&&c.createElement(st,{position:[0,t.s[1]*1.15+.08,0],style:{pointerEvents:"none"},distanceFactor:9},c.createElement("div",{className:"an-label"},t.ko)))}),bt="#d9b593",Ee="#eee7d8";function F({shape:o,args:t,position:n,rotation:e,planes:r,opacity:a=.11,color:u=bt}){return c.createElement("mesh",{position:n,rotation:e,raycast:()=>null},o==="sphere"&&c.createElement("sphereGeometry",{args:t}),o==="cylinder"&&c.createElement("cylinderGeometry",{args:t}),o==="box"&&c.createElement("boxGeometry",{args:t}),o==="torus"&&c.createElement("torusGeometry",{args:t}),c.createElement("meshPhysicalMaterial",{color:u,transparent:!0,opacity:a,roughness:.38,depthWrite:!1,clippingPlanes:r,side:be}))}function Io({profile:o,planes:t,opacity:n}){const e=l.useMemo(()=>Xn(o.torso),[o]);return c.useEffect(()=>()=>e.dispose(),[e]),c.createElement("mesh",{geometry:e,scale:[1,1,o.depthRatio],raycast:()=>null},c.createElement("meshPhysicalMaterial",{color:bt,transparent:!0,opacity:n,roughness:.36,depthWrite:!1,clippingPlanes:t,side:be}))}function Uo({planes:o,opacity:t}){const n=Qe();return c.createElement("group",{position:me.position,rotation:me.rotation,scale:me.scale},c.createElement("mesh",{name:"skinBody",geometry:n.skinBody,raycast:()=>null},c.createElement("meshPhysicalMaterial",{color:bt,transparent:!0,opacity:t,roughness:.36,depthWrite:!1,clippingPlanes:o,side:be})))}function Gt({side:o,planes:t,limbScale:n,shoulderX:e,hipX:r}){const a=o,u=n,s=e/1.22,d=r/.55;return c.createElement("group",null,c.createElement(F,{shape:"sphere",args:[.19*u,16,12],position:[a*1.22*s,2.02,-.05],planes:t}),c.createElement(F,{shape:"cylinder",args:[.18*u,.15*u,1.05,16],position:[a*1.28*s,1.45,-.03],rotation:[0,0,a*-.09],planes:t}),c.createElement(F,{shape:"sphere",args:[.15*u,16,12],position:[a*1.34*s,.9,0],planes:t}),c.createElement(F,{shape:"cylinder",args:[.14*u,.105*u,1,16],position:[a*1.3*s,.35,.02],rotation:[0,0,a*-.05],planes:t}),c.createElement(F,{shape:"sphere",args:[.14*u,16,12],position:[a*1.27*s,-.28,.05],planes:t}),c.createElement(F,{shape:"sphere",args:[.26*u,16,12],position:[a*.52*d,-1.55,-.05],planes:t}),c.createElement(F,{shape:"cylinder",args:[.27*u,.21*u,1.55,16],position:[a*.55*d,-2.35,-.05],planes:t}),c.createElement(F,{shape:"sphere",args:[.19*u,16,12],position:[a*.56*d,-3.12,-.03],planes:t}),c.createElement(F,{shape:"cylinder",args:[.19*u,.13*u,1.5,16],position:[a*.57*d,-3.9,0],planes:t}),c.createElement(F,{shape:"box",args:[.28*u,.16*u,.62*u],position:[a*.58*d,-4.68,.22],planes:t}))}function Bo({planes:o,profile:t}){const n=t.shoulderX/1.22,e=t.hipX/.55;return c.createElement("group",null,c.createElement(F,{shape:"sphere",args:[.42*t.headScale,16,12],position:[0,3.46,.02],color:Ee,opacity:.5,planes:o}),[2.35,2,1.65,1.3].map((r,a)=>c.createElement(F,{key:r,shape:"torus",args:[.6-a*.03,.045,8,20],position:[0,r,-.05],rotation:[Math.PI/2,0,0],color:Ee,opacity:.55,planes:o})),c.createElement(F,{shape:"torus",args:[.48,.08,8,20],position:[0,-1.55,-.05],rotation:[Math.PI/2,0,0],color:Ee,opacity:.55,planes:o}),[-1,1].map(r=>c.createElement("group",{key:r},c.createElement(F,{shape:"cylinder",args:[.055,.05,1,10],position:[r*1.28*n,1.45,-.03],rotation:[0,0,r*-.09],color:Ee,opacity:.6,planes:o}),c.createElement(F,{shape:"cylinder",args:[.045,.04,.95,10],position:[r*1.3*n,.4,.02],rotation:[0,0,r*-.05],color:Ee,opacity:.6,planes:o}),c.createElement(F,{shape:"cylinder",args:[.09,.07,1.5,10],position:[r*.55*e,-2.35,-.05],color:Ee,opacity:.6,planes:o}),c.createElement(F,{shape:"cylinder",args:[.07,.05,1.45,10],position:[r*.57*e,-3.9,0],color:Ee,opacity:.6,planes:o}))))}function ko({planes:o,profile:t}){const n=Qe();return n.skeletonFull?c.createElement("group",{position:me.position,rotation:me.rotation,scale:me.scale},c.createElement("mesh",{geometry:n.skeletonFull,raycast:()=>null},c.createElement("meshStandardMaterial",{color:Ee,roughness:.55,transparent:!0,opacity:.7,depthWrite:!1,clippingPlanes:o,side:be}))):c.createElement(Bo,{planes:o,profile:t})}function No({planes:o}){const t=Qe();return t.vascularFull?c.createElement("group",{position:me.position,rotation:me.rotation,scale:me.scale},c.createElement("mesh",{geometry:t.vascularFull,raycast:()=>null},c.createElement("meshStandardMaterial",{color:"#a83f4d",roughness:.5,transparent:!0,opacity:.4,depthWrite:!1,clippingPlanes:o,side:be}))):null}function Fo({selected:o,choose:t,hidden:n,data:e,planes:r,reduced:a,sex:u,heightCm:s,weightKg:d,bodyOpacity:S,showLabels:f,onHoverOrgan:p,demoImagingOpen:E}){const g=mn[u||"unspecified"],M=Math.min(1,Math.max(0,(S??55)/100)),b=Qe(),y=b.skinBody?fn(u,s,d):{x:1,y:1,z:1};return c.createElement("group",{position:[0,zo*(1-y.y),0],scale:[y.x,y.y,y.z]},!n.body&&(b.skinBody?c.createElement(Uo,{planes:r,opacity:M}):c.createElement(c.Fragment,null,c.createElement(Io,{profile:g,planes:r,opacity:M}),c.createElement(F,{shape:"sphere",args:[.58*g.headScale,32,24],position:[0,3.5,.04],opacity:M,planes:r}),c.createElement(F,{shape:"cylinder",args:[.2,.28,.5,24],position:[0,2.92,-.05],opacity:M,planes:r}),c.createElement(Gt,{side:-1,planes:r,limbScale:g.limbScale,shoulderX:g.shoulderX,hipX:g.hipX}),c.createElement(Gt,{side:1,planes:r,limbScale:g.limbScale,shoulderX:g.shoulderX,hipX:g.hipX}))),!n.skeleton&&c.createElement(ko,{planes:r,profile:g}),!n.vascularFull&&c.createElement(No,{planes:r}),Xt.filter(v=>!n[v.id]).map(v=>{const A=Pt(e,v.group);return c.createElement(jo,{key:v.id,organ:v,selected:o===v.id,dim:!!o&&o!==v.id,choose:t,severity:Ot(A),targets:A,planes:r,reduced:a,showLabels:f,onHover:p,demoImagingOpen:E})}),!n.spine&&Array.from({length:18},(v,A)=>c.createElement("mesh",{key:A,position:[0,-1.49+A*.218,-.56],raycast:()=>null},c.createElement("cylinderGeometry",{args:[.2,.19,.15,12]}),c.createElement("meshStandardMaterial",{color:"#c2ced0",transparent:!0,opacity:o==="spine"?.9:.25,clippingPlanes:r}))),!n.vascular&&[-1,1].map(v=>c.createElement(nn,{key:v,points:[[0,-.25,-.1],[v*.3,-.3,-.15],[v*.6,-.36,-.22]],color:mt[Ot(Pt(e,"systemic"))],lineWidth:3})))}class Ho extends c.Component{constructor(){super(...arguments);Mt(this,"state",{failed:!1})}static getDerivedStateFromError(){return{failed:!0}}render(){return this.state.failed?c.createElement("div",{className:"an-fallback"},"3D rendering is unavailable on this device.",c.createElement("br",null),"장기 목록에서 관련 근거를 확인할 수 있습니다."):this.props.children}}function Wo(o){const{mode:t,position:n,clipping:e,view:r,selected:a,reduced:u}=o,s=l.useRef(),d=l.useRef(null),{camera:S,gl:f}=j(),p=gn[t],E=yn(t,n),g=l.useMemo(()=>new C(...[0,1,2].map(v=>v===p?-1:0)),[p]),M=l.useMemo(()=>e?[new Zt(g,E)]:[],[e,g,E]),b=[0,0,0];b[p]=E;const y=t==="axial"?[-Math.PI/2,0,0]:t==="sagittal"?[0,Math.PI/2,0]:[0,0,0];return l.useEffect(()=>{f.localClippingEnabled=!0},[f]),l.useEffect(()=>{var x;const v=new C(...r.kind==="focus"?((x=Xt.find(P=>P.id===a))==null?void 0:x.p)||[0,.8,0]:[0,.8,0]),A={front:[0,0,9],back:[0,0,-9],left:[9,0,0],right:[-9,0,0],top:[0,9,.01],reset:[3,1.4,9],focus:[0,.2,4.4]};d.current={target:v,position:v.clone().add(new C(...A[r.kind]||A.reset))}},[r,a]),Me((v,A)=>{const x=d.current;if(!x||!s.current)return;const P=u?1:1-Math.exp(-A*7);S.position.lerp(x.position,P),s.current.target.lerp(x.target,P),s.current.update(),S.position.distanceTo(x.position)<.01&&(d.current=null)}),c.createElement(c.Fragment,null,c.createElement("color",{attach:"background",args:["#0c1a25"]}),c.createElement("ambientLight",{intensity:1.1}),c.createElement("directionalLight",{position:[3,5,5],intensity:2}),c.createElement("directionalLight",{position:[-4,2,-3],color:"#84cadc",intensity:1.5}),c.createElement(Fo,{...o,planes:M}),c.createElement("mesh",{position:b,rotation:y,raycast:()=>null},c.createElement("planeGeometry",{args:t==="axial"?[3.6,2.2]:[t==="sagittal"?2.2:3.6,7.6]}),c.createElement("meshBasicMaterial",{color:"#6bd5ca",transparent:!0,opacity:.12,side:be,depthWrite:!1})),c.createElement("gridHelper",{args:[8,16,"#284452","#182f3b"],position:[0,-1.95,0]}),c.createElement(Oo,{ref:s,makeDefault:!0,minDistance:2,maxDistance:16,enableDamping:!u,onStart:()=>{d.current=null}}),c.createElement(Ro,{alignment:"bottom-right",margin:[48,48]},c.createElement(Do,{axisColors:["#7d9ea9","#7d9ea9","#7d9ea9"],labelColor:"#07121b"})))}function $o(o){const[t,n]=l.useState(!1);return c.createElement(Ho,null,t?c.createElement("div",{className:"an-fallback"},"3D rendering is unavailable on this device.",c.createElement("button",{onClick:()=>n(!1)},"다시 시도")):c.createElement(to,{dpr:[1,1.5],camera:{position:[3,2.2,9],fov:43},gl:{antialias:!0,localClippingEnabled:!0},fallback:c.createElement("div",{className:"an-fallback"},"3D rendering is unavailable on this device."),onCreated:({gl:e})=>{e.domElement.addEventListener("webglcontextlost",r=>{r.preventDefault(),n(!0)},{once:!0})}},c.createElement(Wo,{...o})))}export{$o as default};

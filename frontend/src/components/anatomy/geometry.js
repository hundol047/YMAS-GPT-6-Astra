import {SphereGeometry,LatheGeometry,Vector2} from 'three';
import {organs,sliceAxes,sliceValue} from '../../data/anatomyMap';
export function makeGeometry(organ){
 const geo=new SphereGeometry(1,48,32),pos=geo.attributes.position;
 for(let i=0;i<pos.count;i++){
  let x=pos.getX(i),y=pos.getY(i),z=pos.getZ(i);
  if(organ.group==='kidneys'){x*=1-.28*Math.exp(-y*y*8)*(x*(organ.id==='leftKidney'?-1:1)>0?1:0);x+=.14*y*y;}
  if(organ.group==='lungs'){x*=.8-.2*y;z*=.91+.09*y;y+=.09*x;}
  if(organ.group==='heart'){x*=.8+.23*y;x-=.22*y;y-=.12*Math.abs(x);}
  if(organ.group==='liver'){y*=.82+.24*(-x);y+=.19*x;}
  if(organ.group==='stomach'){x+=.3*Math.sin(y*2);x*=.85-.14*y;}
  if(organ.group==='brain'){const r=1+.025*Math.sin(x*32+z*13)*Math.cos(y*27);x*=r;y*=r;z*=r;x+=Math.sign(x)*.025;}
  if(organ.group==='pancreas'){x*=1.4;y*=.4;x+=.25*Math.sin(y*1.5);z*=.7;}
  if(organ.group==='spleen'){x*=.75-.15*y;y*=1.15;z*=.8;x+=.08*y*y;}
  if(organ.group==='bladder'){y=y<0?y*.5:y*1.1;x*=1-.1*y;}
  if(organ.group==='intestine'){const r=1+.07*Math.sin(x*9+z*7+y*5);x*=r;y*=r*.75;z*=r;}
  pos.setXYZ(i,x,y,z);
 }
 geo.computeVertexNormals();return geo;
}
// Continuous chest->pelvis silhouette for the procedural body shell: a lathe (surface of
// revolution) through the sex-profile control points in anatomyMap.BODY_PROFILES, flattened
// front-to-back by the caller via mesh scale. This replaces stacking separate primitives so the
// torso reads as one organic surface instead of glued spheres/cylinders.
export function buildTorsoLathe(points,segments=40){
 const sorted=[...points].sort((a,b)=>a[0]-b[0]);
 const verts=sorted.map(([y,r])=>new Vector2(Math.max(r,.001),y));
 const geo=new LatheGeometry(verts,segments);
 geo.computeVertexNormals();
 return geo;
}

// Intersect the SAME procedural/asset organ surfaces with a slice plane. Shared by the single-pane
// AnatomySlicePanel and the 3-pane demo AnatomyImagingPanel so there is exactly one implementation
// of this math. This is a surface reference, never generated CT pixels or patient imaging.
export function crossSectionPaths(mode,value,assets){
 const axis=sliceAxes[mode],axes=mode==='axial'?[0,2]:mode==='coronal'?[0,1]:[2,1],v=sliceValue(mode,value);
 return organs.map(o=>{
  const g=assets?.[o.id]?.clone()||makeGeometry(o),pos=g.attributes.position,indices=g.index.array,segments=[];
  for(let i=0;i<indices.length;i+=3){
   const vertices=[0,1,2].map(j=>[0,1,2].map(k=>pos.array[indices[i+j]*3+k]*o.s[k]+o.p[k]));
   const hits=[];
   for(let j=0;j<3;j++){const a=vertices[j],b=vertices[(j+1)%3];if((a[axis]<v)===(b[axis]<v))continue;const t=(v-a[axis])/(b[axis]-a[axis]);hits.push(a.map((c,k)=>c+t*(b[k]-c)));}
   if(hits.length===2){const point=p=>`${150+p[axes[0]]*54},${(mode==='axial'?115:190)-p[axes[1]]*54}`;segments.push(`M${point(hits[0])}L${point(hits[1])}`);}
  }
  g.dispose();return {organ:o,path:segments.join(' ')};
 });
}
// Inverse of sliceValue: a raw model coordinate on physical axis 0/1/2 (X/Y/Z) back to the
// -100..100 slider value for whichever mode slices along that axis.
const AXIS_TO_MODE={0:'sagittal',1:'axial',2:'coronal'};
export {AXIS_TO_MODE};
export function modelToSlider(axisIndex,modelValue){
 const mode=AXIS_TO_MODE[axisIndex];
 const raw=mode==='axial'?(modelValue-.9)/.033:modelValue/.014;
 return Math.max(-100,Math.min(100,Math.round(raw)));
}

import {SphereGeometry} from 'three';
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
  pos.setXYZ(i,x,y,z);
 }
 geo.computeVertexNormals();return geo;
}

import React from 'react';
import {Eye,EyeOff} from 'lucide-react';
import {organs,colors,labels,targetsFor,severityFor} from '../../data/anatomyMap';
export default function AnatomyOrganList({selected,choose,hidden,setHidden,data}){
 return <aside className="an-organ-list"><h3>ANATOMY <span>10 LAYERS</span></h3>{organs.map(o=>{const severity=severityFor(targetsFor(data,o.group));return <div key={o.id} className={'an-organ '+(selected===o.id?'active':'')}><button aria-label={o.ko+(hidden[o.id]?' 표시':' 숨기기')} aria-pressed={!hidden[o.id]} onClick={()=>setHidden(h=>({...h,[o.id]:!h[o.id]}))}>{hidden[o.id]?<EyeOff size={15}/>:<Eye size={15}/>}</button><button aria-pressed={selected===o.id} onClick={()=>choose(o.id)}><b>{o.ko}</b><span>{o.en}</span><small style={{color:colors[severity]}}>{labels[severity]}</small></button></div>})}<p>좌·우는 환자 기준입니다.</p></aside>;
}

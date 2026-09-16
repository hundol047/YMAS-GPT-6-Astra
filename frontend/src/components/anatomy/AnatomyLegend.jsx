import React from 'react';
import {colors,legendCopy} from '../../data/anatomyMap';
export default function AnatomyLegend(){
 return <div className="an-legend">
 {legendCopy.map(l=><span key={l.key} title={l.desc}><i style={{background:colors[l.key]}}/>{l.title}</span>)}
 </div>;
}

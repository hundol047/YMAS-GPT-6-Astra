import React from 'react';
import {colors,labels} from '../../data/anatomyMap';
export default function AnatomyLegend(){return <div className="an-legend">{['danger','caution','info','none'].map(s=><span key={s}><i style={{background:colors[s]}}/>{labels[s]}</span>)}</div>}

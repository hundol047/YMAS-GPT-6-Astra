import React from 'react';
import {organs,colors,labels,targetsFor,severityFor} from '../../data/anatomyMap';
export default function AnatomyRiskPanel({selected,data,analysis,onOpenAlert,focusAlert}){
 const organ=organs.find(o=>o.id===selected),targets=targetsFor(data,organ?.group),severity=severityFor(targets);
 return <section className="an-risk-panel"><h3>ANATOMICAL RISK</h3><h2>{organ?.ko||'장기를 선택하십시오'}</h2><p>{organ?.en}</p>{organ&&<strong style={{color:colors[severity]}}>{labels[severity]}</strong>}
 {targets.map((t,i)=><article key={`${t.alert_id}-${i}`} className={focusAlert===t.alert_id?'an-linked':''}><b>{t.title}</b><p>{t.reason}</p><dl>{t.sources.filter(s=>s.type!=='alert').map((s,j)=><React.Fragment key={j}><dt>{s.type}</dt><dd>{s.name}{s.value!=null?` · ${s.value} ${s.unit||''}`:''}{s.date?` (${s.date})`:''}</dd></React.Fragment>)}</dl>{t.alert_id&&<button onClick={()=>{const a=analysis?.alerts.find(a=>a.id===t.alert_id);if(a)onOpenAlert(a,analysis.analysis_id)}}>관련 경고 보기 ↗</button>}</article>)}
 {organ&&!targets.length&&<p>현재 분석에서 이 장기와 연결된 신호가 없습니다. 정상 판정을 의미하지 않습니다.</p>}
 <p className="an-note">관련성은 규칙으로 연결합니다. AI Risk Score를 장기별 확률로 분해하지 않습니다.</p></section>;
}

// Original procedural reference anatomy, model units (not patient millimetres).
// Patient right is negative X; anterior is positive Z; superior is positive Y.
export const organs = [
 {id:'brain',group:'brain',en:'Brain',ko:'뇌',p:[0,3.55,0],s:[.57,.46,.47],color:'#b9a5bd'},
 {id:'rightLung',group:'lungs',en:'Right lung',ko:'우측 폐',p:[-.68,1.67,0],s:[.48,.89,.44],color:'#d59caa'},
 {id:'leftLung',group:'lungs',en:'Left lung',ko:'좌측 폐',p:[.68,1.67,0],s:[.46,.86,.42],color:'#d59caa'},
 {id:'heart',group:'heart',en:'Heart',ko:'심장',p:[.17,1.36,.4],s:[.37,.51,.32],color:'#bc6675'},
 {id:'liver',group:'liver',en:'Liver',ko:'간',p:[-.43,.39,.18],s:[.87,.38,.51],color:'#a77b86'},
 {id:'stomach',group:'stomach',en:'Stomach',ko:'위',p:[.61,.17,.26],s:[.35,.52,.35],color:'#d3b394'},
 {id:'rightKidney',group:'kidneys',en:'Right kidney',ko:'우측 신장',p:[-.61,-.46,-.23],s:[.24,.4,.25],color:'#bd8e7d'},
 {id:'leftKidney',group:'kidneys',en:'Left kidney',ko:'좌측 신장',p:[.61,-.35,-.23],s:[.24,.4,.25],color:'#bd8e7d'},
 {id:'vascular',group:'systemic',en:'Vascular / systemic',ko:'혈관 · 전신',p:[0,.35,-.1],s:[.09,1.85,.09],color:'#ae777b'},
 {id:'spine',group:'skeleton',en:'Spine',ko:'척추',p:[0,.48,-.56],s:[.16,2.15,.16],color:'#bdc8ca'}
];
export const colors={danger:'#ef7278',caution:'#edb45f',info:'#69d9d4',none:'#8ba9ad'};
export const labels={danger:'위험 관련성',caution:'주의 관련성',info:'기록 관련성',none:'연결된 신호 없음'};
export const DISCLAIMER='3D 강조 영역은 AI가 환자 기록과 위험 신호를 해부학적 영역에 연결한 임상 관련성 시각화이며, 실제 병변 위치 또는 영상진단 결과를 의미하지 않습니다.';
export function targetsFor(data,group){return (group==='systemic'?data?.systemic:data?.targets?.filter(t=>t.organ_id===group))||[]}
export function severityFor(targets){return ['danger','caution','info'].find(s=>targets.some(t=>t.severity===s))||'none'}
export const sliceAxes={axial:1,coronal:2,sagittal:0};
export function sliceValue(mode,value){return mode==='axial'? .9+value*.033:value*.014}

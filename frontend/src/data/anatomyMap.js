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
 {id:'spine',group:'skeleton',en:'Spine',ko:'척추',p:[0,.48,-.56],s:[.16,2.15,.16],color:'#bdc8ca'},
 {id:'pancreas',group:'pancreas',en:'Pancreas',ko:'췌장',p:[.05,-.02,-.12],s:[.46,.15,.2],color:'#d7ab8c'},
 {id:'spleen',group:'spleen',en:'Spleen',ko:'비장',p:[.78,.14,-.08],s:[.2,.28,.2],color:'#8a5566'},
 {id:'bladder',group:'bladder',en:'Bladder',ko:'방광',p:[0,-1.58,.16],s:[.26,.22,.24],color:'#c9b16a'},
 {id:'smallIntestine',group:'intestine',en:'Small intestine',ko:'소장',p:[0,-.68,.16],s:[.5,.36,.36],color:'#d99aa0'},
 {id:'largeIntestine',group:'intestine',en:'Large intestine',ko:'대장',p:[0,-.8,.1],s:[.72,.5,.46],color:'#c98f95'}
];
// Layer-list rows shown above the organ rows. Purely visibility toggles for the
// procedural body/skeleton shell -- never deleted, never affects patient data.
export const pseudoLayers=[
 {id:'body',ko:'신체',en:'Body'},
 {id:'skeleton',ko:'골격',en:'Skeleton'}
];
export const colors={danger:'#ef7278',caution:'#edb45f',info:'#69d9d4',imaging:'#b48be0',none:'#8ba9ad'};
export const labels={danger:'위험 관련성',caution:'주의 관련성',info:'기록 관련성',imaging:'영상 소견',none:'연결된 신호 없음'};
export const legendCopy=[
 {key:'info',title:'Cyan · 임상 연관',desc:'환자 기록에 근거한 관련성(Clinical association)'},
 {key:'caution',title:'Amber · 검토 권고',desc:'검토가 필요한 신호(Review recommended)'},
 {key:'danger',title:'Red · 고위험 신호',desc:'우선순위 높은 안전 신호(High-priority safety signal)'},
 {key:'imaging',title:'Purple · 영상 소견',desc:'실제 segmentation이 있을 때만 표시(Imaging-derived region)'}
];
export const DISCLAIMER='3D 강조 영역은 AI가 환자 기록과 위험 신호를 해부학적 영역에 연결한 임상 관련성 시각화이며, 실제 병변 위치 또는 영상진단 결과를 의미하지 않습니다.';
export function targetsFor(data,group){return (group==='systemic'?data?.systemic:data?.targets?.filter(t=>t.organ_id===group))||[]}
export function severityFor(targets){return ['danger','caution','info'].find(s=>targets.some(t=>t.severity===s))||'none'}
export const sliceAxes={axial:1,coronal:2,sagittal:0};
export function sliceValue(mode,value){return mode==='axial'? .9+value*.033:value*.014}

// Explicit sex support. Anything outside this set -> neutral fallback + "unavailable" notice,
// never guessed. Values match the free-text Patient.sex field already used across the app.
export const SUPPORTED_SEXES=['male','female'];
export function resolveSex(raw){return SUPPORTED_SEXES.includes(raw)?raw:null}
export const SEX_LABELS={male:'남성',female:'여성',unspecified:'성별 미상'};

// Body-shell silhouette control points for the procedural (non-GLB) reference figure.
// [y, radius] pairs, chest->pelvis, revolved into a lathe and flattened front-to-back by depthRatio.
// These are anatomical-reference proportion differences (shoulder:hip ratio, waist taper), not a
// literal scan -- see docs/ANATOMY.md for the GLB replacement path when a licensed asset is available.
export const BODY_PROFILES={
 male:{
  torso:[[2.86,1.03],[2.55,1.0],[2.1,.95],[1.4,.9],[.6,.79],[-.15,.73],[-.7,.75],[-1.2,.82],[-1.55,.88],[-1.85,.5]],
  depthRatio:.58,limbScale:1.06,headScale:1.0,shoulderX:1.24,hipX:.58
 },
 female:{
  torso:[[2.86,.9],[2.55,.88],[2.1,.85],[1.4,.79],[.6,.63],[-.15,.5],[-.7,.58],[-1.2,.8],[-1.55,.95],[-1.85,.53]],
  depthRatio:.55,limbScale:.9,headScale:.95,shoulderX:1.08,hipX:.66
 },
 unspecified:{
  torso:[[2.86,.97],[2.55,.94],[2.1,.9],[1.4,.85],[.6,.71],[-.15,.62],[-.7,.67],[-1.2,.81],[-1.55,.91],[-1.85,.52]],
  depthRatio:.565,limbScale:.98,headScale:.975,shoulderX:1.16,hipX:.62
 }
};

// Fixed organ<->lab reference table for the organ detail panel. Explicit and reviewable --
// never inferred at runtime. Only labs actually present on the patient are ever shown.
export const ORGAN_LABS={
 kidneys:['Creatinine','eGFR','Potassium'],
 liver:['AST','ALT'],
 heart:['INR'],
 pancreas:['Glucose'],
 systemic:['INR','Glucose']
};

// Fixed ICD-10 reference for the demo condition vocabulary used in backend/data/patients.json
// and rules.json. Unmapped conditions show "코드 매핑 없음" rather than a guessed code.
export const CONDITION_ICD10={
 '고혈압':'I10','만성신부전':'N18.9','고칼륨혈증':'E87.5','심방세동':'I48.91'
};

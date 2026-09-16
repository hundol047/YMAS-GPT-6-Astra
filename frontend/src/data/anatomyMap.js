// Original procedural reference anatomy, model units (not patient millimetres).
// Patient right is negative X; anterior is positive Z; superior is positive Y.
//
// p/s for the 10 organs with real BodyParts3D meshes (brain, rightLung, leftLung, heart, liver,
// stomach, rightKidney, leftKidney, vascular, spine) are measured, not hand-picked: each organ's
// raw (unnormalized) bounding box was read from anatomy.glb and run through the exact same
// rotation+scale as extrasTransform, so a real organ's final rendered size and position match its
// true proportions and true placement in the same specimen as the real skin/skeleton/vascular
// mesh (see extrasTransform below and AnatomyAssets.jsx's per-organ 2-unit-cube normalization,
// which this cancels out exactly when s = real_size_mm * extrasTransform.scale / 2). These same
// p/s values also drive the procedural fallback shape for these 10 organs when no GLB loads.
// pancreas/spleen (no real mesh) keep hand-picked shapes but were shifted by stomach's real-data
// delta so they stay adjacent to it instead of separating; bladder/intestines are unaffected
// (lower abdomen/pelvis, independent of the upper-abdominal reposition).
export const organs = [
 {id:'brain',group:'brain',en:'Brain',ko:'뇌',p:[-0.004,3.588,-0.114],s:[0.368,0.433,0.469],color:'#b9a5bd'},
 {id:'rightLung',group:'lungs',en:'Right lung',ko:'우측 폐',p:[-0.348,1.979,0.026],s:[0.319,0.628,0.469],color:'#d59caa'},
 {id:'leftLung',group:'lungs',en:'Left lung',ko:'좌측 폐',p:[0.346,1.969,0.022],s:[0.319,0.631,0.470],color:'#d59caa'},
 {id:'heart',group:'heart',en:'Heart',ko:'심장',p:[0.112,1.914,0.114],s:[0.301,0.275,0.278],color:'#bc6675'},
 {id:'liver',group:'liver',en:'Liver',ko:'간',p:[-0.059,1.415,0.147],s:[0.118,0.195,0.131],color:'#a77b86'},
 {id:'stomach',group:'stomach',en:'Stomach',ko:'위',p:[0.200,1.244,0.190],s:[0.351,0.305,0.295],color:'#d3b394'},
 {id:'rightKidney',group:'kidneys',en:'Right kidney',ko:'우측 신장',p:[-0.308,0.829,-0.069],s:[0.149,0.273,0.123],color:'#bd8e7d'},
 {id:'leftKidney',group:'kidneys',en:'Left kidney',ko:'좌측 신장',p:[0.322,0.926,-0.113],s:[0.150,0.277,0.106],color:'#bd8e7d'},
 {id:'vascular',group:'systemic',en:'Vascular / systemic',ko:'혈관 · 전신',p:[0.029,1.995,0.002],s:[0.191,1.542,0.297],color:'#ae777b'},
 {id:'spine',group:'skeleton',en:'Spine',ko:'척추',p:[-0.004,1.327,-0.248],s:[0.308,1.730,0.320],color:'#bdc8ca'},
 {id:'pancreas',group:'pancreas',en:'Pancreas',ko:'췌장',p:[.05,1.054,-.12],s:[.46,.15,.2],color:'#d7ab8c'},
 {id:'spleen',group:'spleen',en:'Spleen',ko:'비장',p:[.78,1.214,-.08],s:[.2,.28,.2],color:'#8a5566'},
 {id:'bladder',group:'bladder',en:'Bladder',ko:'방광',p:[0,-1.58,.16],s:[.26,.22,.24],color:'#c9b16a'},
 {id:'smallIntestine',group:'intestine',en:'Small intestine',ko:'소장',p:[0,-.68,.16],s:[.5,.36,.36],color:'#d99aa0'},
 {id:'largeIntestine',group:'intestine',en:'Large intestine',ko:'대장',p:[0,-.8,.1],s:[.72,.5,.46],color:'#c98f95'}
];
// Layer-list rows shown above the organ rows. Purely visibility toggles for the
// procedural body/skeleton shell -- never deleted, never affects patient data.
export const pseudoLayers=[
 {id:'body',ko:'신체',en:'Body'},
 {id:'skeleton',ko:'골격',en:'Skeleton'},
 {id:'vascularFull',ko:'전신 혈관',en:'Vascular (full)'}
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
// Picks the single most relevant target to headline on the 3D marker/layer row -- backend's
// fixed rule-engine title/reason (e.g. "출혈 위험 상승 — 항응고 효과 중첩"), never a guessed or
// AI-inferred symptom. Highest severity first, then most recently generated.
const SEVERITY_ORDER={danger:0,caution:1,info:2};
export function primaryTargetFor(targets){
 if(!targets?.length)return null;
 return [...targets].sort((a,b)=>(SEVERITY_ORDER[a.severity]??3)-(SEVERITY_ORDER[b.severity]??3))[0];
}
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

// Real full-body skeleton/vascular tree merged from BodyParts3D (extras.glb, see
// AnatomyExtrasAssets.jsx). It is an additional optional layer on top of the 10 organs above --
// it never repositions or replaces spine/vascular or any other organ mesh/logic. BodyParts3D
// ships in millimetres with a Z-up axis convention; this transform converts the merged mesh into
// this app's Y-up model-unit space (1 unit = 1/scale mm). The 10 real organs' p/s above are
// derived from this exact same rotation+scale, so both stay in one consistent, real-world-scaled
// coordinate system. See frontend/public/models/anatomy/README.md.
export const extrasTransform={scale:.00522,position:[0,-4.49,-.53],rotation:[-Math.PI/2,0,0]};

// BodyParts3D ships one reference adult specimen -- there is no separate real female scan to
// switch to. Rather than silently showing the same body for every patient, this applies a uniform
// anthropometric size scale (average adult height ratio) to the *same* real scan when the real
// data path is active, pivoted from the feet so the figure still stands on the ground. It is
// explicitly NOT a female-specific segmentation -- never present it as one. The procedural
// fallback (no real GLB) keeps its own, separate male/female BODY_PROFILES shape difference below
// and is unaffected by this constant.
export const SEX_BODY_SCALE={male:1,female:.93,unspecified:.965};

// Required attribution for BodyParts3D-derived meshes (organs + extras). Must stay visible on
// screen whenever a GLB asset is loaded -- do not remove.
export const ANATOMY_ATTRIBUTION='BodyParts3D, © Database Center for Life Science, CC BY-SA 2.1 Japan';

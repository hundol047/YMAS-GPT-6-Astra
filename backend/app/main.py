import json,os,logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from .schemas import RiskFeatures, PatientRequest, SimulationRequest, ReviewRequest, Medication, Patient
from .services.risk_inference import RiskEngine
from .services.rule_engine import CATALOG, DRUGS
from .services.emr_adapter import DemoAdapter
from .services.clinical_agent import ClinicalAgent
from .services.audit import AuditStore

log=logging.getLogger('synexagent')
@asynccontextmanager
async def lifespan(app):
    app.state.engine=RiskEngine()
    app.state.agent=ClinicalAgent(app.state.engine)
    app.state.adapter=DemoAdapter()
    app.state.audit=AuditStore()
    yield

app=FastAPI(title='SynexAgent Demo API',version='1.0.0',lifespan=lifespan)
origins=os.getenv('SYNEX_CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(',')
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET','POST'],allow_headers=['Content-Type'])

def patient(pid):
    p=app.state.adapter.get(pid)
    if p is None:raise HTTPException(404,'Patient not found')
    return p

def save_analysis(result,event='analysis_completed'):
    audit=app.state.audit
    audit.save_analysis(result)
    for a in result['alerts']:
        audit.record(result['patient_id'],'alert_detected',{'analysis_id':result['analysis_id'],'alert_id':a['id'],'title':a['title'],'severity':a['severity']})
    audit.record(result['patient_id'],event,{'analysis_id':result['analysis_id'],'risk_probability':result['risk']['risk_probability'],'model_sha256':result['risk']['model_sha256'],'rules_sha256':result['rules_sha256']})

@app.get('/health')
def health():return {'status':'ok','demo':True,**app.state.engine.health()}

@app.get('/catalog')
def catalog():return CATALOG

@app.get('/patients')
def patients():
    out=[]
    for p in app.state.adapter.list():
        a=app.state.agent.run(p)
        out.append({'id':p.id,'name':p.name,'age':p.age,'sex':p.sex,'diagnosis':p.diagnosis,'scenario':p.scenario,
                    'risk':a['risk'],'alerts':len(a['alerts']),'danger':sum(x['severity']=='danger' for x in a['alerts'])})
    return out

@app.get('/patients/{pid}')
def get_patient(pid:str):
    p=patient(pid);app.state.audit.record(pid,'patient_selected',{'name':p.name});return p

@app.get('/patients/{pid}/anatomy')
def anatomy(pid:str):
    return app.state.agent.run(patient(pid))['anatomy']

@app.get('/patients/{pid}/fhir')
def fhir(pid:str):patient(pid);return app.state.adapter.bundle(pid)

@app.post('/predict')
def predict(features:RiskFeatures):return app.state.engine.predict(features)

@app.post('/medication-check')
def check(p:Patient):return app.state.agent.run(p)

@app.post('/agent/analyze')
def analyze(req:PatientRequest):
    p=patient(req.patient_id)
    app.state.audit.record(p.id,'analysis_started',{})
    result=app.state.agent.run(p);save_analysis(result);return result

@app.get('/agent/stream/{pid}')
def stream(pid:str):
    p=patient(pid)
    def events():
        try:
            app.state.audit.record(pid,'analysis_started',{})
            # Progress is a replay of measured completed stages, never fabricated checks.
            result=app.state.agent.run(p)
            save_analysis(result)
            for step in result['steps']:
                yield 'event: step\ndata: '+json.dumps(step,ensure_ascii=False)+'\n\n'
            yield 'event: result\ndata: '+json.dumps(result,ensure_ascii=False)+'\n\n'
        except Exception:
            log.exception('Analysis failed')
            yield 'event: failure\ndata: {"message":"분석 실패: 다시 시도하십시오."}\n\n'
    return StreamingResponse(events(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

@app.post('/prescription/simulate')
def simulate(req:SimulationRequest):
    p=patient(req.patient_id)
    if req.drug_id not in DRUGS:raise HTTPException(422,'Unknown drug: select a catalog entry')
    if any(m.status=='active' and m.drug_id==req.drug_id for m in p.medications):raise HTTPException(409,'이미 복용 중인 약물입니다.')
    before=app.state.agent.run(p)
    proposal=p.model_copy(deep=True)
    proposal.medications.append(Medication(drug_id=req.drug_id,dispenses=req.dispenses,note='Simulation only'))
    after=app.state.agent.run(proposal)
    save_analysis(before,'simulation_baseline');save_analysis(after,'simulation_proposal')
    old={a['id'] for a in before['alerts']}
    added=[a for a in after['alerts'] if a['id'] not in old]
    delta=(after['risk']['risk_probability']-before['risk']['risk_probability'])*100
    result={'patient_id':p.id,'drug':DRUGS[req.drug_id],'before':before,'after':after,'delta_percentage_points':delta,
            'new_alerts':added,'original_unchanged':True,'prescription_committed':False}
    app.state.audit.record(p.id,'prescription_simulated',{'drug_id':req.drug_id,'delta_percentage_points':delta,'analysis_id':after['analysis_id']})
    return result

@app.post('/reviews')
def review(req:ReviewRequest):
    a=app.state.audit.get_analysis(req.analysis_id)
    if a is None:raise HTTPException(404,'Analysis not found')
    if not any(x['id']==req.alert_id for x in a['alerts']):raise HTTPException(404,'Alert not in this analysis')
    app.state.audit.record(a['patient_id'],'alert_'+req.action,req.model_dump())
    return {'saved':True,'action':req.action,'prescription_committed':False}

@app.get('/audit/{pid}')
def audit(pid:str):patient(pid);return app.state.audit.list(pid)

DIST=Path(__file__).resolve().parents[2]/'frontend'/'dist'
if DIST.exists():
    if (DIST/'models').exists():
        app.mount('/models',StaticFiles(directory=DIST/'models'),name='models')
    app.mount('/assets',StaticFiles(directory=DIST/'assets'),name='assets')
    @app.get('/',include_in_schema=False)
    def index():return FileResponse(DIST/'index.html')
    @app.get('/favicon.svg',include_in_schema=False)
    def favicon():return FileResponse(DIST/'favicon.svg')

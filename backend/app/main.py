import json,os,logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from .schemas import RiskFeatures, PatientRequest, SimulationRequest, ReviewRequest, FeedbackRequest, Medication, Patient
from .services.risk_inference import RiskEngine
from .services.rule_engine import CATALOG, DRUGS
from .services.emr_adapter import DemoAdapter, FHIRAdapter, SmartOAuthClient
from .services.clinical_agent import ClinicalAgent
from .services.audit import AuditStore
from .services.terminology_mapper import patient_terminology
from .services.data_quality import assess as assess_data_quality
from .services.cds_hooks import SERVICES_DOC, build_cards
from .services.smart_launch import build_authorize_redirect, exchange_code
from .services.auth import get_current_user, require, User
from .services.validation import alert_type_breakdown, alert_fatigue_metrics
from .services.imaging_pipeline import health as imaging_health
from .services.rule_engine import RULE_METADATA
from fastapi import Depends
from fastapi.responses import RedirectResponse

log=logging.getLogger('synexagent')

def build_adapter():
    """EMR_MODE=demo (default) or EMR_MODE=fhir. FHIR mode requires FHIR_BASE_URL; client
    credentials (FHIR_CLIENT_ID/FHIR_CLIENT_SECRET/FHIR_SCOPE) are optional -- omit them to call
    an already-authenticated/network-restricted FHIR endpoint with no bearer token."""
    mode=os.getenv('EMR_MODE','demo').lower()
    if mode=='fhir':
        client_id=os.getenv('FHIR_CLIENT_ID')
        oauth=SmartOAuthClient(os.environ['FHIR_BASE_URL'], client_id, os.getenv('FHIR_CLIENT_SECRET',''),
                                os.getenv('FHIR_SCOPE','system/*.read')) if client_id else None
        return FHIRAdapter(oauth=oauth)
    return DemoAdapter()

@asynccontextmanager
async def lifespan(app):
    app.state.engine=RiskEngine()
    app.state.agent=ClinicalAgent(app.state.engine)
    app.state.adapter=build_adapter()
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

@app.get('/health/subsystems')
def health_subsystems():
    """Per-subsystem status for observability. Degraded-mode by design: a subsystem being
    not_configured/degraded never crashes this endpoint or the app -- see each try/except below.
    No patient data is included in this response."""
    emr_mode=os.getenv('EMR_MODE','demo').lower()
    try:
        model=app.state.engine.health()
        model_status='ok' if model['model_loaded'] else 'degraded'
    except Exception as e:
        model={'error':str(e)};model_status='down'
    return {
        'emr':{'status':'ok','mode':emr_mode,'adapter':type(app.state.adapter).__name__},
        'terminology':{'status':'ok','note':'fixed reference tables; see services/terminology_mapper.py'},
        'rule_engine':{'status':'ok','rules_version':RULE_METADATA['rules_version'],'evidence_level':RULE_METADATA['evidence_level']},
        'ai_model':{'status':model_status,**model},
        'auth':{'status':'ok','mode':os.getenv('AUTH_MODE','demo').lower()},
        'imaging':imaging_health(),
    }

@app.get('/catalog')
def catalog():return CATALOG

@app.get('/patients')
def patients():
    out=[]
    try:
        roster=app.state.adapter.list()
    except NotImplementedError as e:
        raise HTTPException(501,str(e))
    for p in roster:
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

@app.get('/patients/{pid}/terminology')
def terminology(pid:str):return patient_terminology(patient(pid),DRUGS)

@app.get('/patients/{pid}/data-quality')
def data_quality(pid:str):return assess_data_quality(patient(pid))

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
def review(req:ReviewRequest,user:User=Depends(require('alert:review'))):
    a=app.state.audit.get_analysis(req.analysis_id)
    if a is None:raise HTTPException(404,'Analysis not found')
    if not any(x['id']==req.alert_id for x in a['alerts']):raise HTTPException(404,'Alert not in this analysis')
    app.state.audit.record(a['patient_id'],'alert_'+req.action,req.model_dump(),user_id=user.id,role=user.role)
    return {'saved':True,'action':req.action,'prescription_committed':False}

@app.post('/feedback')
def feedback(req:FeedbackRequest,user:User=Depends(require('feedback:submit'))):
    """Clinician feedback on an alert (Useful/Not useful/Incorrect/Already known/Needs more info).
    Stored as research/improvement data only -- never fed back into model training or rule
    generation automatically."""
    a=app.state.audit.get_analysis(req.analysis_id)
    if a is None:raise HTTPException(404,'Analysis not found')
    if not any(x['id']==req.alert_id for x in a['alerts']):raise HTTPException(404,'Alert not in this analysis')
    app.state.audit.record(a['patient_id'],'alert_feedback',req.model_dump(),user_id=user.id,role=user.role)
    return {'saved':True,'used_for_training':False}

@app.get('/whoami')
def whoami(user:User=Depends(get_current_user)):return {'user_id':user.id,'role':user.role}

@app.get('/validation/alert-breakdown')
def validation_alert_breakdown():
    try:cohort=app.state.adapter.list()
    except NotImplementedError as e:raise HTTPException(501,str(e))
    return alert_type_breakdown(app.state.agent,cohort)

@app.get('/validation/alert-fatigue')
def validation_alert_fatigue():
    try:cohort=[p.id for p in app.state.adapter.list()]
    except NotImplementedError as e:raise HTTPException(501,str(e))
    return alert_fatigue_metrics(app.state.audit,cohort)

@app.get('/audit/{pid}')
def audit(pid:str):patient(pid);return app.state.audit.list(pid)

# --- CDS Hooks: https://cds-hooks.org/ -------------------------------------------------------
@app.get('/cds-services')
def cds_services():return SERVICES_DOC

@app.post('/cds-services/synex-medication-safety')
def cds_medication_safety(req:dict):
    pid=(req.get('context') or {}).get('patientId')
    if not pid:raise HTTPException(400,'context.patientId is required')
    p=app.state.adapter.get(pid)
    if p is None:raise HTTPException(404,'Patient not found')
    result=app.state.agent.run(p)
    app.state.audit.record(pid,'cds_hook_fired',{'hook':req.get('hook'),'analysis_id':result['analysis_id']})
    base=os.getenv('SYNEX_PUBLIC_BASE_URL','')
    return build_cards(pid,result,base)

# --- SMART App Launch --------------------------------------------------------------------------
# Unverified against a real EMR/authorization server -- see services/smart_launch.py docstring.
@app.get('/smart/launch',include_in_schema=False)
def smart_launch(iss:str,launch:str):
    client_id=os.getenv('FHIR_CLIENT_ID')
    redirect_uri=os.getenv('FHIR_REDIRECT_URI','')
    scope=os.getenv('FHIR_SCOPE','launch openid fhirUser patient/*.read')
    if not client_id or not redirect_uri:
        raise HTTPException(500,'FHIR_CLIENT_ID and FHIR_REDIRECT_URI must be configured for SMART launch')
    url=build_authorize_redirect(iss,launch,client_id,redirect_uri,scope)
    return RedirectResponse(url,status_code=307)

@app.get('/smart/callback',include_in_schema=False)
def smart_callback(code:str,state:str):
    client_id=os.getenv('FHIR_CLIENT_ID')
    try:
        token=exchange_code(state,code,client_id)
    except KeyError:
        raise HTTPException(400,'Unknown or expired launch state')
    # A real deployment would store token['patient'] (the SMART launch context patient id) in a
    # session and redirect into the app for that patient; this demo returns the raw token
    # response so the exchange itself can be inspected/verified.
    return token

DIST=Path(__file__).resolve().parents[2]/'frontend'/'dist'
if DIST.exists():
    if (DIST/'models').exists():
        app.mount('/models',StaticFiles(directory=DIST/'models'),name='models')
    app.mount('/assets',StaticFiles(directory=DIST/'assets'),name='assets')
    @app.get('/',include_in_schema=False)
    def index():return FileResponse(DIST/'index.html')
    @app.get('/favicon.svg',include_in_schema=False)
    def favicon():return FileResponse(DIST/'favicon.svg')

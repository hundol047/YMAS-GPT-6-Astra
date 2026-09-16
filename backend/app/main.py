import json,os,logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from .schemas import (RiskFeatures, PatientRequest, SimulationRequest, ReviewRequest, FeedbackRequest, Medication, Patient,
                       EncounterCreateRequest, EncounterUpdateRequest, VitalsCreateRequest, NoteCreateRequest,
                       NoteUpdateRequest, NoteAmendRequest, DiagnosisCreateRequest, MedicationOrderCreateRequest,
                       LabOrderCreateRequest, LabResultCreateRequest)
from .services.risk_inference import RiskEngine
from .services.rule_engine import CATALOG, DRUGS
from .services.emr_adapter import DemoAdapter, FHIRAdapter, SmartOAuthClient, SmartSessionTokenProvider
from .services.clinical_agent import ClinicalAgent
from .services.audit import AuditStore
from .services.terminology_mapper import patient_terminology
from .services.data_quality import assess as assess_data_quality
from .services.cds_hooks import SERVICES_DOC, build_cards
from .services.smart_launch import (build_authorize_redirect, exchange_code, create_session, SESSIONS,
                                     SESSION_TTL_SECONDS, CURRENT_SESSION_ID)
from .services.auth import get_current_user, require, require_all, User
from .services.validation import alert_type_breakdown, alert_fatigue_metrics
from .services.imaging_pipeline import health as imaging_health
from .services.rule_engine import RULE_METADATA
from .services.repositories import (EncounterRepository, ClinicalNoteRepository, DiagnosisRepository,
                                     MedicationOrderRepository, LabOrderRepository, NotFound as RepoNotFound)
from .services.timeline import build_timeline, with_ai_warnings
from .services.clinical_summary import build_summary
from .services.results import unified_results
from .services.vitals import assess as assess_vitals
from .services.demo_seed import seed_demo_clinical_data
from fastapi import Depends, Cookie
from fastapi.responses import RedirectResponse

log=logging.getLogger('synexagent')

def build_adapter():
    """EMR_MODE=demo (default) or EMR_MODE=fhir. FHIR mode requires FHIR_BASE_URL.

    Within EMR_MODE=fhir, FHIR_AUTH_MODE picks how FHIRAdapter authenticates each request --
    the two modes are mutually exclusive, never blended:
      - FHIR_AUTH_MODE=client_credentials (default, unchanged from before this round): one shared
        app-level token from FHIR_CLIENT_ID/FHIR_CLIENT_SECRET/FHIR_SCOPE. Optional -- omit
        FHIR_CLIENT_ID to call an already-authenticated/network-restricted FHIR endpoint with no
        bearer token at all.
      - FHIR_AUTH_MODE=smart: each request instead uses the per-clinician access token SMART App
        Launch stored in the browser's session (see smart_session_context middleware below and
        emr_adapter.SmartSessionTokenProvider) -- the real SMART Launch -> session -> FHIR request
        chain, not the shared client_credentials token.
    """
    mode=os.getenv('EMR_MODE','demo').lower()
    if mode=='fhir':
        if os.getenv('FHIR_AUTH_MODE','client_credentials').lower()=='smart':
            return FHIRAdapter(token_provider=SmartSessionTokenProvider())
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
    # Clinical Workspace repositories -- see services/repositories.py. All wrap app.state.adapter,
    # so EMR_MODE=fhir naturally gets NotImplementedError from adapter.mutate() on any write (no
    # local write-back to a real hospital system), translated to 501 by call() below.
    app.state.encounter_repo=EncounterRepository(app.state.adapter)
    app.state.note_repo=ClinicalNoteRepository(app.state.adapter)
    app.state.diagnosis_repo=DiagnosisRepository(app.state.adapter)
    app.state.medication_order_repo=MedicationOrderRepository(app.state.adapter)
    app.state.lab_order_repo=LabOrderRepository(app.state.adapter)
    if isinstance(app.state.adapter,DemoAdapter):
        # Seed each bundled demo patient with one past Encounter+Vitals+Diagnosis+signed Note --
        # see services/demo_seed.py. Runs through the same repository methods a real API call
        # uses, not hand-crafted JSON. Skipped for EMR_MODE=fhir: FHIRAdapter.mutate() doesn't
        # support local write-back by design (see emr_adapter.py).
        seed_demo_clinical_data(app.state.adapter,app.state.encounter_repo,app.state.diagnosis_repo,app.state.note_repo)
    yield

def call(fn,*args,**kwargs):
    """Run a repository call, translating its exceptions into the right HTTP status: 501 if the
    active EMR adapter doesn't support local write-back (BaseEMRAdapter.mutate), 404 if the
    referenced resource doesn't exist, 409 if the requested state transition isn't allowed (e.g.
    editing a signed note directly), 422 if the resource itself fails validation."""
    try:
        return fn(*args,**kwargs)
    except NotImplementedError as e:
        raise HTTPException(501,str(e))
    except RepoNotFound as e:
        raise HTTPException(404,f'Not found: {e}')
    except PermissionError as e:
        raise HTTPException(409,str(e))
    except ValueError as e:
        raise HTTPException(422,str(e))

def resolve_cors_config(cors_origins_env=None, allow_credentials_env=None):
    """Parses SYNEX_CORS_ORIGINS/SYNEX_CORS_ALLOW_CREDENTIALS and enforces the one CORS rule that
    must never be violated: allow_credentials=True (needed for the synex_session HttpOnly cookie --
    SMART on FHIR launch context, SSE auth below -- to be sent on cross-origin dev requests) can
    never be combined with a wildcard origin. That combination would accept a credentialed request
    from ANY origin, which is exactly the CSRF-shaped hole CORS exists to prevent. Pulled out as a
    standalone function (rather than inline at import time) so it's independently testable without
    constructing a whole FastAPI app."""
    origins=[o.strip() for o in (cors_origins_env if cors_origins_env is not None else
             os.getenv('SYNEX_CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173')).split(',') if o.strip()]
    allow_credentials=(allow_credentials_env if allow_credentials_env is not None else
                        os.getenv('SYNEX_CORS_ALLOW_CREDENTIALS','true')).lower()!='false'
    if '*' in origins and allow_credentials:
        raise RuntimeError('SYNEX_CORS_ORIGINS must not be "*" while credentialed CORS is enabled '
                            '(cookies/Authorization) -- set explicit origins, or SYNEX_CORS_ALLOW_CREDENTIALS=false.')
    return origins, allow_credentials

app=FastAPI(title='SynexAgent Demo API',version='1.0.0',lifespan=lifespan)
_cors_origins,_cors_allow_credentials=resolve_cors_config()
app.add_middleware(CORSMiddleware,allow_origins=_cors_origins,allow_credentials=_cors_allow_credentials,
                    allow_methods=['GET','POST','PATCH','DELETE','OPTIONS'],allow_headers=['Content-Type','Authorization'])

@app.middleware('http')
async def smart_session_context_middleware(request,call_next):
    """Makes 'which SMART session is this request' available to emr_adapter.SmartSessionTokenProvider
    (FHIR_AUTH_MODE=smart) without threading a session_id through every adapter.get(pid) call site --
    see smart_launch.CURRENT_SESSION_ID's docstring. Reads only the opaque session_id cookie, never
    a token; reset in `finally` so it never leaks into the next request handled by this worker."""
    reset_token=CURRENT_SESSION_ID.set(request.cookies.get('synex_session'))
    try:
        return await call_next(request)
    finally:
        CURRENT_SESSION_ID.reset(reset_token)

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
def patients(user:User=Depends(require('patient:read'))):
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
def get_patient(pid:str,user:User=Depends(require('patient:read'))):
    p=patient(pid);app.state.audit.record(pid,'patient_selected',{'name':p.name},user_id=user.id,role=user.role);return p

@app.get('/patients/{pid}/anatomy')
def anatomy(pid:str,user:User=Depends(require('patient:read'))):
    return app.state.agent.run(patient(pid))['anatomy']

@app.get('/patients/{pid}/fhir')
def fhir(pid:str,user:User=Depends(require('patient:read'))):patient(pid);return app.state.adapter.bundle(pid)

@app.get('/patients/{pid}/terminology')
def terminology(pid:str,user:User=Depends(require('patient:read'))):return patient_terminology(patient(pid),DRUGS)

@app.get('/patients/{pid}/data-quality')
def data_quality(pid:str,user:User=Depends(require('patient:read'))):return assess_data_quality(patient(pid))

@app.post('/predict')
def predict(features:RiskFeatures):return app.state.engine.predict(features)

@app.post('/medication-check')
def check(p:Patient,user:User=Depends(require('analysis:read'))):return app.state.agent.run(p)

@app.post('/agent/analyze')
def analyze(req:PatientRequest,user:User=Depends(require('analysis:read'))):
    p=patient(req.patient_id)
    app.state.audit.record(p.id,'analysis_started',{})
    result=app.state.agent.run(p);save_analysis(result);return result

@app.get('/agent/stream/{pid}')
def stream(pid:str,user:User=Depends(require('analysis:read'))):
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
def simulate(req:SimulationRequest,user:User=Depends(require_all('patient:read','order:write'))):
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
def audit(pid:str,user:User=Depends(require('audit:read'))):patient(pid);return app.state.audit.list(pid)

# --- Clinical Workspace: Encounters/Notes/Vitals/Diagnoses/Orders/Timeline ----------------------
# All writes go through backend/app/services/repositories.py, which (a) dual-writes into the
# existing flat Patient.medications/conditions/labs so the unchanged rule engine/risk model/3D
# anatomy keep working, and (b) is idempotent against retries (see repositories.py's module
# docstring). EMR_MODE=fhir gets a clean 501 from every write below (via call()'s
# NotImplementedError handling) -- writing a new order back into a real hospital system is out of
# scope; this app is not that system's EHR.

@app.get('/patients/{pid}/encounters')
def list_encounters(pid:str,user:User=Depends(require('patient:read'))):
    patient(pid);return app.state.encounter_repo.list(pid)

@app.post('/patients/{pid}/encounters')
def create_encounter(pid:str,req:EncounterCreateRequest,user:User=Depends(require('patient:write'))):
    patient(pid)
    enc=call(app.state.encounter_repo.create,pid,encounter_type=req.encounter_type,department=req.department,
              attending_physician=req.attending_physician,chief_complaint=req.chief_complaint)
    app.state.audit.record(pid,'encounter_created',{'encounter_id':enc.id,'encounter_type':enc.encounter_type},user_id=user.id,role=user.role)
    return enc

@app.get('/encounters/{eid}')
def get_encounter(eid:str,user:User=Depends(require('patient:read'))):
    _,enc=call(app.state.encounter_repo.get_by_id,eid);return enc

@app.patch('/encounters/{eid}')
def update_encounter(eid:str,req:EncounterUpdateRequest,user:User=Depends(require('patient:write'))):
    pid,_=call(app.state.encounter_repo.get_by_id,eid)
    patch={k:v for k,v in req.model_dump().items() if v is not None}
    enc=call(app.state.encounter_repo.update,pid,eid,**patch)
    app.state.audit.record(pid,'encounter_updated',{'encounter_id':eid,'fields_changed':list(patch)},user_id=user.id,role=user.role)
    return enc

@app.get('/patients/{pid}/vitals')
def list_vitals(pid:str,user:User=Depends(require('patient:read'))):
    patient(pid);return app.state.encounter_repo.list_vitals(pid)

@app.post('/encounters/{eid}/vitals')
def add_vitals(eid:str,req:VitalsCreateRequest,user:User=Depends(require('patient:write'))):
    pid,_=call(app.state.encounter_repo.get_by_id,eid)
    v=call(app.state.encounter_repo.add_vitals,pid,eid,**req.model_dump())
    app.state.audit.record(pid,'vitals_recorded',{'encounter_id':eid,'vital_id':v.id},user_id=user.id,role=user.role)
    return {**v.model_dump(),'assessment':assess_vitals(v)}

@app.get('/patients/{pid}/problem-list')
def problem_list(pid:str,user:User=Depends(require('patient:read'))):return patient(pid).problem_list

@app.post('/encounters/{eid}/diagnoses')
def create_diagnosis(eid:str,req:DiagnosisCreateRequest,user:User=Depends(require('patient:write'))):
    pid,_=call(app.state.encounter_repo.get_by_id,eid)
    dx=call(app.state.diagnosis_repo.create,pid,eid,display_name=req.display_name,diagnosis_type=req.diagnosis_type,
             code=req.code,code_system=req.code_system,clinician=req.clinician)
    app.state.audit.record(pid,'diagnosis_added',{'encounter_id':eid,'diagnosis_id':dx.id,'display_name':dx.display_name},user_id=user.id,role=user.role)
    return dx

@app.get('/encounters/{eid}/notes')
def list_notes(eid:str,user:User=Depends(require('note:read'))):
    pid,_=call(app.state.encounter_repo.get_by_id,eid)
    return app.state.note_repo.list_for_encounter(pid,eid)

@app.post('/encounters/{eid}/notes')
def create_note(eid:str,req:NoteCreateRequest,user:User=Depends(require('note:write'))):
    pid,_=call(app.state.encounter_repo.get_by_id,eid)
    note=call(app.state.note_repo.create,pid,eid,author=req.author,subjective=req.subjective,objective=req.objective,
               assessment=req.assessment,plan=req.plan)
    app.state.audit.record(pid,'note_created',{'encounter_id':eid,'note_id':note.id,'author':note.author},user_id=user.id,role=user.role)
    return note

@app.patch('/notes/{note_id}')
def update_note(note_id:str,req:NoteUpdateRequest,user:User=Depends(require('note:write'))):
    # Rejects (409, via call()'s PermissionError handling) instead of amending if the note is
    # already signed -- see ClinicalNoteRepository.update()'s docstring. No auto-amendment here.
    patch={k:v for k,v in req.model_dump().items() if v is not None}
    updated=call(app.state.note_repo.update,note_id,**patch)
    app.state.audit.record(updated.patient_id,'note_modified',{'note_id':note_id,'fields_changed':list(patch)},user_id=user.id,role=user.role)
    return updated

@app.post('/notes/{note_id}/sign')
def sign_note(note_id:str,user:User=Depends(require('note:sign'))):
    note=call(app.state.note_repo.sign,note_id)
    app.state.audit.record(note.patient_id,'note_signed',{'note_id':note_id,'author':note.author},user_id=user.id,role=user.role)
    return note

@app.post('/notes/{note_id}/amendments')
def amend_note(note_id:str,req:NoteAmendRequest,user:User=Depends(require('note:sign'))):
    # Only path that can change a signed note -- author + reason are required by NoteAmendRequest
    # itself (min_length=1), and the original S/O/A/P text is never overwritten (see
    # ClinicalNoteRepository.amend()).
    note=call(app.state.note_repo.amend,note_id,author=req.author,reason=req.reason,subjective=req.subjective,
               objective=req.objective,assessment=req.assessment,plan=req.plan)
    app.state.audit.record(note.patient_id,'note_amended',{'note_id':note_id,'author':req.author,'reason':req.reason},user_id=user.id,role=user.role)
    return note

def _agent_diff(p,drug_id,dispenses=None):
    """Same before/after comparison /prescription/simulate already uses -- reused here for
    MedicationOrder's SynexAgent precheck instead of duplicating the risk-diff logic.

    dispenses is a risk-model feature meaning "how many times this medication has been
    dispensed/refilled" (see feature_engineering.py's therapy_duration_load) -- a completely
    different concept from MedicationOrder.quantity (how many units THIS order is for, e.g. "30
    tablets"). Callers below must never pass quantity here: a new order for 30 tablets is not 30
    past refill events, and doing so would make the risk model misread a brand-new prescription as
    a long-established one. There is no real dispense-count data for a not-yet-confirmed order, so
    this always stays at its default (None/unknown) -- the precheck evaluates the drug's presence
    and interactions, not a fabricated refill history."""
    before=app.state.agent.run(p)
    proposal=p.model_copy(deep=True)
    proposal.medications.append(Medication(drug_id=drug_id,dispenses=dispenses,status='active',note='Precheck only'))
    after=app.state.agent.run(proposal)
    old={a['id'] for a in before['alerts']}
    new_alerts=[a for a in after['alerts'] if a['id'] not in old]
    delta=(after['risk']['risk_probability']-before['risk']['risk_probability'])*100
    return before,after,new_alerts,delta

@app.post('/encounters/{eid}/medication-orders/precheck')
def medication_order_precheck(eid:str,req:MedicationOrderCreateRequest,user:User=Depends(require('order:read'))):
    pid,_=call(app.state.encounter_repo.get_by_id,eid)
    p=patient(pid)
    if req.medication_code not in DRUGS:raise HTTPException(422,'Unknown drug: select a catalog entry')
    before,after,new_alerts,delta=_agent_diff(p,req.medication_code)
    app.state.audit.record(pid,'ai_warning_viewed',{'encounter_id':eid,'medication_code':req.medication_code,'new_alert_count':len(new_alerts)},user_id=user.id,role=user.role)
    return {'patient_id':pid,'encounter_id':eid,'drug':DRUGS[req.medication_code],'before':before,'after':after,
            'delta_percentage_points':delta,'new_alerts':new_alerts,'requires_override':bool(new_alerts)}

@app.post('/encounters/{eid}/medication-orders')
def create_medication_order(eid:str,req:MedicationOrderCreateRequest,user:User=Depends(require('order:write'))):
    # SynexAgent never blocks a prescription automatically: a warning-producing order still goes
    # through as long as the clinician supplies a non-blank override_reason, which is recorded to
    # audit as 'warning_overridden'. The precheck is re-run here server-side (not trusted from the
    # client) so a client that skips /precheck can't bypass the override requirement.
    pid,_=call(app.state.encounter_repo.get_by_id,eid)
    p=patient(pid)
    if req.medication_code not in DRUGS:raise HTTPException(422,'Unknown drug: select a catalog entry')
    _,_,new_alerts,_=_agent_diff(p,req.medication_code)
    if new_alerts and not (req.override_reason and req.override_reason.strip()):
        raise HTTPException(409,f'SynexAgent detected {len(new_alerts)} new signal(s); an override_reason is required to confirm this order.')
    order=call(app.state.medication_order_repo.create,pid,eid,medication_code=req.medication_code,medication_name=req.medication_name,
               dose=req.dose,dose_unit=req.dose_unit,route=req.route,frequency=req.frequency,duration=req.duration,
               quantity=req.quantity,prn=req.prn,indication=req.indication,start_date=req.start_date,end_date=req.end_date,
               prescriber=req.prescriber)
    order=call(app.state.medication_order_repo.confirm,order.id,override_reason=req.override_reason if new_alerts else None)
    app.state.audit.record(pid,'medication_ordered',{'encounter_id':eid,'order_id':order.id,'medication_code':order.medication_code,
        'dose':order.dose,'dose_unit':order.dose_unit,'route':order.route,'overridden':bool(new_alerts)},user_id=user.id,role=user.role)
    if new_alerts:
        app.state.audit.record(pid,'warning_overridden',{'encounter_id':eid,'order_id':order.id,'override_reason':order.override_reason,
            'alert_ids':[a['id'] for a in new_alerts]},user_id=user.id,role=user.role)
    return order

@app.get('/patients/{pid}/medication-orders')
def list_medication_orders(pid:str,user:User=Depends(require('order:read'))):
    patient(pid);return app.state.medication_order_repo.list_for_patient(pid)

@app.post('/medication-orders/{order_id}/cancel')
def cancel_medication_order(order_id:str,user:User=Depends(require('order:write'))):
    order=call(app.state.medication_order_repo.cancel,order_id)
    app.state.audit.record(order.patient_id,'medication_cancelled',{'order_id':order.id},user_id=user.id,role=user.role)
    return order

@app.post('/encounters/{eid}/lab-orders')
def create_lab_order(eid:str,req:LabOrderCreateRequest,user:User=Depends(require('order:write'))):
    pid,_=call(app.state.encounter_repo.get_by_id,eid)
    order=call(app.state.lab_order_repo.create,pid,eid,test_code=req.test_code,test_name=req.test_name,panel=req.panel,
               priority=req.priority,indication=req.indication,ordering_physician=req.ordering_physician)
    app.state.audit.record(pid,'lab_ordered',{'encounter_id':eid,'order_id':order.id,'test_name':order.test_name,'priority':order.priority},user_id=user.id,role=user.role)
    return order

@app.get('/patients/{pid}/lab-orders')
def list_lab_orders(pid:str,user:User=Depends(require('order:read'))):
    patient(pid);return app.state.lab_order_repo.list_for_patient(pid)

@app.post('/lab-orders/{order_id}/cancel')
def cancel_lab_order(order_id:str,user:User=Depends(require('order:write'))):
    order=call(app.state.lab_order_repo.cancel,order_id)
    app.state.audit.record(order.patient_id,'lab_order_cancelled',{'order_id':order.id},user_id=user.id,role=user.role)
    return order

@app.post('/lab-orders/{order_id}/result')
def submit_lab_result(order_id:str,req:LabResultCreateRequest,user:User=Depends(require('order:write'))):
    # Demo scope: no real lab instrument feed exists, so a result is direct clinician data entry
    # (like a real order-entry system's demo/manual mode) -- never fabricated by the agent.
    result=call(app.state.lab_order_repo.submit_result,order_id,value=req.value,unit=req.unit,
                reference_low=req.reference_low,reference_high=req.reference_high)
    app.state.audit.record(result.patient_id,'lab_result_recorded',{'order_id':order_id,'result_id':result.id,
        'test_name':result.test_name,'abnormal_flag':result.abnormal_flag},user_id=user.id,role=user.role)
    return result

@app.get('/patients/{pid}/lab-results')
def list_lab_results(pid:str,user:User=Depends(require('order:read'))):
    patient(pid)
    orders=app.state.lab_order_repo.list_for_patient(pid)
    return [r for o in orders for r in [app.state.lab_order_repo.result_for(o.id)] if r]

@app.get('/patients/{pid}/results')
def results(pid:str,user:User=Depends(require('order:read'))):
    # Unified Results: legacy/demo Patient.labs + FHIR Observations (already normalized into the
    # same Patient.labs list at fetch time by FHIRAdapter -- see emr_adapter.py) + LabOrder/
    # LabResult, merged chronologically. Does not replace /patients/{pid}/lab-orders or
    # /patients/{pid}/lab-results, which still return their own narrower views.
    p=patient(pid)
    legacy_source='legacy' if isinstance(app.state.adapter,DemoAdapter) else 'fhir'
    return {'patient_id':pid,'items':unified_results(p,lab_order_repo=app.state.lab_order_repo,legacy_source=legacy_source)}

@app.get('/patients/{pid}/timeline')
def timeline(pid:str,user:User=Depends(require('patient:read'))):
    p=patient(pid)
    events=build_timeline(p,note_repo=app.state.note_repo,medication_order_repo=app.state.medication_order_repo,
                            lab_order_repo=app.state.lab_order_repo)
    events=with_ai_warnings(events,app.state.audit.list(pid))
    return {'patient_id':pid,'events':events}

@app.get('/patients/{pid}/clinical-summary')
def clinical_summary(pid:str,user:User=Depends(require('patient:read'))):
    p=patient(pid)
    events=build_timeline(p,note_repo=app.state.note_repo,medication_order_repo=app.state.medication_order_repo,
                            lab_order_repo=app.state.lab_order_repo)
    events=with_ai_warnings(events,app.state.audit.list(pid))
    return build_summary(p,lab_order_repo=app.state.lab_order_repo,ai_warning_events=events)

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
    # The access token is NEVER returned to the browser, logged, or put in an audit detail dict --
    # see smart_launch.py's _SessionStore docstring for that boundary. Only an opaque session_id
    # (an HttpOnly cookie) reaches the browser; the SPA learns its SMART patient context by calling
    # GET /session/context, which reads the cookie server-side and returns only {patient_id}.
    client_id=os.getenv('FHIR_CLIENT_ID')
    try:
        token=exchange_code(state,code,client_id)
    except KeyError:
        raise HTTPException(400,'Unknown or expired launch state')
    patient_id=token.get('patient')
    if not patient_id:
        raise HTTPException(502,'Authorization server did not return a patient context (token.patient)')
    session_id=create_session(patient_id=patient_id,iss=token['iss'],access_token=token.get('access_token',''))
    secure=os.getenv('SYNEX_COOKIE_SECURE','true').lower()!='false'  # set false only for local HTTP dev
    redirect=RedirectResponse('/',status_code=307)
    redirect.set_cookie('synex_session',session_id,httponly=True,secure=secure,samesite='lax',max_age=SESSION_TTL_SECONDS)
    return redirect

@app.get('/session/context')
def session_context(synex_session:str|None=Cookie(default=None)):
    """What patient (if any) this browser's SMART launch session is scoped to -- deliberately the
    ONLY thing this endpoint exposes; see /smart/callback's comment on why the token itself never
    reaches here."""
    if not synex_session:return {'patient_id':None}
    ctx=SESSIONS.context(synex_session)
    return {'patient_id':ctx['patient_id'] if ctx else None}

DIST=Path(__file__).resolve().parents[2]/'frontend'/'dist'
# Served straight from frontend/public (not the dist copy Vite makes on build) so the real
# anatomy GLBs -- large, checked into git -- don't need duplicating inside dist/ too.
PUBLIC_MODELS=Path(__file__).resolve().parents[2]/'frontend'/'public'/'models'
if PUBLIC_MODELS.exists():
    app.mount('/models',StaticFiles(directory=PUBLIC_MODELS),name='models')
if DIST.exists():
    app.mount('/assets',StaticFiles(directory=DIST/'assets'),name='assets')
    @app.get('/',include_in_schema=False)
    def index():return FileResponse(DIST/'index.html')
    @app.get('/favicon.svg',include_in_schema=False)
    def favicon():return FileResponse(DIST/'favicon.svg')

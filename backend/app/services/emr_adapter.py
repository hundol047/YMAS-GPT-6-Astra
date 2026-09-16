"""EMR adapter boundary.

BaseEMRAdapter is the interface main.py talks to (list/get/bundle) so the running EMR_MODE
(demo|fhir) can be swapped without touching any API response schema.

DemoAdapter is unchanged: it reads backend/data/patients.json.

FHIRAdapter has NOT been exercised against a real hospital FHIR server from this environment --
none is reachable here. It is built against the FHIR R4 resource shapes (Patient, Condition,
MedicationRequest, MedicationStatement, AllergyIntolerance, Observation) and SMART on FHIR
client_credentials OAuth2, and is unit-tested with a fake HTTP transport
(backend/tests/test_fhir_adapter.py) rather than a live server. Treat it as
implemented-but-unverified-against-production until it is pointed at a real FHIR sandbox and that
run is captured somewhere. Encounter/DiagnosticReport/ImagingStudy are fetched via `_search` and
mapped into Patient.encounters/diagnostic_reports/imaging_studies (simple summaries, not full FHIR
resources -- only what those fields carry: id/date/type-or-name/status[/conclusion or modality]).
"""
import json, os, time
from abc import ABC, abstractmethod
from datetime import date as _date
from pathlib import Path
from typing import Optional
import httpx
from ..schemas import Patient, Medication, Allergy, Lab, Encounter, DiagnosticReport, ImagingStudy
from .rule_engine import DRUGS


class BaseEMRAdapter(ABC):
    @abstractmethod
    def list(self) -> list: ...
    @abstractmethod
    def get(self, pid: str): ...
    @abstractmethod
    def bundle(self, pid: str) -> Optional[dict]: ...


class DemoAdapter(BaseEMRAdapter):
    def __init__(self):
        path=Path(__file__).resolve().parents[2]/'data'/'patients.json'
        self.patients={p['id']:Patient.model_validate(p) for p in json.loads(path.read_text(encoding='utf-8'))}
    def list(self):return [p.model_copy(deep=True) for p in self.patients.values()]
    def get(self,pid):
        p=self.patients.get(pid)
        return p.model_copy(deep=True) if p else None
    def bundle(self,pid):
        p=self.get(pid)
        if p is None:return None
        subject={'reference':f'Patient/{p.id}'}
        resources=[{'resourceType':'Patient','id':p.id,'name':[{'text':p.name}], 'gender':p.sex,
                    'extension':[{'url':'https://synexagent.example/demo','valueBoolean':True}]}]
        for i,m in enumerate(p.medications):
            resources.append({'resourceType':'MedicationStatement','id':f'{p.id}-med-{i}','status':m.status,
                'subject':subject,'medicationCodeableConcept':{'coding':[{'system':'urn:synexagent:drug-catalog','code':m.drug_id,'display':DRUGS.get(m.drug_id,{}).get('name_ko',m.drug_id)}]}})
        for i,c in enumerate(p.conditions):
            resources.append({'resourceType':'Condition','id':f'{p.id}-condition-{i}','subject':subject,'code':{'text':c}})
        for i,a in enumerate(p.allergies):
            resources.append({'resourceType':'AllergyIntolerance','id':f'{p.id}-allergy-{i}','patient':subject,'code':{'text':a.substance},'category':[a.category] if a.category!='environment' else ['environment'], 'note':[{'text':f'{a.severity}: {a.reaction}'}]})
        for i,l in enumerate(p.labs):
            resources.append({'resourceType':'Observation','id':f'{p.id}-lab-{i}','status':'final','subject':subject,'code':{'text':l.name},'effectiveDateTime':str(l.date), 'valueQuantity':{'value':l.value,'unit':l.unit}})
        for e in p.encounters:
            resources.append({'resourceType':'Encounter','id':e.id,'status':e.status,'subject':subject,
                'type':[{'text':e.type}],'period':{'start':str(e.date)} if e.date else {}})
        for r in p.diagnostic_reports:
            resources.append({'resourceType':'DiagnosticReport','id':r.id,'status':r.status,'subject':subject,
                'code':{'text':r.name},'effectiveDateTime':str(r.date) if r.date else None,'conclusion':r.conclusion})
        for s in p.imaging_studies:
            resources.append({'resourceType':'ImagingStudy','id':s.id,'status':'available','subject':subject,
                'started':str(s.date) if s.date else None,'modality':[{'display':s.modality}] if s.modality else [],
                'description':s.description})
        return {'resourceType':'Bundle','type':'collection','entry':[{'resource':r} for r in resources]}


class SmartOAuthClient:
    """SMART on FHIR backend-service auth: client_credentials token acquisition + refresh, with
    .well-known/smart-configuration discovery. Reads client_id/secret ONLY from arguments the
    caller sourced from the environment -- nothing here reads or writes a secret to disk, an
    image layer, or git."""
    def __init__(self, base_url, client_id, client_secret, scope, transport=None):
        self.base_url=base_url.rstrip('/')
        self.client_id=client_id
        self.client_secret=client_secret
        self.scope=scope
        self._token=None
        self._expires_at=0.0
        self._client=httpx.Client(transport=transport, timeout=10)

    def discover_token_url(self):
        try:
            r=self._client.get(f'{self.base_url}/.well-known/smart-configuration')
            r.raise_for_status()
            return r.json()['token_endpoint']
        except Exception:
            return f'{self.base_url}/oauth2/token'  # conservative guess; real deployments should set FHIR_TOKEN_URL

    def token(self):
        if self._token and time.time() < self._expires_at-30:
            return self._token
        token_url=os.getenv('FHIR_TOKEN_URL') or self.discover_token_url()
        r=self._client.post(token_url, data={
            'grant_type':'client_credentials','client_id':self.client_id,
            'client_secret':self.client_secret,'scope':self.scope})
        r.raise_for_status()
        body=r.json()
        self._token=body['access_token']
        self._expires_at=time.time()+body.get('expires_in',300)
        return self._token


def _fhir_date(value):
    if not value:return None
    try:return _date.fromisoformat(str(value)[:10])
    except ValueError:return None

# Body height/weight Observation unit conversion. Real math (SI/imperial conversion), not a guess --
# an Observation reported in a unit outside this list is left unmapped (height_cm/weight_kg stay
# None and the gap is disclosed in `missing`) rather than assumed to be cm/kg.
def _height_cm(value_quantity):
    v=value_quantity.get('value');unit=(value_quantity.get('unit') or value_quantity.get('code') or '').strip().lower()
    if v is None:return None
    if unit in ('cm','centimeter','centimeters'):return float(v)
    if unit in ('in','in_i','inch','inches','[in_i]'):return float(v)*2.54
    return None

def _weight_kg(value_quantity):
    v=value_quantity.get('value');unit=(value_quantity.get('unit') or value_quantity.get('code') or '').strip().lower()
    if v is None:return None
    if unit in ('kg','kilogram','kilograms'):return float(v)
    if unit in ('lb','lb_av','lbs','pound','pounds','[lb_av]'):return float(v)*0.45359237
    return None


class FHIRAdapter(BaseEMRAdapter):
    def __init__(self, base_url=None, oauth: Optional[SmartOAuthClient]=None, transport=None):
        self.base_url=(base_url or os.environ['FHIR_BASE_URL']).rstrip('/')
        self.oauth=oauth
        self._client=httpx.Client(transport=transport, timeout=15)

    def _get(self, path, params=None):
        headers={'Accept':'application/fhir+json'}
        if self.oauth:headers['Authorization']=f'Bearer {self.oauth.token()}'
        r=self._client.get(f'{self.base_url}/{path}', params=params, headers=headers)
        r.raise_for_status()
        return r.json()

    def _search(self, resource_type, patient_id):
        bundle=self._get(resource_type, params={'patient':patient_id})
        return [e['resource'] for e in bundle.get('entry',[])]

    def list(self):
        # Whole-roster browsing needs an institution-approved "system" search scope most FHIR
        # servers don't grant. Real usage is SMART App Launch handing this adapter one patient id
        # from the EMR context (see smart_launch.py), not a sidebar list -- so this is an honest
        # NotImplementedError, not a silently empty list.
        raise NotImplementedError('FHIRAdapter.list() is not implemented: patient roster browsing '
                                   'requires an institution-approved search scope. Use get(patient_id) '
                                   'with an id supplied by the calling EMR/SMART launch context.')

    def get(self, pid):
        try:
            fhir_patient=self._get(f'Patient/{pid}')
        except httpx.HTTPStatusError as e:
            if e.response.status_code==404:return None
            raise
        return self._to_patient(fhir_patient, pid)

    def bundle(self, pid):
        # A real FHIR server already serves a canonical bundle for a patient's compartment;
        # pass it through rather than re-deriving one, so /fhir stays honest about being a
        # passthrough here (unlike DemoAdapter.bundle, which IS a demo projection).
        return self._get(f'Patient/{pid}/$everything')

    def _to_patient(self, fhir_patient, pid):
        missing=[]
        name=(fhir_patient.get('name') or [{}])[0]
        display_name=name.get('text') or ' '.join([*name.get('given',[]), name.get('family','')]).strip()
        if not display_name:display_name=pid;missing.append('patient name')
        sex=fhir_patient.get('gender')
        if sex not in ('male','female'):missing.append('patient sex (missing or not male/female)')
        birth_date=fhir_patient.get('birthDate')
        age=0
        if birth_date:
            b=_date.fromisoformat(birth_date);today=_date.today()
            age=today.year-b.year-((today.month,today.day)<(b.month,b.day))
        else:
            missing.append('birth date')

        conditions=[]
        for c in self._search('Condition', pid):
            code=c.get('code',{})
            text=code.get('text') or (code.get('coding') or [{}])[0].get('display')
            if text:conditions.append(text)
        if not conditions:missing.append('condition history (none returned)')

        medications=[]
        for kind in ('MedicationRequest','MedicationStatement'):
            for m in self._search(kind, pid):
                coding=(m.get('medicationCodeableConcept',{}).get('coding') or [{}])[0]
                drug_id=coding.get('code') or 'unknown'
                status=m.get('status','active')
                medications.append(Medication(drug_id=drug_id,
                    status='active' if status in ('active','in-progress') else 'stopped',
                    note=f'source: {kind}/{m.get("id","")}'))
        if not medications:missing.append('medication list (none returned)')

        allergies=[]
        for a in self._search('AllergyIntolerance', pid):
            code=a.get('code',{})
            substance=code.get('text') or (code.get('coding') or [{}])[0].get('display') or 'unknown'
            severity=((a.get('reaction') or [{}])[0].get('severity') or 'unknown').upper()
            if severity not in ('MILD','MODERATE','SEVERE'):severity='UNKNOWN'
            allergies.append(Allergy(substance=substance, severity=severity))

        labs=[]
        height_cm=None; weight_kg=None
        for o in self._search('Observation', pid):
            value=o.get('valueQuantity')
            code=o.get('code',{})
            coding=code.get('coding') or [{}]
            loinc=next((c.get('code') for c in coding if str(c.get('system','')).endswith('loinc.org')), None)
            if value is not None and loinc=='8302-2':  # Body height
                height_cm=_height_cm(value) if height_cm is None else height_cm
                continue
            if value is not None and loinc=='29463-7':  # Body weight
                weight_kg=_weight_kg(value) if weight_kg is None else weight_kg
                continue
            eff=_fhir_date(o.get('effectiveDateTime'))
            text=code.get('text') or coding[0].get('display')
            if value is not None and eff is not None and text:
                labs.append(Lab(name=text, value=value.get('value',0), unit=value.get('unit',''), date=eff))
        if not labs:missing.append('observations/labs (none returned)')
        # height_cm/weight_kg only feed the 3D viewer's body-scale approximation, never the risk
        # model or rule engine -- but a missing/unrecognized-unit Observation is still disclosed
        # rather than silently defaulting to an average build.
        if height_cm is None:missing.append('height (no body height Observation, LOINC 8302-2, in cm/in)')
        if weight_kg is None:missing.append('weight (no body weight Observation, LOINC 29463-7, in kg/lb)')

        # Encounter/DiagnosticReport/ImagingStudy: genuinely optional history (unlike
        # medications/conditions/labs, a patient legitimately having none isn't a data gap), so an
        # empty result here is not added to `missing`.
        encounters=[]
        for e in self._search('Encounter', pid):
            type_text=((e.get('type') or [{}])[0].get('text')
                       or (((e.get('type') or [{}])[0].get('coding') or [{}])[0].get('display'))
                       or ((e.get('class') or {}).get('display')) or '')
            encounters.append(Encounter(id=e.get('id', pid), date=_fhir_date((e.get('period') or {}).get('start')),
                                         type=type_text, status=e.get('status','')))

        diagnostic_reports=[]
        for r in self._search('DiagnosticReport', pid):
            code=r.get('code',{})
            name=code.get('text') or (code.get('coding') or [{}])[0].get('display') or ''
            when=r.get('effectiveDateTime') or r.get('issued')
            diagnostic_reports.append(DiagnosticReport(id=r.get('id', pid), date=_fhir_date(when),
                                                         name=name, status=r.get('status',''),
                                                         conclusion=r.get('conclusion','')))

        imaging_studies=[]
        for s in self._search('ImagingStudy', pid):
            modality=((s.get('modality') or [{}])[0].get('display')
                      or (s.get('modality') or [{}])[0].get('code') or '')
            imaging_studies.append(ImagingStudy(id=s.get('id', pid), date=_fhir_date(s.get('started')),
                                                 modality=modality, description=s.get('description','')))

        return Patient(id=pid, name=display_name, age=age, sex=sex or 'unspecified',
                        diagnosis=conditions[0] if conditions else '', scenario='',
                        medications=medications, conditions=conditions, allergies=allergies,
                        labs=labs, history=[], missing=missing, demo=True,
                        height_cm=height_cm, weight_kg=weight_kg,
                        encounters=encounters, diagnostic_reports=diagnostic_reports,
                        imaging_studies=imaging_studies)

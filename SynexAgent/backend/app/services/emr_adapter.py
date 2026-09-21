"""Demo adapter boundary. FHIR export is a demo projection, not a certified interface."""
import json
from pathlib import Path
from ..schemas import Patient
from .rule_engine import DRUGS

class DemoAdapter:
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
        return {'resourceType':'Bundle','type':'collection','entry':[{'resource':r} for r in resources]}

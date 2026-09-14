"""Run after installing a Jetson-compatible ORT build, or on any CPU PC."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.services.risk_inference import RiskEngine
from app.services.emr_adapter import DemoAdapter
from app.services.clinical_agent import ClinicalAgent
engine=RiskEngine();print(json.dumps(engine.health(),indent=2))
agent=ClinicalAgent(engine)
for patient in DemoAdapter().list():
    a=agent.run(patient)
    print(patient.id,a['risk']['risk_probability'],a['training_counts'])

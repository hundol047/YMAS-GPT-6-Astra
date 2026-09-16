from typing import Annotated, Literal
from datetime import date
from pydantic import BaseModel, ConfigDict, Field, field_validator

Unit = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class RiskFeatures(StrictModel):
    drug_conflict: Unit
    comorbidity_load: Unit
    age_risk: Unit
    allergy_flag: Literal[0.0, 1.0]
    adverse_history: Unit
    polypharmacy_load: Unit
    therapy_duration_load: Unit

class Medication(StrictModel):
    drug_id: str = Field(min_length=1, max_length=80)
    dispenses: float | None = Field(default=None, ge=0, le=10000, allow_inf_nan=False)
    started: date | None = None
    status: Literal['active','stopped'] = 'active'
    note: str = Field(default='', max_length=300)

class Allergy(StrictModel):
    substance: str
    category: Literal['medication','food','environment'] = 'medication'
    severity: Literal['NONE','MILD','MODERATE','SEVERE','UNKNOWN'] = 'UNKNOWN'
    reaction: str = ''

class Lab(StrictModel):
    name: str
    value: float = Field(allow_inf_nan=False)
    unit: str
    date: date
    low: float | None = Field(default=None, allow_inf_nan=False)
    high: float | None = Field(default=None, allow_inf_nan=False)

class Patient(StrictModel):
    id: str
    name: str
    age: int = Field(ge=0, le=120)
    sex: str
    diagnosis: str
    scenario: str = ''
    medications: list[Medication] = Field(max_length=100)
    conditions: list[str] = Field(max_length=100)
    allergies: list[Allergy] = Field(max_length=100)
    labs: list[Lab] = Field(max_length=500)
    history: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    # Optional, patient-reported build. Never used by the risk model (see docs/MODEL_CARD.md's
    # fixed 7-feature contract) or the rule engine -- purely for the 3D viewer's body-scale
    # approximation (frontend/src/data/anatomyMap.js bodyScaleFor). Absent for demo patients that
    # never had this recorded; never guessed.
    height_cm: float | None = Field(default=None, ge=30, le=250)
    weight_kg: float | None = Field(default=None, ge=1, le=400)
    demo: Literal[True] = True

class PatientRequest(StrictModel):
    patient_id: str

class SimulationRequest(PatientRequest):
    drug_id: str
    dispenses: float | None = Field(default=1, ge=0, le=10000, allow_inf_nan=False)

class FeedbackRequest(StrictModel):
    analysis_id: str
    alert_id: str
    rating: Literal['useful','not_useful','incorrect','already_known','needs_more_information']
    comment: str = Field(default='', max_length=500)

class ReviewRequest(StrictModel):
    analysis_id: str
    alert_id: str
    action: Literal['reviewed','dismissed','deferred']
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def nonblank_reason(cls, value):
        if not value.strip():
            raise ValueError("Review reason must not be blank")
        return value.strip()

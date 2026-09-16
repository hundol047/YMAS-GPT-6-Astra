from typing import Annotated, Literal
from datetime import date
from pydantic import BaseModel, ConfigDict, Field, field_validator

Unit = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
# `date | None = None` inside a class whose field is itself named `date` self-shadows: Python binds
# the RHS `None` to the class-local name `date` before evaluating the annotation, so `date | None`
# becomes `None | None` (TypeError). This alias sidesteps that for Encounter/DiagnosticReport/
# ImagingStudy below, all of which have an optional `date` field.
OptionalDate = date | None
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

class Encounter(StrictModel):
    id: str
    date: OptionalDate = None
    type: str = ''
    status: str = ''

class DiagnosticReport(StrictModel):
    id: str
    date: OptionalDate = None
    name: str = ''
    status: str = ''
    conclusion: str = ''

class ImagingStudy(StrictModel):
    id: str
    date: OptionalDate = None
    modality: str = ''
    description: str = ''

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
    # Optional, additive clinical history. Not consumed by the risk model or rule engine (same
    # 7-feature contract as always) -- exposed so FHIRAdapter can surface real Encounter/
    # DiagnosticReport/ImagingStudy data instead of just fetching and discarding it.
    encounters: list[Encounter] = Field(default_factory=list, max_length=200)
    diagnostic_reports: list[DiagnosticReport] = Field(default_factory=list, max_length=200)
    imaging_studies: list[ImagingStudy] = Field(default_factory=list, max_length=200)
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

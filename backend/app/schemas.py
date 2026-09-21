from typing import Annotated, Literal, Optional, List
from datetime import date
from pydantic import BaseModel, ConfigDict, Field, field_validator

Unit = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
# `date | None = None` inside a class whose field is itself named `date` self-shadows: Python binds
# the RHS `None` to the class-local name `date` before evaluating the annotation, so `date | None`
# becomes `None | None` (TypeError). This alias sidesteps that for Encounter/DiagnosticReport/
# ImagingStudy below, all of which have an optional `date` field.
# Written as typing.Optional (not `date | None`, PEP 604) so this whole module imports cleanly on
# Python 3.8 too -- see backend/requirements-jetpack5.txt / docs/JETSON_DEPLOYMENT.md for why: the
# `int | None`-style union operator on bare types is only supported from Python 3.10 (Jetson AGX
# Orin + JetPack 5.1.2 ships Python 3.8.10), and Pydantic v2 resolves every field annotation to a
# real type object when building its validation schema, so this can't be dodged with
# `from __future__ import annotations` the way a plain internal function's annotation can.
OptionalDate = Optional[date]
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
    dispenses: Optional[float] = Field(default=None, ge=0, le=10000, allow_inf_nan=False)
    started: Optional[date] = None
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
    low: Optional[float] = Field(default=None, allow_inf_nan=False)
    high: Optional[float] = Field(default=None, allow_inf_nan=False)

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

class VitalSigns(StrictModel):
    id: str
    encounter_id: str
    sbp: Optional[int] = Field(default=None, ge=40, le=300)
    dbp: Optional[int] = Field(default=None, ge=20, le=200)
    heart_rate: Optional[int] = Field(default=None, ge=20, le=250)
    respiratory_rate: Optional[int] = Field(default=None, ge=4, le=60)
    temperature_c: Optional[float] = Field(default=None, ge=25, le=45, allow_inf_nan=False)
    spo2: Optional[int] = Field(default=None, ge=0, le=100)
    # Encounter-time snapshot, independent of Patient.height_cm/weight_kg (which is a single
    # latest-known value used only for the 3D viewer). BMI is never stored -- see
    # backend/app/services/vitals.py's bmi() -- so it can never go stale relative to these two.
    height_cm: Optional[float] = Field(default=None, ge=30, le=250)
    weight_kg: Optional[float] = Field(default=None, ge=1, le=400)
    measured_at: str
    recorder: str = ''

class ClinicalNoteAmendment(StrictModel):
    author: str = Field(min_length=1)
    # Mandatory -- an amendment to a signed note must always say who changed it and why. There is
    # no code path that creates an amendment without both (see ClinicalNoteRepository.amend());
    # a PATCH on a signed note is rejected outright rather than silently becoming an amendment.
    reason: str = Field(min_length=1, max_length=500)
    created_at: str
    subjective: str = ''
    objective: str = ''
    assessment: str = ''
    plan: str = ''

class ClinicalNote(StrictModel):
    id: str
    encounter_id: str
    patient_id: str
    subjective: str = Field(default='', max_length=4000)
    objective: str = Field(default='', max_length=4000)
    assessment: str = Field(default='', max_length=4000)
    plan: str = Field(default='', max_length=4000)
    status: Literal['draft','signed'] = 'draft'
    author: str
    created_at: str
    updated_at: str
    signed_at: Optional[str] = None
    # A signed note's S/O/A/P fields above are frozen at sign time (enforced in
    # ClinicalNoteRepository, not here) -- any later edit becomes a new amendment instead of
    # overwriting the original, so the signed record is never silently rewritten.
    amendments: List[ClinicalNoteAmendment] = Field(default_factory=list, max_length=100)

class Diagnosis(StrictModel):
    id: str
    patient_id: str
    encounter_id: str
    code: str = ''
    code_system: Literal['ICD-10','SNOMED-CT','text'] = 'text'
    display_name: str = Field(min_length=1, max_length=200)
    diagnosis_type: Literal['primary','secondary'] = 'secondary'
    status: Literal['active','resolved'] = 'active'
    diagnosed_at: str
    clinician: str = ''

class MedicationOrder(StrictModel):
    id: str
    patient_id: str
    encounter_id: str
    medication_code: str = Field(min_length=1, max_length=80)  # drug_catalog.json id
    medication_name: str = ''
    dose: float = Field(gt=0, le=100000, allow_inf_nan=False)
    dose_unit: str = Field(min_length=1, max_length=20)
    route: Literal['PO','IV','IM','SC','topical']
    frequency: str = Field(default='', max_length=40)
    duration: str = Field(default='', max_length=40)
    quantity: Optional[float] = Field(default=None, ge=0, le=100000, allow_inf_nan=False)
    prn: bool = False
    indication: str = Field(default='', max_length=200)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    prescriber: str = ''
    ordered_at: str
    status: Literal['pending_review','confirmed','cancelled'] = 'pending_review'
    # Required (enforced in the /medication-orders endpoint, not here) only when the SynexAgent
    # precheck raised a warning and the clinician confirms anyway.
    override_reason: Optional[str] = Field(default=None, max_length=500)

    @field_validator('end_date')
    @classmethod
    def end_not_before_start(cls, v, info):
        start = info.data.get('start_date')
        if v is not None and start is not None and v < start:
            raise ValueError('end_date must not be before start_date')
        return v

class LabOrder(StrictModel):
    id: str
    patient_id: str
    encounter_id: str
    test_code: str = ''
    test_name: str = Field(min_length=1, max_length=120)
    panel: str = ''
    priority: Literal['routine','urgent','stat'] = 'routine'
    indication: str = Field(default='', max_length=200)
    ordering_physician: str = ''
    ordered_at: str
    status: Literal['ordered','collected','processing','completed','cancelled'] = 'ordered'

class LabResult(StrictModel):
    id: str
    lab_order_id: str
    patient_id: str
    test_code: str = ''
    test_name: str
    value: float = Field(allow_inf_nan=False)
    unit: str = ''
    reference_low: Optional[float] = Field(default=None, allow_inf_nan=False)
    reference_high: Optional[float] = Field(default=None, allow_inf_nan=False)
    abnormal_flag: Literal['normal','high','low','critical'] = 'normal'
    measured_at: str
    reported_at: str

class ClinicalEncounter(StrictModel):
    # Named ClinicalEncounter (not Encounter) to avoid colliding with the FHIR-resource-shaped
    # `Encounter` model above, which Patient.encounters already uses for FHIRAdapter passthrough.
    id: str
    patient_id: str
    encounter_type: Literal['outpatient','inpatient','emergency','telemedicine']
    department: str = ''
    attending_physician: str = ''
    started_at: str
    ended_at: Optional[str] = None
    status: Literal['in_progress','completed','cancelled'] = 'in_progress'
    chief_complaint: str = Field(default='', max_length=300)
    vital_signs: List[VitalSigns] = Field(default_factory=list, max_length=50)
    note_ids: List[str] = Field(default_factory=list, max_length=50)
    diagnosis_ids: List[str] = Field(default_factory=list, max_length=50)
    medication_order_ids: List[str] = Field(default_factory=list, max_length=50)
    lab_order_ids: List[str] = Field(default_factory=list, max_length=50)
    signed: bool = False

class Patient(StrictModel):
    id: str
    name: str
    age: int = Field(ge=0, le=120)
    sex: str
    diagnosis: str
    scenario: str = ''
    medications: List[Medication] = Field(max_length=100)
    conditions: List[str] = Field(max_length=100)
    allergies: List[Allergy] = Field(max_length=100)
    labs: List[Lab] = Field(max_length=500)
    history: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    # Optional, patient-reported build. Never used by the risk model (see docs/MODEL_CARD.md's
    # fixed 7-feature contract) or the rule engine -- purely for the 3D viewer's body-scale
    # approximation (frontend/src/data/anatomyMap.js bodyScaleFor). Absent for demo patients that
    # never had this recorded; never guessed.
    height_cm: Optional[float] = Field(default=None, ge=30, le=250)
    weight_kg: Optional[float] = Field(default=None, ge=1, le=400)
    # Optional, additive clinical history. Not consumed by the risk model or rule engine (same
    # 7-feature contract as always) -- exposed so FHIRAdapter can surface real Encounter/
    # DiagnosticReport/ImagingStudy data instead of just fetching and discarding it.
    encounters: List[Encounter] = Field(default_factory=list, max_length=200)
    diagnostic_reports: List[DiagnosticReport] = Field(default_factory=list, max_length=200)
    imaging_studies: List[ImagingStudy] = Field(default_factory=list, max_length=200)
    # Clinical Workspace demographic/identifier fields. All optional so every existing
    # patients.json entry and every existing test payload (which omit them) keeps validating.
    mrn: Optional[str] = Field(default=None, max_length=40)
    date_of_birth: OptionalDate = None
    phone: Optional[str] = Field(default=None, max_length=40)
    address: Optional[str] = Field(default=None, max_length=200)
    blood_type: Optional[str] = Field(default=None, max_length=10)
    emergency_contact: Optional[str] = Field(default=None, max_length=120)
    # Structured clinical history. `conditions`/`medications`/`labs` above remain the flat,
    # unchanged contract the rule engine/risk model read -- creating a Diagnosis/MedicationOrder/
    # LabResult also dual-writes into those flat lists (see repositories.py), so this structured
    # layer is additive and never replaces the existing pipeline's inputs.
    problem_list: List[Diagnosis] = Field(default_factory=list, max_length=100)
    clinical_encounters: List[ClinicalEncounter] = Field(default_factory=list, max_length=100)
    demo: Literal[True] = True

class PatientRequest(StrictModel):
    patient_id: str

class SimulationRequest(PatientRequest):
    drug_id: str
    dispenses: Optional[float] = Field(default=1, ge=0, le=10000, allow_inf_nan=False)

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

# --- Clinical Workspace request bodies (main.py's /encounters, /notes, /medication-orders,
# /lab-orders endpoints). Small, endpoint-scoped request shapes -- not the same as the stored
# resource models above (e.g. no id/status/timestamps, which the repository assigns). ------------

class EncounterCreateRequest(StrictModel):
    encounter_type: Literal['outpatient','inpatient','emergency','telemedicine']
    department: str = Field(default='', max_length=80)
    attending_physician: str = Field(default='', max_length=80)
    chief_complaint: str = Field(default='', max_length=300)

class EncounterUpdateRequest(StrictModel):
    status: Optional[Literal['in_progress','completed','cancelled']] = None
    ended_at: Optional[str] = None
    signed: Optional[bool] = None

class VitalsCreateRequest(StrictModel):
    sbp: Optional[int] = Field(default=None, ge=40, le=300)
    dbp: Optional[int] = Field(default=None, ge=20, le=200)
    heart_rate: Optional[int] = Field(default=None, ge=20, le=250)
    respiratory_rate: Optional[int] = Field(default=None, ge=4, le=60)
    temperature_c: Optional[float] = Field(default=None, ge=25, le=45, allow_inf_nan=False)
    spo2: Optional[int] = Field(default=None, ge=0, le=100)
    height_cm: Optional[float] = Field(default=None, ge=30, le=250)
    weight_kg: Optional[float] = Field(default=None, ge=1, le=400)
    recorder: str = Field(default='', max_length=80)

class NoteCreateRequest(StrictModel):
    author: str = Field(min_length=1, max_length=80)
    subjective: str = Field(default='', max_length=4000)
    objective: str = Field(default='', max_length=4000)
    assessment: str = Field(default='', max_length=4000)
    plan: str = Field(default='', max_length=4000)

class NoteUpdateRequest(StrictModel):
    subjective: Optional[str] = Field(default=None, max_length=4000)
    objective: Optional[str] = Field(default=None, max_length=4000)
    assessment: Optional[str] = Field(default=None, max_length=4000)
    plan: Optional[str] = Field(default=None, max_length=4000)

class NoteAmendRequest(StrictModel):
    author: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=1, max_length=500)
    subjective: Optional[str] = Field(default=None, max_length=4000)
    objective: Optional[str] = Field(default=None, max_length=4000)
    assessment: Optional[str] = Field(default=None, max_length=4000)
    plan: Optional[str] = Field(default=None, max_length=4000)

class DiagnosisCreateRequest(StrictModel):
    display_name: str = Field(min_length=1, max_length=200)
    diagnosis_type: Literal['primary','secondary'] = 'secondary'
    code: str = Field(default='', max_length=40)
    code_system: Literal['ICD-10','SNOMED-CT','text'] = 'text'
    clinician: str = Field(default='', max_length=80)

class MedicationOrderCreateRequest(StrictModel):
    medication_code: str = Field(min_length=1, max_length=80)
    medication_name: str = Field(default='', max_length=120)
    dose: float = Field(gt=0, le=100000, allow_inf_nan=False)
    dose_unit: str = Field(min_length=1, max_length=20)
    route: Literal['PO','IV','IM','SC','topical']
    frequency: str = Field(default='', max_length=40)
    duration: str = Field(default='', max_length=40)
    quantity: Optional[float] = Field(default=None, ge=0, le=100000, allow_inf_nan=False)
    prn: bool = False
    indication: str = Field(default='', max_length=200)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    prescriber: str = Field(default='', max_length=80)
    # Required by the /medication-orders endpoint (not here) only when the server-side SynexAgent
    # precheck (re-run there, never trusted from the client) finds a new warning; a clean precheck
    # can confirm with this omitted. /medication-orders/precheck ignores this field entirely.
    override_reason: Optional[str] = Field(default=None, max_length=500)

    @field_validator('end_date')
    @classmethod
    def end_not_before_start(cls, v, info):
        start = info.data.get('start_date')
        if v is not None and start is not None and v < start:
            raise ValueError('end_date must not be before start_date')
        return v

class LabOrderCreateRequest(StrictModel):
    test_code: str = Field(default='', max_length=40)
    test_name: str = Field(min_length=1, max_length=120)
    panel: str = Field(default='', max_length=80)
    priority: Literal['routine','urgent','stat'] = 'routine'
    indication: str = Field(default='', max_length=200)
    ordering_physician: str = Field(default='', max_length=80)

class LabResultCreateRequest(StrictModel):
    value: float = Field(allow_inf_nan=False)
    unit: str = Field(default='', max_length=20)
    reference_low: Optional[float] = Field(default=None, allow_inf_nan=False)
    reference_high: Optional[float] = Field(default=None, allow_inf_nan=False)

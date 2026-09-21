"""Explicit reference-table medical terminology normalization.

This module NEVER guesses a code at request time. Every RxNorm/ATC/LOINC/ICD-10 value below is a
fixed, reviewable table entry for a specific, verifiable identifier. Anything not in these tables
comes back with mapping_status='unmapped' (never a fabricated code) so the caller can show that
honestly instead of silently treating it as normal.

Scope note: this demo's drug catalog has 178 entries (backend/data/drug_catalog.json); only a
subset of well-established ingredients are mapped here. Extending coverage means adding verified
rows to these tables (ideally sourced from a real RxNorm/LOINC/ICD-10 terminology service), never
inferring a code from the drug name at runtime.
"""
from dataclasses import dataclass, field
from typing import List, Literal, Optional

MappingStatus = Literal['mapped', 'partial', 'unmapped', 'ambiguous']


@dataclass
class NormalizedCode:
    source_system: str
    source_code: str
    display: str
    target_system: Optional[str] = None
    target_code: Optional[str] = None
    target_display: Optional[str] = None
    mapping_status: MappingStatus = 'unmapped'
    note: str = ''

    def to_dict(self):
        return {
            'source_system': self.source_system, 'source_code': self.source_code, 'display': self.display,
            'target_system': self.target_system, 'target_code': self.target_code, 'target_display': self.target_display,
            'mapping_status': self.mapping_status, 'note': self.note,
        }


# --- Medication: internal drug_catalog.json id -> RxNorm ingredient RxCUI + ATC. -----------------
# Only well-established, stable ingredient-level identifiers are included; combination products and
# less common entries in the catalog are intentionally left unmapped rather than guessed.
RXNORM_ATC_BY_DRUG_ID = {
    'warfarin': {'rxnorm': ('11289', 'Warfarin'), 'atc': ('B01AA03', 'warfarin')},
    'aspirin': {'rxnorm': ('1191', 'Aspirin'), 'atc': ('B01AC06', 'acetylsalicylic acid')},
    'ibuprofen': {'rxnorm': ('5640', 'Ibuprofen'), 'atc': ('M01AE01', 'ibuprofen')},
    'metformin': {'rxnorm': ('6809', 'Metformin'), 'atc': ('A10BA02', 'metformin')},
    'atorvastatin': {'rxnorm': ('83367', 'Atorvastatin'), 'atc': ('C10AA05', 'atorvastatin')},
    'omeprazole': {'rxnorm': ('7646', 'Omeprazole'), 'atc': ('A02BC01', 'omeprazole')},
    'amoxicillin': {'rxnorm': ('723', 'Amoxicillin'), 'atc': ('J01CA04', 'amoxicillin')},
    'amlodipine': {'rxnorm': ('17767', 'Amlodipine'), 'atc': ('C08CA01', 'amlodipine')},
    'losartan': {'rxnorm': ('52175', 'Losartan'), 'atc': ('C09CA01', 'losartan')},
    'clopidogrel': {'rxnorm': ('32968', 'Clopidogrel'), 'atc': ('B01AC04', 'clopidogrel')},
    'digoxin': {'rxnorm': ('3407', 'Digoxin'), 'atc': ('C01AA05', 'digoxin')},
    'furosemide': {'rxnorm': ('4603', 'Furosemide'), 'atc': ('C03CA01', 'furosemide')},
    'levothyroxine': {'rxnorm': ('10582', 'Levothyroxine'), 'atc': ('H03AA01', 'levothyroxine')},
    'insulin': {'rxnorm': ('5856', 'Insulin'), 'atc': ('A10A', 'insulin')},
    'vitamind': {'rxnorm': ('67662', 'Cholecalciferol'), 'atc': ('A11CC05', 'colecalciferol')},
    # Added to cover every drug_id actually referenced by backend/data/patients.json -- before this,
    # 6 of the 13 drugs used by the bundled demo patients had no RxNorm/ATC row at all, so
    # /patients/{pid}/terminology silently under-reported coverage for real demo cases, not just
    # hypothetical catalog entries.
    'acetaminophen': {'rxnorm': ('161', 'Acetaminophen'), 'atc': ('N02BE01', 'paracetamol')},
    'albuterol': {'rxnorm': ('435', 'Albuterol'), 'atc': ('R03AC02', 'salbutamol')},
    'haloperidol': {'rxnorm': ('5093', 'Haloperidol'), 'atc': ('N05AD01', 'haloperidol')},
    'lisinopril': {'rxnorm': ('29046', 'Lisinopril'), 'atc': ('C09AA03', 'lisinopril')},
    'lorazepam': {'rxnorm': ('6470', 'Lorazepam'), 'atc': ('N05BA06', 'lorazepam')},
    'simvastatin': {'rxnorm': ('36567', 'Simvastatin'), 'atc': ('C10AA01', 'simvastatin')},
}

# Reverse index (RxCUI -> internal drug_catalog.json id), derived from RXNORM_ATC_BY_DRUG_ID above --
# never a separately-maintained or separately-guessed table, so it can't drift from the forward
# table or introduce a code that isn't already verified there. Used by FHIRAdapter._to_patient
# (emr_adapter.py) to recover a matching internal drug_id when an incoming FHIR MedicationRequest/
# MedicationStatement carries a standard RxNorm coding instead of our own catalog id -- without this,
# a real hospital's RxNorm-coded medication would show up as an unrecognized drug_id (still visible
# to the clinician and still flagged in Patient.missing via feature_engineering.py's `unknown` list,
# never silently dropped) instead of matching the catalog/rule engine.
RXCUI_TO_DRUG_ID = {row['rxnorm'][0]: drug_id for drug_id, row in RXNORM_ATC_BY_DRUG_ID.items()}

# --- Observation / lab: patient.labs `name` -> LOINC. ---------------------------------------------
LOINC_BY_LAB_NAME = {
    'Creatinine': ('2160-0', 'Creatinine [Mass/volume] in Serum or Plasma'),
    'eGFR': ('33914-3', 'Estimated glomerular filtration rate'),
    'AST': ('1920-8', 'Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma'),
    'ALT': ('1742-6', 'Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma'),
    'INR': ('6301-6', 'INR in Platelet poor plasma by Coagulation assay'),
    'Glucose': ('2345-7', 'Glucose [Mass/volume] in Serum or Plasma'),
    'Potassium': ('2823-3', 'Potassium [Moles/volume] in Serum or Plasma'),
}

# --- Condition: free-text condition string (as stored on Patient.conditions) -> ICD-10 + SNOMED CT.
ICD10_SNOMED_BY_CONDITION = {
    '고혈압': {'icd10': ('I10', 'Essential (primary) hypertension'), 'snomed': ('38341003', 'Hypertensive disorder')},
    '만성신부전': {'icd10': ('N18.9', 'Chronic kidney disease, unspecified'), 'snomed': ('709044004', 'Chronic kidney disease')},
    '고칼륨혈증': {'icd10': ('E87.5', 'Hyperkalemia'), 'snomed': ('14140009', 'Hyperkalemia')},
    '심방세동': {'icd10': ('I48.91', 'Unspecified atrial fibrillation'), 'snomed': ('49436004', 'Atrial fibrillation')},
}


def normalize_medication(drug_id: str, display: str) -> NormalizedCode:
    row = RXNORM_ATC_BY_DRUG_ID.get(drug_id)
    if not row:
        return NormalizedCode('synexagent:drug-catalog', drug_id, display, mapping_status='unmapped',
                               note='No verified RxNorm/ATC mapping in this demo\'s reference table')
    code, name = row['rxnorm']
    return NormalizedCode('synexagent:drug-catalog', drug_id, display, 'RxNorm', code, name, 'mapped')


def normalize_medication_atc(drug_id: str, display: str) -> NormalizedCode:
    row = RXNORM_ATC_BY_DRUG_ID.get(drug_id)
    if not row:
        return NormalizedCode('synexagent:drug-catalog', drug_id, display, mapping_status='unmapped',
                               note='No verified RxNorm/ATC mapping in this demo\'s reference table')
    code, name = row['atc']
    return NormalizedCode('synexagent:drug-catalog', drug_id, display, 'ATC', code, name, 'mapped')


def normalize_lab(name: str) -> NormalizedCode:
    row = LOINC_BY_LAB_NAME.get(name)
    if not row:
        return NormalizedCode('synexagent:lab-name', name, name, mapping_status='unmapped',
                               note='No verified LOINC mapping in this demo\'s reference table')
    code, display = row
    return NormalizedCode('synexagent:lab-name', name, name, 'LOINC', code, display, 'mapped')


def normalize_condition(text: str) -> List[NormalizedCode]:
    row = ICD10_SNOMED_BY_CONDITION.get(text)
    if not row:
        return [NormalizedCode('synexagent:condition-text', text, text, mapping_status='unmapped',
                                note='No verified ICD-10/SNOMED mapping in this demo\'s reference table')]
    out = []
    if 'icd10' in row:
        code, display = row['icd10']
        out.append(NormalizedCode('synexagent:condition-text', text, text, 'ICD-10', code, display, 'mapped'))
    if 'snomed' in row:
        code, display = row['snomed']
        out.append(NormalizedCode('synexagent:condition-text', text, text, 'SNOMED CT', code, display, 'mapped'))
    return out


def patient_terminology(patient, drug_catalog: dict) -> dict:
    """Normalize everything on a patient at once. Additive/read-only -- does not change any
    existing response shape; callers opt in via a dedicated endpoint."""
    meds = []
    for m in patient.medications:
        display = drug_catalog.get(m.drug_id, {}).get('name_ko', m.drug_id)
        meds.append({'drug_id': m.drug_id, 'status': m.status,
                     'rxnorm': normalize_medication(m.drug_id, display).to_dict(),
                     'atc': normalize_medication_atc(m.drug_id, display).to_dict()})
    labs = [{'name': l.name, 'date': str(l.date), 'loinc': normalize_lab(l.name).to_dict()} for l in patient.labs]
    conditions = [{'text': c, 'codes': [x.to_dict() for x in normalize_condition(c)]} for c in patient.conditions]
    counts = {
        'medications_mapped': sum(1 for m in meds if m['rxnorm']['mapping_status'] == 'mapped'),
        'medications_unmapped': sum(1 for m in meds if m['rxnorm']['mapping_status'] == 'unmapped'),
        'labs_mapped': sum(1 for l in labs if l['loinc']['mapping_status'] == 'mapped'),
        'labs_unmapped': sum(1 for l in labs if l['loinc']['mapping_status'] == 'unmapped'),
        'conditions_mapped': sum(1 for c in conditions if any(x['mapping_status'] == 'mapped' for x in c['codes'])),
        'conditions_unmapped': sum(1 for c in conditions if all(x['mapping_status'] == 'unmapped' for x in c['codes'])),
    }
    return {'patient_id': patient.id, 'medications': meds, 'labs': labs, 'conditions': conditions,
            'coverage': counts,
            'disclaimer': 'Fixed reference-table mapping for this demo\'s vocabulary only; not a certified terminology service.'}

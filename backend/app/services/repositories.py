"""Clinical Workspace repositories: thin classes wrapping DemoAdapter.mutate(pid) (the live,
in-process Patient object -- see emr_adapter.py), one per new resource type, styled after the
existing hand-rolled AuditStore/_LaunchStore (no ORM, narrow interface, easy to later swap the
backing store for Postgres without changing callers).

Two invariants enforced here, not just at the endpoint layer:
1. Dual-write idempotency. Confirming a MedicationOrder appends to patient.medications; cancelling
   a confirmed order flips that same entry to status='stopped' rather than leaving it orphaned.
   Both are guarded by the order's own status so a retried HTTP request (confirm-confirm,
   cancel-cancel) never double-appends or double-stops -- state transitions are checked before any
   mutation, and the dual-written Medication carries a stable `note='order:<order_id>'` marker so a
   defensive re-scan can also catch it. The same status-gate pattern protects LabOrder -> LabResult
   dual-writes into patient.labs.
2. A signed ClinicalNote's S/O/A/P fields are never overwritten. ClinicalNoteRepository.update()
   raises PermissionError on a signed note -- there is no code path that turns a PATCH into a
   silent amendment. amend() is the only way to change a signed note, and it requires both an
   author and a reason (see schemas.ClinicalNoteAmendment) and only ever appends to `amendments`.
"""
# Several classes below define a method literally named `list` (repository-pattern convention).
# Without this, a later method's own `-> list[...]` return annotation would resolve `list` to that
# method (class-body names shadow builtins the same way the `date`-self-shadow in schemas.py does)
# instead of the builtin, raising "'function' object is not subscriptable" at import time.
from __future__ import annotations
import uuid
from datetime import datetime, timezone

from ..schemas import (
    ClinicalEncounter, ClinicalNote, ClinicalNoteAmendment, Diagnosis, Medication,
    MedicationOrder, LabOrder, LabResult, Lab, VitalSigns,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f'{prefix}-{uuid.uuid4().hex[:12]}'


class NotFound(KeyError):
    pass


class EncounterRepository:
    def __init__(self, adapter):
        self.adapter = adapter
        self._patient_of: dict[str, str] = {}  # encounter_id -> patient_id, for endpoints keyed by encounter_id alone

    def list(self, patient_id) -> list[ClinicalEncounter]:
        return list(self.adapter.mutate(patient_id).clinical_encounters)

    def get(self, patient_id, encounter_id) -> ClinicalEncounter:
        for e in self.adapter.mutate(patient_id).clinical_encounters:
            if e.id == encounter_id:
                return e
        raise NotFound(encounter_id)

    def resolve(self, encounter_id) -> str:
        """patient_id for an encounter_id, when the caller (an /encounters/{eid}/... endpoint)
        doesn't already have it in the URL."""
        pid = self._patient_of.get(encounter_id)
        if pid is None:
            raise NotFound(encounter_id)
        return pid

    def get_by_id(self, encounter_id):
        pid = self.resolve(encounter_id)
        return pid, self.get(pid, encounter_id)

    def create(self, patient_id, *, encounter_type, department='', attending_physician='',
               chief_complaint='') -> ClinicalEncounter:
        p = self.adapter.mutate(patient_id)
        enc = ClinicalEncounter(id=_new_id('ENC'), patient_id=patient_id, encounter_type=encounter_type,
                                 department=department, attending_physician=attending_physician,
                                 started_at=_now(), status='in_progress', chief_complaint=chief_complaint)
        p.clinical_encounters.append(enc)
        self._patient_of[enc.id] = patient_id
        return enc

    def update(self, patient_id, encounter_id, **patch) -> ClinicalEncounter:
        p = self.adapter.mutate(patient_id)
        for i, e in enumerate(p.clinical_encounters):
            if e.id == encounter_id:
                updated = e.model_copy(update=patch)
                p.clinical_encounters[i] = updated
                return updated
        raise NotFound(encounter_id)

    def add_vitals(self, patient_id, encounter_id, **fields) -> VitalSigns:
        p = self.adapter.mutate(patient_id)
        for e in p.clinical_encounters:
            if e.id == encounter_id:
                v = VitalSigns(id=_new_id('VIT'), encounter_id=encounter_id, measured_at=fields.pop('measured_at', _now()), **fields)
                e.vital_signs.append(v)
                return v
        raise NotFound(encounter_id)

    def list_vitals(self, patient_id) -> list[VitalSigns]:
        out = []
        for e in self.adapter.mutate(patient_id).clinical_encounters:
            out.extend(e.vital_signs)
        return out


class ClinicalNoteRepository:
    def __init__(self, adapter):
        self.adapter = adapter
        self._notes: dict[str, ClinicalNote] = {}  # note_id -> note, indexed across all patients

    def get(self, note_id) -> ClinicalNote:
        n = self._notes.get(note_id)
        if n is None:
            raise NotFound(note_id)
        return n

    def list_for_encounter(self, patient_id, encounter_id) -> list[ClinicalNote]:
        return [n for n in self._notes.values() if n.patient_id == patient_id and n.encounter_id == encounter_id]

    def list_for_patient(self, patient_id) -> list[ClinicalNote]:
        return [n for n in self._notes.values() if n.patient_id == patient_id]

    def create(self, patient_id, encounter_id, *, author, subjective='', objective='', assessment='', plan='') -> ClinicalNote:
        enc_repo = EncounterRepository(self.adapter)
        enc = enc_repo.get(patient_id, encounter_id)  # 404s if the encounter doesn't exist
        now = _now()
        note = ClinicalNote(id=_new_id('NOTE'), encounter_id=encounter_id, patient_id=patient_id,
                             subjective=subjective, objective=objective, assessment=assessment, plan=plan,
                             status='draft', author=author, created_at=now, updated_at=now)
        self._notes[note.id] = note
        enc.note_ids.append(note.id)
        return note

    def update(self, note_id, **patch) -> ClinicalNote:
        note = self.get(note_id)
        if note.status == 'signed':
            # Never silently turn a PATCH on a signed note into an amendment -- the caller must
            # explicitly call amend() with an author and a reason.
            raise PermissionError('Signed clinical notes cannot be edited directly; use the '
                                   'amendment flow (author + reason required) instead.')
        updated = note.model_copy(update={**patch, 'updated_at': _now()})
        self._notes[note_id] = updated
        return updated

    def sign(self, note_id) -> ClinicalNote:
        note = self.get(note_id)
        if note.status == 'signed':
            return note  # idempotent: re-signing an already-signed note is a no-op, not an error
        signed = note.model_copy(update={'status': 'signed', 'signed_at': _now(), 'updated_at': _now()})
        self._notes[note_id] = signed
        return signed

    def amend(self, note_id, *, author, reason, subjective=None, objective=None, assessment=None, plan=None) -> ClinicalNote:
        note = self.get(note_id)
        if note.status != 'signed':
            raise PermissionError('Only a signed note can be amended; edit a draft directly via update().')
        amendment = ClinicalNoteAmendment(author=author, reason=reason, created_at=_now(),
                                           subjective=subjective or '', objective=objective or '',
                                           assessment=assessment or '', plan=plan or '')
        updated = note.model_copy(update={'amendments': [*note.amendments, amendment], 'updated_at': _now()})
        self._notes[note_id] = updated
        return updated


def _normalized_display(name: str) -> str:
    return ' '.join(name.strip().lower().split())


def _diagnosis_key(*, code, code_system, display_name):
    """Priority: code_system+code identifies a diagnosis when a code is given (a code is a code
    regardless of how the display text is phrased); only when the diagnosis has NO code do we fall
    back to the normalized display name. A coded diagnosis is never matched against an uncoded one
    by display text alone -- that would risk false-positive dedup between a generic free-text entry
    and an unrelated but similarly-worded coded diagnosis."""
    if code:
        return ('code', code_system, code)
    return ('name', _normalized_display(display_name))


class DiagnosisRepository:
    def __init__(self, adapter):
        self.adapter = adapter

    def _find_active_duplicate(self, p, *, code, code_system, display_name) -> Diagnosis | None:
        key = _diagnosis_key(code=code, code_system=code_system, display_name=display_name)
        for dx in p.problem_list:
            # Only ACTIVE diagnoses are deduped against -- a diagnosis resolved in the past and
            # newly reactivated is a genuinely new clinical event, not a network retry, and must be
            # allowed through (e.g. resolved 2025 AFib episode + a new active 2026 episode).
            if dx.status == 'active' and _diagnosis_key(code=dx.code, code_system=dx.code_system, display_name=dx.display_name) == key:
                return dx
        return None

    def find_active_duplicate(self, patient_id, *, code, code_system, display_name) -> Diagnosis | None:
        """Public read-only check for callers (main.py) that need to know BEFORE calling create()
        whether this would be a dedup no-op -- e.g. to skip logging a duplicate audit event for a
        network retry without duplicating the matching logic above."""
        return self._find_active_duplicate(self.adapter.mutate(patient_id), code=code, code_system=code_system, display_name=display_name)

    def create(self, patient_id, encounter_id, *, display_name, diagnosis_type='secondary', code='',
               code_system='text', clinician='') -> Diagnosis:
        p = self.adapter.mutate(patient_id)
        existing = self._find_active_duplicate(p, code=code, code_system=code_system, display_name=display_name)
        if existing is not None:
            # Idempotent, same style as ClinicalNoteRepository.sign()/MedicationOrderRepository.confirm():
            # a retried create for an already-active diagnosis returns the existing record rather
            # than minting a duplicate problem_list entry (which would also duplicate the
            # patient.conditions dual-write and the Timeline entry derived from problem_list).
            #
            # The Problem List entry (a patient-level "active condition") is conceptually distinct
            # from an Encounter's own record of addressing it -- reusing the existing Diagnosis must
            # NOT skip linking it to *this* encounter, or a later encounter that re-records the same
            # active problem would leave diagnosis_ids empty for it. _link_to_encounter is itself
            # idempotent (checked-before-append), so re-POSTing the same diagnosis to the SAME
            # encounter twice still yields a single id in diagnosis_ids, not a duplicate.
            self._link_to_encounter(p, encounter_id, existing.id)
            return existing
        diag = Diagnosis(id=_new_id('DX'), patient_id=patient_id, encounter_id=encounter_id,
                          code=code, code_system=code_system, display_name=display_name,
                          diagnosis_type=diagnosis_type, status='active', diagnosed_at=_now(), clinician=clinician)
        p.problem_list.append(diag)
        # Dual-write: the rule engine/anatomy mapping read patient.conditions (plain strings), so a
        # structured Diagnosis must also show up there or it would be invisible to every existing
        # analysis path. Idempotent: skip if this exact text is already present.
        if display_name not in p.conditions:
            p.conditions.append(display_name)
        self._link_to_encounter(p, encounter_id, diag.id)
        return diag

    def _link_to_encounter(self, p, encounter_id, diagnosis_id) -> None:
        for e in p.clinical_encounters:
            if e.id == encounter_id:
                if diagnosis_id not in e.diagnosis_ids:
                    e.diagnosis_ids.append(diagnosis_id)
                break

    def list(self, patient_id) -> list[Diagnosis]:
        return list(self.adapter.mutate(patient_id).problem_list)


class MedicationOrderRepository:
    def __init__(self, adapter):
        self.adapter = adapter
        self._orders: dict[str, MedicationOrder] = {}

    def get(self, order_id) -> MedicationOrder:
        o = self._orders.get(order_id)
        if o is None:
            raise NotFound(order_id)
        return o

    def list_for_patient(self, patient_id) -> list[MedicationOrder]:
        return [o for o in self._orders.values() if o.patient_id == patient_id]

    def create(self, patient_id, encounter_id, **fields) -> MedicationOrder:
        enc_repo = EncounterRepository(self.adapter)
        enc = enc_repo.get(patient_id, encounter_id)
        order = MedicationOrder(id=_new_id('RX'), patient_id=patient_id, encounter_id=encounter_id,
                                 ordered_at=_now(), status='pending_review', **fields)
        self._orders[order.id] = order
        enc.medication_order_ids.append(order.id)
        return order

    def confirm(self, order_id, *, override_reason=None) -> MedicationOrder:
        order = self.get(order_id)
        if order.status == 'confirmed':
            return order  # idempotent: a retried confirm must not double-append the medication
        if order.status == 'cancelled':
            raise ValueError('Cannot confirm a cancelled order')
        p = self.adapter.mutate(order.patient_id)
        marker = f'order:{order.id}'
        if not any(m.note == marker for m in p.medications):
            p.medications.append(Medication(drug_id=order.medication_code, dispenses=None,
                                              started=None, status='active', note=marker))
        confirmed = order.model_copy(update={'status': 'confirmed', 'override_reason': override_reason})
        self._orders[order_id] = confirmed
        return confirmed

    def cancel(self, order_id) -> MedicationOrder:
        order = self.get(order_id)
        if order.status == 'cancelled':
            return order  # idempotent
        if order.status == 'confirmed':
            p = self.adapter.mutate(order.patient_id)
            marker = f'order:{order.id}'
            for i, m in enumerate(p.medications):
                if m.note == marker:
                    p.medications[i] = m.model_copy(update={'status': 'stopped'})
                    break
        cancelled = order.model_copy(update={'status': 'cancelled'})
        self._orders[order_id] = cancelled
        return cancelled


class LabOrderRepository:
    def __init__(self, adapter):
        self.adapter = adapter
        self._orders: dict[str, LabOrder] = {}
        self._results: dict[str, LabResult] = {}  # order_id -> result (one result per order)

    def get(self, order_id) -> LabOrder:
        o = self._orders.get(order_id)
        if o is None:
            raise NotFound(order_id)
        return o

    def list_for_patient(self, patient_id) -> list[LabOrder]:
        return [o for o in self._orders.values() if o.patient_id == patient_id]

    def create(self, patient_id, encounter_id, **fields) -> LabOrder:
        enc_repo = EncounterRepository(self.adapter)
        enc = enc_repo.get(patient_id, encounter_id)
        order = LabOrder(id=_new_id('LAB'), patient_id=patient_id, encounter_id=encounter_id,
                          ordered_at=_now(), status='ordered', **fields)
        self._orders[order.id] = order
        enc.lab_order_ids.append(order.id)
        return order

    def cancel(self, order_id) -> LabOrder:
        order = self.get(order_id)
        if order.status in ('cancelled', 'completed'):
            return order  # idempotent no-op; a completed order is not retroactively cancellable
        cancelled = order.model_copy(update={'status': 'cancelled'})
        self._orders[order_id] = cancelled
        return cancelled

    def result_for(self, order_id) -> LabResult | None:
        return self._results.get(order_id)

    def submit_result(self, order_id, *, value, unit='', reference_low=None, reference_high=None) -> LabResult:
        order = self.get(order_id)
        existing = self._results.get(order_id)
        if existing is not None:
            return existing  # idempotent: a retried result submission returns the first result
        if order.status == 'cancelled':
            raise ValueError('Cannot record a result for a cancelled order')
        flag = 'normal'
        if reference_low is not None and value < reference_low:
            flag = 'low'
        elif reference_high is not None and value > reference_high:
            flag = 'high'
        now = _now()
        result = LabResult(id=_new_id('RES'), lab_order_id=order_id, patient_id=order.patient_id,
                            test_code=order.test_code, test_name=order.test_name, value=value, unit=unit,
                            reference_low=reference_low, reference_high=reference_high,
                            abnormal_flag=flag, measured_at=now, reported_at=now)
        self._results[order_id] = result
        self._orders[order_id] = order.model_copy(update={'status': 'completed'})
        # Dual-write into the flat Lab list the rule engine/feature_engineering/3D anatomy already
        # read (see rule_engine.py's lab_review check and feature_engineering.py's missing-labs
        # flag). Idempotent because submit_result() itself is idempotent per order above.
        p = self.adapter.mutate(order.patient_id)
        p.labs.append(Lab(name=order.test_name, value=value, unit=unit, date=now[:10],
                           low=reference_low, high=reference_high))
        return result

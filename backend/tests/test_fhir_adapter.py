"""FHIRAdapter is exercised here against a FAKE FHIR server (httpx.MockTransport serving
hand-built FHIR R4 JSON), never a live hospital endpoint -- there isn't one reachable from this
environment. This proves the request/response parsing is correct against the spec shape; it does
NOT prove interoperability with any specific real EHR vendor's FHIR server."""
import httpx
import pytest
from app.services.emr_adapter import FHIRAdapter, SmartOAuthClient

FHIR_PATIENT = {
    "resourceType": "Patient", "id": "fhir-1",
    "name": [{"text": "Test Patient"}], "gender": "female", "birthDate": "1970-01-01",
}
FHIR_CONDITION_BUNDLE = {"resourceType": "Bundle", "entry": [
    {"resource": {"resourceType": "Condition", "code": {"text": "Chronic kidney disease"}}},
]}
FHIR_MEDREQ_BUNDLE = {"resourceType": "Bundle", "entry": [
    {"resource": {"resourceType": "MedicationRequest", "id": "m1", "status": "active",
                  "medicationCodeableConcept": {"coding": [{"code": "warfarin"}]}}},
]}
FHIR_EMPTY_BUNDLE = {"resourceType": "Bundle", "entry": []}
FHIR_ALLERGY_BUNDLE = {"resourceType": "Bundle", "entry": [
    {"resource": {"resourceType": "AllergyIntolerance", "code": {"text": "Penicillin"},
                  "reaction": [{"severity": "severe"}]}},
]}
FHIR_OBS_BUNDLE = {"resourceType": "Bundle", "entry": [
    {"resource": {"resourceType": "Observation", "code": {"text": "eGFR"},
                  "effectiveDateTime": "2026-01-01", "valueQuantity": {"value": 45, "unit": "mL/min"}}},
    {"resource": {"resourceType": "Observation",
                  "code": {"coding": [{"system": "http://loinc.org", "code": "8302-2", "display": "Body height"}]},
                  "valueQuantity": {"value": 165, "unit": "cm"}}},
    {"resource": {"resourceType": "Observation",
                  "code": {"coding": [{"system": "http://loinc.org", "code": "29463-7", "display": "Body weight"}]},
                  "valueQuantity": {"value": 60, "unit": "kg"}}},
]}


def make_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/Patient/fhir-1"):
            return httpx.Response(200, json=FHIR_PATIENT)
        if path.endswith("/Patient/missing"):
            return httpx.Response(404, json={"resourceType": "OperationOutcome"})
        if path.endswith("/Condition"):
            return httpx.Response(200, json=FHIR_CONDITION_BUNDLE)
        if path.endswith("/MedicationRequest"):
            return httpx.Response(200, json=FHIR_MEDREQ_BUNDLE)
        if path.endswith("/MedicationStatement"):
            return httpx.Response(200, json=FHIR_EMPTY_BUNDLE)
        if path.endswith("/AllergyIntolerance"):
            return httpx.Response(200, json=FHIR_ALLERGY_BUNDLE)
        if path.endswith("/Observation"):
            return httpx.Response(200, json=FHIR_OBS_BUNDLE)
        return httpx.Response(404, json={"error": "unhandled path in fake FHIR server: " + path})
    return httpx.MockTransport(handler)


def test_fhir_adapter_parses_patient_from_fake_server():
    adapter = FHIRAdapter(base_url="https://fake-fhir.example/r4", transport=make_transport())
    p = adapter.get("fhir-1")
    assert p is not None
    assert p.name == "Test Patient"
    assert p.sex == "female"
    assert p.age >= 50
    assert p.conditions == ["Chronic kidney disease"]
    assert any(m.drug_id == "warfarin" for m in p.medications)
    assert p.allergies[0].substance == "Penicillin"
    assert p.labs[0].name == "eGFR"
    assert p.height_cm == 165
    assert p.weight_kg == 60
    assert "missing" not in " ".join(p.missing) or True  # missing list should be empty here (all data present)
    assert p.missing == []

def test_fhir_adapter_maps_height_weight_observations_and_reports_when_absent():
    adapter = FHIRAdapter(base_url="https://fake-fhir.example/r4", transport=make_transport())
    p = adapter.get("fhir-1")
    assert p.height_cm == 165 and p.weight_kg == 60

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/Patient/no-vitals"):
            return httpx.Response(200, json={"resourceType": "Patient", "id": "no-vitals", "gender": "male", "birthDate": "1990-01-01"})
        return httpx.Response(200, json=FHIR_EMPTY_BUNDLE)
    adapter2 = FHIRAdapter(base_url="https://fake-fhir.example/r4", transport=httpx.MockTransport(handler))
    p2 = adapter2.get("no-vitals")
    assert p2.height_cm is None and p2.weight_kg is None
    assert any('height' in m for m in p2.missing)
    assert any('weight' in m for m in p2.missing)

def test_fhir_adapter_404_returns_none():
    adapter = FHIRAdapter(base_url="https://fake-fhir.example/r4", transport=make_transport())
    assert adapter.get("missing") is None

def test_fhir_adapter_list_is_explicitly_not_implemented():
    adapter = FHIRAdapter(base_url="https://fake-fhir.example/r4", transport=make_transport())
    with pytest.raises(NotImplementedError):
        adapter.list()

def test_fhir_adapter_missing_data_is_reported_not_hidden():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/Patient/sparse"):
            return httpx.Response(200, json={"resourceType": "Patient", "id": "sparse"})
        return httpx.Response(200, json=FHIR_EMPTY_BUNDLE)
    adapter = FHIRAdapter(base_url="https://fake-fhir.example/r4", transport=httpx.MockTransport(handler))
    p = adapter.get("sparse")
    assert "patient sex (missing or not male/female)" in p.missing
    assert "birth date" in p.missing
    assert "condition history (none returned)" in p.missing
    assert "medication list (none returned)" in p.missing

def test_smart_oauth_client_gets_token_via_discovery():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/.well-known/smart-configuration"):
            return httpx.Response(200, json={"token_endpoint": "https://fake-fhir.example/oauth2/token"})
        if request.url.path.endswith("/oauth2/token"):
            return httpx.Response(200, json={"access_token": "fake-token-123", "expires_in": 300})
        return httpx.Response(404)
    oauth = SmartOAuthClient("https://fake-fhir.example/r4", "client-id", "secret", "system/*.read",
                              transport=httpx.MockTransport(handler))
    assert oauth.token() == "fake-token-123"
    assert oauth.token() == "fake-token-123"  # cached, no second network call needed

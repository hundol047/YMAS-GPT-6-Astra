import json
from types import SimpleNamespace

import httpx
import pytest

from app.services.emr_adapter import DemoAdapter
from app.services.gpt_summary import AISummaryUnavailable, summarize_demo
from app.services.rule_engine import DRUGS


def test_demo_summary_sends_minimal_record_and_parses_structured_result():
    patient = DemoAdapter().get("SYN-002")
    notes = [SimpleNamespace(
        subjective="항응고요법 지속 중.",
        objective="최근 INR 상승 추세 확인.",
        assessment="출혈 위험 관련 재평가 필요.",
        plan="INR 재검사 및 추적 관찰.",
    )]
    captured = {}

    def respond(request):
        captured["body"] = json.loads(request.content)
        captured["auth"] = request.headers["Authorization"]
        return httpx.Response(200, json={
            "output": [{"type": "message", "content": [
                {"type": "output_text", "text": json.dumps(
                    {"summary": "항응고요법 중 INR 상승 추세가 기록되었습니다."},
                    ensure_ascii=False,
                )}
            ]}]
        })

    summary = summarize_demo(
        patient, notes, {"alerts": [], "missing": []}, DRUGS,
        api_key="test-key", model="test-model", transport=httpx.MockTransport(respond),
    )
    assert "INR 상승" in summary
    assert captured["auth"] == "Bearer test-key"
    assert captured["body"]["store"] is False
    snapshot = json.loads(captured["body"]["input"])
    assert "INR 상승 추세" in snapshot["soap_notes"][0]["objective"]
    assert "name" not in snapshot
    assert "mrn" not in snapshot
    assert "phone" not in snapshot


def test_demo_summary_requires_key_and_rejects_invalid_output():
    patient = DemoAdapter().get("SYN-001")
    with pytest.raises(AISummaryUnavailable):
        summarize_demo(patient, [], {"alerts": [], "missing": []}, DRUGS, api_key="")

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"output": []}))
    with pytest.raises(AISummaryUnavailable):
        summarize_demo(
            patient, [], {"alerts": [], "missing": []}, DRUGS,
            api_key="test-key", transport=transport,
        )


def test_agent_analyze_enriches_existing_summary_without_changing_alerts(client, monkeypatch):
    from app import main

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured = {}

    def fake_summary(patient, notes, analysis, catalog):
        captured["notes"] = notes
        return "SOAP 기록과 기존 경고를 요약했습니다."

    monkeypatch.setattr(main, "summarize_demo", fake_summary)
    response = client.post("/agent/analyze", json={"patient_id": "SYN-002"})
    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == "의료 AI 요약 · SOAP 기록과 기존 경고를 요약했습니다."
    assert body["agent_mode"] == "openai_demo_summary"
    assert body["ai_summary_status"] == "available"
    assert captured["notes"]
    assert any(alert["type"] == "drug_interaction" for alert in body["alerts"])


def test_agent_analyze_preserves_rule_results_when_api_unavailable(client, monkeypatch):
    from app import main

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    def unavailable(*args):
        raise AISummaryUnavailable("upstream failure")
    monkeypatch.setattr(main, "summarize_demo", unavailable)
    response = client.post("/agent/analyze", json={"patient_id": "SYN-002"})
    assert response.status_code == 200
    body = response.json()
    assert body["ai_summary_status"] == "unavailable"
    assert body["summary"].startswith("의료 AI 연결 실패 · ")
    assert any(alert["type"] == "drug_interaction" for alert in body["alerts"])

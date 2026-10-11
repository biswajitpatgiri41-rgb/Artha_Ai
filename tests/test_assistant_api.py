from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.main import app
from app.api import routes


client = TestClient(app)


def test_assistant_forwards_safe_context_and_returns_model(monkeypatch):
    captured = {}

    mock_settings = SimpleNamespace(
        nvidia_model="test-model",
        is_llm_configured=lambda: True
    )
    monkeypatch.setattr(routes, "get_settings", lambda: mock_settings)

    async def fake_request_model_async(**kwargs):
        captured.update(kwargs)
        return "Oil can affect inflation through fuel, transport, and input-cost channels."

    monkeypatch.setattr(routes, "request_model_async", fake_request_model_async)
    response = client.post("/assistant/chat", json={
        "message": "If oil rises 20%, what channels might affect inflation?",
        "page": "/simulator",
        "page_context": "Scenario Simulator",
        "page_data": {"page": "/simulator", "mode": "mock", "visibleMetrics": [], "selectedScenario": {"oilShock": 20}, "selectedSeries": None, "warnings": []},
        "conversation": [],
    })

    assert response.status_code == 200
    assert response.json()["model"] == "test-model"
    assert captured["messages"][0]["role"] == "system"
    assert "oilShock" in captured["messages"][1]["content"]


def test_unavailable_nvidia_returns_503(monkeypatch):
    mock_settings = SimpleNamespace(
        nvidia_model="test-model",
        is_llm_configured=lambda: True
    )
    monkeypatch.setattr(routes, "get_settings", lambda: mock_settings)
    monkeypatch.setattr(routes, "request_model_async", lambda **_: (_ for _ in ()).throw(RuntimeError("LLM request failed")))

    response = client.post("/assistant/chat", json={"message": "Explain CPI", "page": "/analysis", "page_context": "Inflation Analysis"})

    assert response.status_code == 502
    assert "unavailable" in response.json()["detail"].lower()


def test_malformed_request_is_rejected():
    response = client.post("/assistant/chat", json={"page": "/analysis"})

    assert response.status_code == 422

import pytest
from fastapi.testclient import TestClient

import apps.api.rate_limit as rate_limit_module
from apps.api.deps import get_db, get_llm_client
from apps.api.main import app


class FakeLLMClient:
    def generate_sentence(self, reasons_payload):
        return "Your request was approved. None of the rules we checked blocked it."


class _OneRequestPerMinute:
    rate_limit_per_minute = 1


def test_create_decision_is_rate_limited(db, monkeypatch):
    monkeypatch.setattr(rate_limit_module, "get_settings", lambda: _OneRequestPerMinute())
    rate_limit_module.limiter.reset()

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient()
    try:
        client = TestClient(app)
        client.headers.update({"X-API-Key": "dev-local-key"})

        payload = {"domain": "returns", "category": "general", "features": {"days_since_delivery": 1}}
        first = client.post("/v1/decisions", json=payload)
        assert first.status_code == 201

        second = client.post("/v1/decisions", json=payload)
        assert second.status_code == 429
    finally:
        app.dependency_overrides.clear()
        rate_limit_module.limiter.reset()

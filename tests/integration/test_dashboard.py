import base64

import pytest
from fastapi.testclient import TestClient

from apps.api.deps import get_db, get_llm_client
from apps.api.main import app


class FakeLLMClient:
    def generate_sentence(self, reasons_payload):
        return (
            "Your return was not approved for two separate reasons: it was submitted nine days after delivery, "
            "two days past our seven-day return window, and separately, the photo provided did not clearly show "
            "the manufacturing defect claimed, which our policy requires for the extended defect exception. "
            "Either reason alone would have led to the same result."
        )


class VagueLLMClient:
    def generate_sentence(self, reasons_payload):
        return "Your return was denied because it was just under the required threshold."


def _basic_auth_header(username="ops", password="change-me"):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@pytest.fixture
def client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient()
    try:
        test_client = TestClient(app)
        test_client.headers.update({"X-API-Key": "dev-local-key", **_basic_auth_header()})
        yield test_client
    finally:
        app.dependency_overrides.clear()


def test_dashboard_requires_login(client):
    client.headers.pop("Authorization")
    response = client.get("/dashboard/review-queue")
    assert response.status_code == 401


def test_wrong_dashboard_password_rejected(client):
    client.headers.update(_basic_auth_header(password="wrong"))
    response = client.get("/dashboard/review-queue")
    assert response.status_code == 401


def test_review_queue_page_renders(client):
    response = client.get("/dashboard/review-queue")
    assert response.status_code == 200
    assert "Review Queue" in response.text


def test_decision_detail_page_shows_reema_case(client):
    created = client.post(
        "/v1/decisions",
        json={
            "domain": "returns",
            "category": "defect_claim",
            "features": {"days_since_delivery": 9, "defect_confidence": 0.61},
        },
    )
    decision_id = created.json()["id"]

    response = client.get(f"/dashboard/decisions/{decision_id}")
    assert response.status_code == 200
    assert "nine days" in response.text
    assert "WINDOW-STANDARD-01" in response.text


def test_full_review_and_disclose_flow_via_dashboard_forms(client):
    app.dependency_overrides[get_llm_client] = lambda: VagueLLMClient()
    created = client.post(
        "/v1/decisions",
        json={
            "domain": "returns",
            "category": "defect_claim",
            "features": {"days_since_delivery": 9, "defect_confidence": 0.61},
        },
    )
    decision_id = created.json()["id"]

    queue_page = client.get("/dashboard/review-queue")
    assert decision_id in queue_page.text

    detail = client.get(f"/dashboard/decisions/{decision_id}")
    assert "Pending review" in detail.text

    # Blocked: disclosing without a reviewed sentence, since justification failed.
    blocked = client.post(
        f"/dashboard/decisions/{decision_id}/disclose",
        data={"channel": "call", "disclosed_by": "uttara"},
        follow_redirects=False,
    )
    assert blocked.status_code == 303
    assert "error=" in blocked.headers["location"]

    disclosed = client.post(
        f"/dashboard/decisions/{decision_id}/disclose",
        data={
            "channel": "call",
            "disclosed_by": "uttara",
            "sentence_override": "Hand-reviewed sentence.",
        },
        follow_redirects=False,
    )
    assert disclosed.status_code == 303
    assert "message=" in disclosed.headers["location"]

    ledger = client.get("/dashboard/disclosures")
    assert decision_id in ledger.text


def test_reopen_via_dashboard_form(client):
    created = client.post(
        "/v1/decisions",
        json={
            "domain": "returns",
            "category": "defect_claim",
            "features": {"days_since_delivery": 9, "defect_confidence": 0.61},
        },
    )
    decision_id = created.json()["id"]

    response = client.post(
        f"/dashboard/decisions/{decision_id}/reopen",
        data={"new_evidence_json": '{"defect_confidence": 0.89}'},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/dashboard/decisions/" in response.headers["location"]
    assert decision_id not in response.headers["location"]  # a *new* decision id

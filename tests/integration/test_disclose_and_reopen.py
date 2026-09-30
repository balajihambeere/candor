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


@pytest.fixture
def client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient()
    try:
        test_client = TestClient(app)
        test_client.headers.update({"X-API-Key": "dev-local-key"})
        yield test_client
    finally:
        app.dependency_overrides.clear()


def _create_reema_decision(client):
    response = client.post(
        "/v1/decisions",
        json={
            "domain": "returns",
            "category": "defect_claim",
            "features": {"days_since_delivery": 9, "defect_confidence": 0.61},
        },
    )
    return response.json()


def test_uttaras_call_to_reema_is_recorded_in_the_ledger(client):
    # Uttara calls, reads the sentence unedited, owns the month-long delay.
    decision = _create_reema_decision(client)

    response = client.post(
        f"/v1/decisions/{decision['id']}/disclose",
        json={
            "channel": "call",
            "disclosed_by": "uttara",
            "delay_owned": True,
            "customer_response": "That's it? That's the actual reason? Both of those?",
            "held_up": True,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["channel"] == "call"
    assert "nine days" in body["sentence_sent"]
    assert "policy team to review" in body["sentence_sent"]
    assert body["held_up"] is True

    ledger = client.get(f"/v1/decisions/{decision['id']}/disclosures").json()
    assert len(ledger) == 1
    assert ledger[0]["disclosed_by"] == "uttara"


def test_cannot_disclose_an_unverified_justification_without_a_reviewed_sentence(client):
    app.dependency_overrides[get_llm_client] = lambda: VagueLLMClient()
    decision = _create_reema_decision(client)
    assert decision["needs_review"] is True

    blocked = client.post(
        f"/v1/decisions/{decision['id']}/disclose",
        json={"channel": "email", "disclosed_by": "support-bot"},
    )
    assert blocked.status_code == 409

    allowed = client.post(
        f"/v1/decisions/{decision['id']}/disclose",
        json={
            "channel": "call",
            "disclosed_by": "uttara",
            "sentence_override": "Hand-reviewed sentence written after the review queue caught the bad one.",
        },
    )
    assert allowed.status_code == 201


def test_invalid_channel_is_rejected(client):
    decision = _create_reema_decision(client)
    response = client.post(
        f"/v1/decisions/{decision['id']}/disclose",
        json={"channel": "carrier-pigeon", "disclosed_by": "uttara"},
    )
    assert response.status_code == 422


def test_reopen_with_sharper_photo_still_denied_by_window_alone(client):
    # Reema's actual follow-up question — her sharper photo, submitted
    # after the fact, still wouldn't have been enough on its own because
    # the window failure doesn't depend on the photo.
    decision = _create_reema_decision(client)

    response = client.post(
        f"/v1/decisions/{decision['id']}/reopen",
        json={"new_evidence": {"defect_confidence": 0.89}},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["original_decision_id"] == decision["id"]
    new_decision = body["new_decision"]
    assert new_decision["verdict"] == "denied"
    assert new_decision["trace"]["determinative_reasons"] == ["WINDOW-STANDARD-01"]
    assert new_decision["id"] != decision["id"]


def test_reopen_with_both_corrections_flips_to_approved(client):
    decision = _create_reema_decision(client)

    response = client.post(
        f"/v1/decisions/{decision['id']}/reopen",
        json={"new_evidence": {"days_since_delivery": 6, "defect_confidence": 0.89}},
    )
    assert response.status_code == 201
    assert response.json()["new_decision"]["verdict"] == "approved"


def test_reopen_on_missing_decision_returns_404(client):
    response = client.post(
        "/v1/decisions/00000000-0000-0000-0000-000000000000/reopen",
        json={"new_evidence": {}},
    )
    assert response.status_code == 404


def test_global_disclosure_ledger_lists_across_decisions(client):
    decision = _create_reema_decision(client)
    client.post(
        f"/v1/decisions/{decision['id']}/disclose",
        json={"channel": "call", "disclosed_by": "uttara", "delay_owned": True},
    )

    ledger = client.get("/v1/disclosures")
    assert ledger.status_code == 200
    matching = [d for d in ledger.json() if d["decision_id"] == decision["id"]]
    assert len(matching) == 1
    assert matching[0]["disclosed_by"] == "uttara"

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


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_create_decision_without_api_key_is_rejected(client):
    client.headers.pop("X-API-Key")
    response = client.post(
        "/v1/decisions",
        json={"domain": "returns", "category": "general", "features": {"days_since_delivery": 1}},
    )
    assert response.status_code == 401


def test_create_decision_with_wrong_api_key_is_rejected(client):
    client.headers.update({"X-API-Key": "not-the-right-key"})
    response = client.post(
        "/v1/decisions",
        json={"domain": "returns", "category": "general", "features": {"days_since_delivery": 1}},
    )
    assert response.status_code == 401


def test_read_endpoints_do_not_require_an_api_key(client):
    client.headers.update({"X-API-Key": "dev-local-key"})
    created = client.post(
        "/v1/decisions",
        json={"domain": "returns", "category": "general", "features": {"days_since_delivery": 1}},
    )
    decision_id = created.json()["id"]

    client.headers.pop("X-API-Key")
    response = client.get(f"/v1/decisions/{decision_id}")
    assert response.status_code == 200


def test_create_and_read_reema_decision(client):
    response = client.post(
        "/v1/decisions",
        json={
            "domain": "returns",
            "category": "defect_claim",
            "features": {"days_since_delivery": 9, "defect_confidence": 0.61},
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["verdict"] == "denied"
    assert set(body["trace"]["determinative_reasons"]) == {"WINDOW-STANDARD-01", "DEFECT-EXCEPTION-02"}
    assert body["justification"]["status"] == "verified"
    assert "nine days" in body["justification"]["sentence"]
    assert body["needs_review"] is False

    decision_id = body["id"]
    read_back = client.get(f"/v1/decisions/{decision_id}")
    assert read_back.status_code == 200
    assert read_back.json()["id"] == decision_id


def test_missing_decision_returns_404(client):
    response = client.get("/v1/decisions/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_unknown_domain_returns_422(client):
    response = client.post(
        "/v1/decisions",
        json={"domain": "not-a-real-domain", "category": "general", "features": {}},
    )
    assert response.status_code == 422


def test_wrong_typed_feature_value_returns_422_not_500(client):
    # days_since_delivery as a string can't be compared against an int
    # threshold — must fail cleanly, not with an unhandled TypeError.
    response = client.post(
        "/v1/decisions",
        json={"domain": "returns", "category": "general", "features": {"days_since_delivery": "nine"}},
    )
    assert response.status_code == 422


def test_missing_category_rule_feature_returns_422(client):
    response = client.post(
        "/v1/decisions",
        json={"domain": "returns", "category": "defect_claim", "features": {"days_since_delivery": 9}},
    )
    assert response.status_code == 422


def test_reemas_own_counterfactual_question(client):
    # "if I'd sent that one first, on day six instead of day nine, would
    # you have approved it?" -> No, the window failure doesn't depend on
    # the photo.
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
        f"/v1/decisions/{decision_id}/counterfactual",
        json={"feature_overrides": {"defect_confidence": 0.89}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["counterfactual_verdict"] == "denied"
    assert body["would_flip"] is False

    # Fixing only the date still isn't enough — the defect exception's own
    # confidence check (0.61 against 0.75) independently still fails
    # ("the defect exception failed on its own regardless of the date").
    response = client.post(
        f"/v1/decisions/{decision_id}/counterfactual",
        json={"feature_overrides": {"days_since_delivery": 7}},
    )
    body = response.json()
    assert body["counterfactual_verdict"] == "denied"
    assert body["would_flip"] is False

    # Both facts have to be fixed at once for the verdict to flip.
    response = client.post(
        f"/v1/decisions/{decision_id}/counterfactual",
        json={"feature_overrides": {"days_since_delivery": 7, "defect_confidence": 0.9}},
    )
    body = response.json()
    assert body["counterfactual_verdict"] == "approved"
    assert body["would_flip"] is True


def test_failed_review_case_appears_in_review_queue_and_resolves(client):
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
    assert created.json()["needs_review"] is True

    queue = client.get("/v1/review-queue").json()
    matching = [item for item in queue if item["decision_id"] == decision_id]
    assert len(matching) == 1
    item_id = matching[0]["id"]
    assert matching[0]["reason"] == "justify_faithfulness_failed"

    resolved = client.post(
        f"/v1/review-queue/{item_id}/resolve",
        json={"assigned_to": "uttara", "resolution_notes": "rewrote by hand"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    again = client.post(
        f"/v1/review-queue/{item_id}/resolve",
        json={"assigned_to": "uttara", "resolution_notes": "already done"},
    )
    assert again.status_code == 409

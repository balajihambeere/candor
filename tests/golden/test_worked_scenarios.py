"""End-to-end reproductions of three worked cases — Reema, Kochi, Indore —
driven entirely through the live HTTP API, using their own shipped dialogue
as the oracle for what a correct run must produce. This is concrete
alignment evidence: not a claim that the pipeline matches the reference
scenarios, but a test that reproduces their exact numbers and sentences and
fails if a future change breaks the match.

The LLM is mocked (scripted by rule topic) so these tests are deterministic,
free, and don't require network access — the same tradeoff the pipeline
itself makes with Decide/Trace being deterministic and only Justify
touching a model at all.
"""

import pytest
from fastapi.testclient import TestClient

from apps.api.deps import get_db, get_llm_client
from apps.api.main import app

REEMA_SENTENCE = (
    "Your return was not approved for two separate reasons: it was submitted nine days after delivery, "
    "two days past our seven-day return window, and separately, the photo provided did not clearly show "
    "the manufacturing defect claimed, which our policy requires for the extended defect exception. "
    "Either reason alone would have led to the same result."
)

KOCHI_SENTENCE = (
    "Your return was not approved because the item showed visible signs of outdoor wear, "
    "which our footwear policy does not cover."
)

INDORE_SENTENCE = (
    "Your return was not approved because this item was purchased under our Final Sale promotion, "
    "which is marked non-returnable in the terms shown at checkout. This category is excluded from "
    "our standard return policy regardless of the reason for return."
)

# Reema's reopened case with only her sharper photo as new evidence — the
# defect exception now clears, but the window failure alone still denies
# it, independent of the photo.
REEMA_WINDOW_ONLY_SENTENCE = (
    "Your return was not approved because it was submitted nine days after delivery, "
    "two days past our seven-day return window."
)


class ScriptedLLMClient:
    """Picks the actual shipped sentence based on which rules are in play,
    the same way a real model would given the same structured record.
    """

    def generate_sentence(self, reasons_payload: list[dict]) -> str:
        descriptions = " ".join(r["description"] for r in reasons_payload)
        if "outdoor wear" in descriptions:
            return KOCHI_SENTENCE
        if "Final Sale" in descriptions:
            return INDORE_SENTENCE
        if "return window" in descriptions and "manufacturing defect" in descriptions:
            return REEMA_SENTENCE
        if "return window" in descriptions:
            return REEMA_WINDOW_ONLY_SENTENCE
        raise AssertionError(f"no scripted sentence for: {descriptions}")


@pytest.fixture
def client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_llm_client] = lambda: ScriptedLLMClient()
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
    assert response.status_code == 201, response.text
    return response.json()


class TestReemaCase:
    """Rs 2,499 cotton kurta, denied for a torn seam claim: filed day 9
    (missed the 7-day window) with a blurry defect photo (0.61 confidence
    against a 0.75 threshold). Both reasons are independently sufficient;
    the two-reason sentence ships; Uttara calls and discloses it, and Reema
    asks whether her later, sharper photo would have changed anything.
    """

    def test_decide_captures_both_reasons(self, client):
        body = _create_reema_decision(client)
        assert body["verdict"] == "denied"

        by_id = {r["rule_id"]: r for r in body["reasons"]}
        assert by_id["WINDOW-STANDARD-01"] == {
            "rule_id": "WINDOW-STANDARD-01", "evaluated_value": 9, "threshold": 7,
            "comparator": "<=", "passed": False,
        }
        assert by_id["DEFECT-EXCEPTION-02"] == {
            "rule_id": "DEFECT-EXCEPTION-02", "evaluated_value": 0.61, "threshold": 0.75,
            "comparator": ">=", "passed": False,
        }

    def test_trace_confirms_both_independently_sufficient(self, client):
        body = _create_reema_decision(client)
        assert body["trace"]["verification_status"] == "verified"
        assert set(body["trace"]["determinative_reasons"]) == {"WINDOW-STANDARD-01", "DEFECT-EXCEPTION-02"}

    def test_justify_ships_the_two_reason_sentence(self, client):
        body = _create_reema_decision(client)
        assert body["justification"]["status"] == "verified"
        assert body["justification"]["sentence"] == REEMA_SENTENCE
        assert "policy team to review" in body["justification"]["boundary_line"]
        assert body["needs_review"] is False

    def test_uttaras_disclosure_call(self, client):
        body = _create_reema_decision(client)
        response = client.post(
            f"/v1/decisions/{body['id']}/disclose",
            json={
                "channel": "call",
                "disclosed_by": "uttara",
                "delay_owned": True,
                "customer_response": "That's it? That's the actual reason? Both of those?",
                "held_up": True,
            },
        )
        assert response.status_code == 201
        assert "nine days" in response.json()["sentence_sent"]

    def test_reemas_sharper_photo_still_denied_by_window_alone(self, client):
        # "No. Not with the late date. The window failure doesn't depend on
        # the photo at all." — Uttara.
        body = _create_reema_decision(client)
        response = client.post(
            f"/v1/decisions/{body['id']}/reopen",
            json={"new_evidence": {"defect_confidence": 0.89}},
        )
        assert response.status_code == 201
        new_decision = response.json()["new_decision"]
        assert new_decision["verdict"] == "denied"
        assert new_decision["trace"]["determinative_reasons"] == ["WINDOW-STANDARD-01"]


class TestKochiCase:
    """Worn sandals: window passes (day 6), footwear-wear classifier fails
    (0.94 confidence against a 0.40 threshold) — a single-cause denial,
    the case that first proves Justify out on a real deadline.
    """

    def test_full_pipeline_matches_the_reference_table(self, client):
        response = client.post(
            "/v1/decisions",
            json={
                "domain": "returns",
                "category": "footwear",
                "features": {"days_since_delivery": 6, "wear_confidence": 0.94},
            },
        )
        assert response.status_code == 201
        body = response.json()

        by_id = {r["rule_id"]: r for r in body["reasons"]}
        assert by_id["WINDOW-STANDARD-01"]["passed"] is True
        assert by_id["FOOTWEAR-EXCEPTION-03"] == {
            "rule_id": "FOOTWEAR-EXCEPTION-03", "evaluated_value": 0.94, "threshold": 0.40,
            "comparator": "<=", "passed": False,
        }
        assert body["trace"]["determinative_reasons"] == ["FOOTWEAR-EXCEPTION-03"]
        assert body["justification"]["sentence"] == KOCHI_SENTENCE


class TestIndoreCase:
    """Final Sale silk saree, a verified and faithful denial that is still
    incomplete on its own — the case that introduces False Clarity and the
    fixed boundary line separating "this decision" from "the policy itself."
    """

    def test_final_sale_denial_carries_the_boundary_line(self, client):
        response = client.post(
            "/v1/decisions",
            json={
                "domain": "returns",
                "category": "final_sale",
                "features": {"days_since_delivery": 3, "is_final_sale": True},
            },
        )
        assert response.status_code == 201
        body = response.json()

        assert body["justification"]["sentence"] == INDORE_SENTENCE
        assert body["justification"]["status"] == "verified"
        boundary = body["justification"]["boundary_line"]
        assert "complete and verified" in boundary
        assert "logged it for our policy team to review" in boundary

    def test_disclosure_records_her_actual_reply_and_still_held_up(self, client):
        # "I'm not asking you to explain the policy to me again... What I'm
        # asking is why nobody made it clear enough..." — her real objection
        # was adjacent to the decision, not a dispute of it; the decision
        # explanation itself held up.
        created = client.post(
            "/v1/decisions",
            json={
                "domain": "returns",
                "category": "final_sale",
                "features": {"days_since_delivery": 3, "is_final_sale": True},
            },
        )
        decision_id = created.json()["id"]

        response = client.post(
            f"/v1/decisions/{decision_id}/disclose",
            json={
                "channel": "email",
                "disclosed_by": "support-team",
                "customer_response": (
                    "I'm not asking you to explain the policy to me again. I read it. I understand it now."
                ),
                "held_up": True,
            },
        )
        assert response.status_code == 201
        assert "policy team to review" in response.json()["sentence_sent"]

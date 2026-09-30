from database.models import ReviewReason, ReviewStatus, VerificationStatus as ORMVerificationStatus
from database.repository import (
    create_case,
    get_review_item,
    list_review_queue,
    persist_pipeline_result,
    resolve_review_item,
)
from domains.registry import get_domain
from packages.candor.pipeline import run_pipeline


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


def test_verified_decision_persists_without_a_review_item(db):
    domain = get_domain("returns")
    result = run_pipeline(
        domain, "defect_claim", {"days_since_delivery": 9, "defect_confidence": 0.61}, FakeLLMClient()
    )

    case = create_case(db, "returns", "defect_claim", {"days_since_delivery": 9, "defect_confidence": 0.61})
    decision = persist_pipeline_result(db, case, result)

    assert decision.verdict == "denied"
    assert decision.trace_result.verification_status == ORMVerificationStatus.VERIFIED
    assert decision.justification.status.value == "verified"
    assert list_review_queue(db, ReviewStatus.PENDING) == [] or all(
        item.decision_id != decision.id for item in list_review_queue(db, ReviewStatus.PENDING)
    )


def test_failed_faithfulness_routes_to_review_queue_not_disclosure(db):
    domain = get_domain("returns")
    result = run_pipeline(
        domain, "defect_claim", {"days_since_delivery": 9, "defect_confidence": 0.61}, VagueLLMClient()
    )

    case = create_case(db, "returns", "defect_claim", {"days_since_delivery": 9, "defect_confidence": 0.61})
    decision = persist_pipeline_result(db, case, result)

    pending = list_review_queue(db, ReviewStatus.PENDING)
    matching = [item for item in pending if item.decision_id == decision.id]
    assert len(matching) == 1
    assert matching[0].reason == ReviewReason.JUSTIFY_FAITHFULNESS_FAILED


def test_resolving_a_review_item_marks_it_resolved(db):
    domain = get_domain("returns")
    result = run_pipeline(
        domain, "defect_claim", {"days_since_delivery": 9, "defect_confidence": 0.61}, VagueLLMClient()
    )
    case = create_case(db, "returns", "defect_claim", {"days_since_delivery": 9, "defect_confidence": 0.61})
    decision = persist_pipeline_result(db, case, result)

    item = [i for i in list_review_queue(db, ReviewStatus.PENDING) if i.decision_id == decision.id][0]
    resolve_review_item(db, item, assigned_to="uttara", resolution_notes="rewrote sentence by hand")

    refreshed = get_review_item(db, item.id)
    assert refreshed.status == ReviewStatus.RESOLVED
    assert refreshed.assigned_to == "uttara"
    assert refreshed.resolved_at is not None

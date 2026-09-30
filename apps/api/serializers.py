from database.models import Decision
from packages.candor.models import JustificationStatus as PyJustificationStatus


def decision_to_response_dict(decision: Decision) -> dict:
    trace_result = decision.trace_result
    justification = decision.justification
    needs_review = any(
        item.status.value == "pending" for item in decision.review_items
    )
    return {
        "id": decision.id,
        "case_id": decision.case_id,
        "verdict": decision.verdict,
        "reasons": decision.reasons,
        "trace": {
            "determinative_reasons": trace_result.determinative_reasons,
            "verification_status": trace_result.verification_status.value,
            "counterfactual_log": trace_result.counterfactual_log,
        },
        "justification": {
            "sentence": justification.sentence,
            "boundary_line": justification.boundary_line,
            "faithfulness_check_passed": justification.faithfulness_check_passed,
            "plain_language_check_passed": justification.plain_language_check_passed,
            "status": justification.status.value,
        },
        "needs_review": needs_review or justification.status == PyJustificationStatus.FAILED_REVIEW.value,
        "created_at": decision.created_at,
    }

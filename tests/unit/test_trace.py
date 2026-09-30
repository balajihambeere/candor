"""Reproduces Reema's trace ("both facts were independently sufficient")
and Kochi's trace ("Determinative rule: FOOTWEAR-EXCEPTION-03") as
counterfactual-replay assertions, not narrative.
"""

from domains.returns.catalog import evaluate_case, passing_patch
from packages.candor.decide import decide
from packages.candor.models import VerificationStatus
from packages.candor.trace import trace


def test_reema_case_both_reasons_independently_sufficient():
    features = {"days_since_delivery": 9, "defect_confidence": 0.61}
    decision = decide("defect_claim", features, evaluate_case)

    outcome = trace("defect_claim", features, decision, evaluate_case, passing_patch)

    assert outcome.verification_status is VerificationStatus.VERIFIED
    assert set(outcome.determinative_reasons) == {"WINDOW-STANDARD-01", "DEFECT-EXCEPTION-02"}
    assert len(outcome.counterfactual_log) == 2
    assert all(check.still_denied for check in outcome.counterfactual_log)


def test_reema_sharper_photo_still_denied_by_window_alone():
    # Uttara confirms the sharp photo on day 9 still wouldn't have been
    # approved, because the window failure doesn't depend on the photo.
    features = {"days_since_delivery": 9, "defect_confidence": 0.89}
    decision = decide("defect_claim", features, evaluate_case)

    assert decision.verdict.value == "denied"
    outcome = trace("defect_claim", features, decision, evaluate_case, passing_patch)
    assert outcome.determinative_reasons == ["WINDOW-STANDARD-01"]


def test_kochi_case_single_determinative_reason():
    features = {"days_since_delivery": 6, "wear_confidence": 0.94}
    decision = decide("footwear", features, evaluate_case)

    outcome = trace("footwear", features, decision, evaluate_case, passing_patch)

    assert outcome.verification_status is VerificationStatus.VERIFIED
    assert outcome.determinative_reasons == ["FOOTWEAR-EXCEPTION-03"]
    assert len(outcome.counterfactual_log) == 1


def test_approved_case_trivially_verified_with_no_determinative_reasons():
    features = {"days_since_delivery": 2, "defect_confidence": 0.95}
    decision = decide("defect_claim", features, evaluate_case)

    outcome = trace("defect_claim", features, decision, evaluate_case, passing_patch)

    assert outcome.verification_status is VerificationStatus.VERIFIED
    assert outcome.determinative_reasons == []
    assert outcome.counterfactual_log == []


def test_indore_final_sale_determinative_alone():
    features = {"days_since_delivery": 3, "is_final_sale": True}
    decision = decide("final_sale", features, evaluate_case)

    outcome = trace("final_sale", features, decision, evaluate_case, passing_patch)

    assert outcome.determinative_reasons == ["FINAL-SALE-EXCLUSION"]


def test_unresolvable_rule_routes_to_unresolved_not_a_guess():
    def unknown_patch(rule_id, features):
        return None

    features = {"days_since_delivery": 9, "defect_confidence": 0.61}
    decision = decide("defect_claim", features, evaluate_case)

    outcome = trace("defect_claim", features, decision, evaluate_case, unknown_patch)

    assert outcome.verification_status is VerificationStatus.UNRESOLVED

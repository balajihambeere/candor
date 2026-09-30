"""Reproduces a known bug catalog as regression cases the checkers must
catch, and the actual shipped sentences (Reema, Kochi, Indore) as cases that
must pass cleanly.
"""

from domains.returns.catalog import JUSTIFY_METADATA, evaluate_case, passing_patch
from packages.candor.decide import decide
from packages.candor.justify import justify
from packages.candor.models import JustificationStatus
from packages.candor.trace import trace


class FakeLLMClient:
    def __init__(self, canned_sentence: str):
        self.canned_sentence = canned_sentence
        self.called = False

    def generate_sentence(self, reasons_payload):
        self.called = True
        return self.canned_sentence


class RaisingLLMClient:
    def generate_sentence(self, reasons_payload):
        raise AssertionError("LLM should not have been called")


def _reema_decision_and_trace():
    features = {"days_since_delivery": 9, "defect_confidence": 0.61}
    decision = decide("defect_claim", features, evaluate_case)
    trace_outcome = trace("defect_claim", features, decision, evaluate_case, passing_patch)
    return decision, trace_outcome


def _kochi_decision_and_trace():
    features = {"days_since_delivery": 6, "wear_confidence": 0.94}
    decision = decide("footwear", features, evaluate_case)
    trace_outcome = trace("footwear", features, decision, evaluate_case, passing_patch)
    return decision, trace_outcome


def _indore_decision_and_trace():
    features = {"days_since_delivery": 3, "is_final_sale": True}
    decision = decide("final_sale", features, evaluate_case)
    trace_outcome = trace("final_sale", features, decision, evaluate_case, passing_patch)
    return decision, trace_outcome


class TestBugCatalogRegressions:
    """Every one of these is a sentence known to ship wrong, and Justify's
    checks must reject it.
    """

    def test_omission_by_summary_is_rejected(self):
        # First version: compresses two specific reasons into one empty
        # phrase.
        decision, trace_outcome = _reema_decision_and_trace()
        llm = FakeLLMClient("Your return was not approved because it did not meet our return policy requirements.")

        result = justify(decision, trace_outcome, llm, JUSTIFY_METADATA)

        assert result.status is JustificationStatus.FAILED_REVIEW
        assert result.faithfulness_check_passed is False

    def test_vague_rounding_is_rejected(self):
        # "0.71 rounded to 'just under the required threshold'".
        decision, trace_outcome = _reema_decision_and_trace()
        llm = FakeLLMClient(
            "Your return was not approved because it was filed just under the required window, "
            "and separately the photo confidence was close to the threshold for the defect exception."
        )

        result = justify(decision, trace_outcome, llm, JUSTIFY_METADATA)

        assert result.status is JustificationStatus.FAILED_REVIEW
        assert result.faithfulness_check_passed is False

    def test_internal_jargon_leak_is_rejected(self):
        # "non-determinative" — internal vocabulary a customer would never
        # say.
        decision, trace_outcome = _kochi_decision_and_trace()
        llm = FakeLLMClient(
            "Your return was not approved: rule FOOTWEAR-EXCEPTION-03 fired because wear was non-determinative "
            "against the footwear policy."
        )

        result = justify(decision, trace_outcome, llm, JUSTIFY_METADATA)

        assert result.status is JustificationStatus.FAILED_REVIEW
        assert result.plain_language_check_passed is False

    def test_single_cause_template_that_drops_the_second_reason_is_rejected(self):
        # A dead template attempt: picks one reason (window) and stays
        # silent about the other (defect exception).
        decision, trace_outcome = _reema_decision_and_trace()
        llm = FakeLLMClient(
            "Your return could not be approved because it was submitted nine days after delivery, "
            "two days past our seven-day return window."
        )

        result = justify(decision, trace_outcome, llm, JUSTIFY_METADATA)

        assert result.status is JustificationStatus.FAILED_REVIEW
        assert result.faithfulness_check_passed is False


class TestShippedSentencesPassCleanly:
    def test_reema_final_sentence_passes(self):
        # The actual, corrected, shipped sentence.
        decision, trace_outcome = _reema_decision_and_trace()
        llm = FakeLLMClient(
            "Your return was not approved for two separate reasons: it was submitted nine days after delivery, "
            "two days past our seven-day return window, and separately, the photo provided did not clearly show "
            "the manufacturing defect claimed, which our policy requires for the extended defect exception. "
            "Either reason alone would have led to the same result."
        )

        result = justify(decision, trace_outcome, llm, JUSTIFY_METADATA)

        assert result.status is JustificationStatus.VERIFIED
        assert result.faithfulness_check_passed is True
        assert result.plain_language_check_passed is True
        assert result.boundary_line != ""

    def test_kochi_sentence_passes(self):
        decision, trace_outcome = _kochi_decision_and_trace()
        llm = FakeLLMClient(
            "Your return was not approved because the item showed visible signs of outdoor wear, "
            "which our footwear policy does not cover."
        )

        result = justify(decision, trace_outcome, llm, JUSTIFY_METADATA)

        assert result.status is JustificationStatus.VERIFIED

    def test_indore_sentence_passes(self):
        decision, trace_outcome = _indore_decision_and_trace()
        llm = FakeLLMClient(
            "Your return was not approved because this item was purchased under our Final Sale promotion, "
            "which is marked non-returnable in the terms shown at checkout. This category is excluded from "
            "our standard return policy regardless of the reason for return."
        )

        result = justify(decision, trace_outcome, llm, JUSTIFY_METADATA)

        assert result.status is JustificationStatus.VERIFIED


class TestGuardrails:
    def test_approved_case_never_calls_the_llm(self):
        features = {"days_since_delivery": 2, "defect_confidence": 0.95}
        decision = decide("defect_claim", features, evaluate_case)
        trace_outcome = trace("defect_claim", features, decision, evaluate_case, passing_patch)

        result = justify(decision, trace_outcome, RaisingLLMClient(), JUSTIFY_METADATA)

        assert result.status is JustificationStatus.VERIFIED
        assert result.sentence

    def test_unresolved_trace_never_calls_the_llm(self):
        decision, trace_outcome = _reema_decision_and_trace()
        # Force an unresolved outcome, as if Trace couldn't neutralize a rule.
        from packages.candor.models import TraceOutcome, VerificationStatus

        broken_trace = TraceOutcome(
            determinative_reasons=[], verification_status=VerificationStatus.UNRESOLVED, counterfactual_log=[]
        )

        result = justify(decision, broken_trace, RaisingLLMClient(), JUSTIFY_METADATA)

        assert result.status is JustificationStatus.FAILED_REVIEW
        assert result.sentence == ""

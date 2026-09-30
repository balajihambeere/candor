"""Reproduces the reference scenarios' own worked numbers as unit tests for
the deterministic rule layer, before any Decide/Trace/Justify logic touches
them.
"""

from domains.returns import rules
from domains.returns.catalog import evaluate_case


class TestWindowRule:
    def test_reema_day_nine_fails(self):
        # "day nine had already missed" the 7-day window.
        result = rules.window_rule(days_since_delivery=9)
        assert result.passed is False
        assert result.evaluated_value == 9
        assert result.threshold == 7

    def test_boundary_day_seven_passes(self):
        result = rules.window_rule(days_since_delivery=7)
        assert result.passed is True

    def test_kochi_day_six_passes(self):
        # "days_since_delivery = 6 (limit: 7, not exceeded)".
        result = rules.window_rule(days_since_delivery=6)
        assert result.passed is True


class TestDefectExceptionRule:
    def test_reema_blurry_photo_fails_on_confidence(self):
        # "0.61 confidence against a required 0.75".
        result = rules.defect_exception_rule(days_since_delivery=9, defect_confidence=0.61)
        assert result.passed is False
        assert result.evaluated_value == 0.61
        assert result.threshold == 0.75

    def test_reema_sharp_photo_clears_confidence_but_window_already_failed_elsewhere(self):
        # "Reema's second, sharper photo ... scored 0.89 and would have
        # cleared the exception easily."
        result = rules.defect_exception_rule(days_since_delivery=9, defect_confidence=0.89)
        assert result.passed is True

    def test_beyond_extended_window_fails_on_date_not_confidence(self):
        result = rules.defect_exception_rule(days_since_delivery=20, defect_confidence=0.99)
        assert result.passed is False
        assert result.evaluated_value == 20
        assert result.threshold == 15


class TestFootwearWearRule:
    def test_kochi_worn_sandals_fail(self):
        # "wear_classifier_confidence = 0.94 (threshold: 0.40, exceeded)".
        result = rules.footwear_wear_rule(wear_confidence=0.94)
        assert result.passed is False
        assert result.evaluated_value == 0.94
        assert result.threshold == 0.40

    def test_low_wear_confidence_passes(self):
        result = rules.footwear_wear_rule(wear_confidence=0.10)
        assert result.passed is True


class TestFinalSaleRule:
    def test_final_sale_item_fails(self):
        result = rules.final_sale_rule(is_final_sale=True)
        assert result.passed is False

    def test_non_final_sale_item_passes(self):
        result = rules.final_sale_rule(is_final_sale=False)
        assert result.passed is True


class TestEvaluateCase:
    def test_reema_case_both_rules_fail_independently(self):
        # Both the window rule and the defect exception fail Reema's case
        # on their own terms.
        reasons = evaluate_case(
            "defect_claim",
            {"days_since_delivery": 9, "defect_confidence": 0.61},
        )
        assert {r.rule_id for r in reasons} == {"WINDOW-STANDARD-01", "DEFECT-EXCEPTION-02"}
        assert all(not r.passed for r in reasons)

    def test_kochi_case_only_footwear_rule_fails(self):
        reasons = evaluate_case(
            "footwear",
            {"days_since_delivery": 6, "wear_confidence": 0.94},
        )
        by_id = {r.rule_id: r for r in reasons}
        assert by_id["WINDOW-STANDARD-01"].passed is True
        assert by_id["FOOTWEAR-EXCEPTION-03"].passed is False

    def test_indore_final_sale_case(self):
        reasons = evaluate_case(
            "final_sale",
            {"days_since_delivery": 3, "is_final_sale": True},
        )
        by_id = {r.rule_id: r for r in reasons}
        assert by_id["WINDOW-STANDARD-01"].passed is True
        assert by_id["FINAL-SALE-EXCLUSION"].passed is False

    def test_general_category_only_runs_window_rule(self):
        reasons = evaluate_case("general", {"days_since_delivery": 2})
        assert [r.rule_id for r in reasons] == ["WINDOW-STANDARD-01"]

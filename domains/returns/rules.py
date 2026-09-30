"""Deterministic rule evaluators for Zuxpert Fashion's return-eligibility
service. Every rule here is a plain comparison against an already-computed
input (a date delta, a classifier confidence score handed in by the
caller). Candor does not reimplement image classification; it wraps
whatever decision logic already exists and captures its reasoning
structurally, which is exactly what Decide does to Zuxpert's existing
eligibility check.
"""

from packages.candor.models import RuleResult

WINDOW_DAYS = 7
DEFECT_EXTENDED_WINDOW_DAYS = 15
DEFECT_CONFIDENCE_THRESHOLD = 0.75
FOOTWEAR_WEAR_THRESHOLD = 0.40
BULK_ORDER_MAX_QUANTITY = 5


def window_rule(days_since_delivery: int, window_days: int = WINDOW_DAYS) -> RuleResult:
    """The universal check: every return is subject to this, regardless of
    category. Reema: day 9 > 7 -> fails, independent of her photo.
    """
    return RuleResult(
        rule_id="WINDOW-STANDARD-01",
        evaluated_value=days_since_delivery,
        threshold=window_days,
        comparator="<=",
        passed=days_since_delivery <= window_days,
    )


def defect_exception_rule(
    days_since_delivery: int,
    defect_confidence: float,
    extended_window_days: int = DEFECT_EXTENDED_WINDOW_DAYS,
    confidence_threshold: float = DEFECT_CONFIDENCE_THRESHOLD,
) -> RuleResult:
    """Category-specific rule for a manufacturing-defect claim: extends the
    window to 15 days, but only if the defect-photo classifier's confidence
    clears the threshold. Reema: day 9 <= 15 (clears the date sub-check), but
    confidence 0.61 < 0.75 -> fails on confidence alone, independent of the
    date. The reported evaluated_value/threshold is always the specific
    sub-check that actually determined this rule's own pass/fail.
    """
    if days_since_delivery > extended_window_days:
        return RuleResult(
            rule_id="DEFECT-EXCEPTION-02",
            evaluated_value=days_since_delivery,
            threshold=extended_window_days,
            comparator="<=",
            passed=False,
        )
    return RuleResult(
        rule_id="DEFECT-EXCEPTION-02",
        evaluated_value=defect_confidence,
        threshold=confidence_threshold,
        comparator=">=",
        passed=defect_confidence >= confidence_threshold,
    )


def footwear_wear_rule(wear_confidence: float, threshold: float = FOOTWEAR_WEAR_THRESHOLD) -> RuleResult:
    """Kochi's rule: a wear-classifier confidence above the threshold means
    visible outdoor wear inconsistent with a defect claim. 0.94 > 0.40 ->
    denied.
    """
    return RuleResult(
        rule_id="FOOTWEAR-EXCEPTION-03",
        evaluated_value=wear_confidence,
        threshold=threshold,
        comparator="<=",
        passed=wear_confidence <= threshold,
    )


def final_sale_rule(is_final_sale: bool) -> RuleResult:
    """Indore's rule: Final Sale items are non-returnable regardless of the
    reason for return. No date, no confidence score — a flat exclusion.
    """
    return RuleResult(
        rule_id="FINAL-SALE-EXCLUSION",
        evaluated_value=is_final_sale,
        threshold=False,
        comparator="==",
        passed=not is_final_sale,
    )


def bulk_order_rule(quantity: int, max_quantity: int = BULK_ORDER_MAX_QUANTITY) -> RuleResult:
    """An underused rule that needs a pre-purchase warning, not just a
    post-purchase denial: orders above the per-SKU quantity cap aren't
    eligible for standard return.
    """
    return RuleResult(
        rule_id="BULK-ORDER-RESTRICTION-04",
        evaluated_value=quantity,
        threshold=max_quantity,
        comparator="<=",
        passed=quantity <= max_quantity,
    )

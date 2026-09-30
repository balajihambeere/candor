"""Category -> applicable rule mapping. Every return runs the universal
window rule; a category may add exactly one more rule: the universal
window check, always, paired with one category-specific second rule that
depends on what's being returned.
"""

from collections.abc import Callable

from packages.candor.models import RuleResult

from . import rules

CATEGORIES: dict[str, Callable[[dict], RuleResult] | None] = {
    "general": None,
    "defect_claim": lambda f: rules.defect_exception_rule(
        days_since_delivery=f["days_since_delivery"],
        defect_confidence=f["defect_confidence"],
    ),
    "footwear": lambda f: rules.footwear_wear_rule(wear_confidence=f["wear_confidence"]),
    "final_sale": lambda f: rules.final_sale_rule(is_final_sale=f["is_final_sale"]),
    "bulk_order": lambda f: rules.bulk_order_rule(quantity=f["quantity"]),
}


class UnknownCategoryError(ValueError):
    pass


def evaluate_case(category: str, features: dict) -> list[RuleResult]:
    """Run every rule applicable to `category` against `features` and return
    the full set of RuleResults Decide should capture — not just the ones
    that failed.
    """
    if category not in CATEGORIES:
        raise UnknownCategoryError(f"no rules registered for category={category!r}")

    reasons = [rules.window_rule(days_since_delivery=features["days_since_delivery"])]

    category_rule = CATEGORIES[category]
    if category_rule is not None:
        reasons.append(category_rule(features))

    return reasons


def _passing_patch_window(features: dict) -> dict:
    return {"days_since_delivery": rules.WINDOW_DAYS}


def _passing_patch_defect_exception(features: dict) -> dict:
    # Only touch whichever sub-check is actually failing, so neutralizing
    # this rule doesn't accidentally disturb a feature another rule (e.g.
    # the window rule) is being held at, for the sake of a different probe.
    patch = {}
    if features["days_since_delivery"] > rules.DEFECT_EXTENDED_WINDOW_DAYS:
        patch["days_since_delivery"] = rules.DEFECT_EXTENDED_WINDOW_DAYS
    if features["defect_confidence"] < rules.DEFECT_CONFIDENCE_THRESHOLD:
        patch["defect_confidence"] = rules.DEFECT_CONFIDENCE_THRESHOLD
    return patch


def _passing_patch_footwear(features: dict) -> dict:
    return {"wear_confidence": rules.FOOTWEAR_WEAR_THRESHOLD}


def _passing_patch_final_sale(features: dict) -> dict:
    return {"is_final_sale": False}


def _passing_patch_bulk_order(features: dict) -> dict:
    return {"quantity": rules.BULK_ORDER_MAX_QUANTITY}


_PASSING_PATCHES = {
    "WINDOW-STANDARD-01": _passing_patch_window,
    "DEFECT-EXCEPTION-02": _passing_patch_defect_exception,
    "FOOTWEAR-EXCEPTION-03": _passing_patch_footwear,
    "FINAL-SALE-EXCLUSION": _passing_patch_final_sale,
    "BULK-ORDER-RESTRICTION-04": _passing_patch_bulk_order,
}


def passing_patch(rule_id: str, features: dict) -> dict | None:
    """Return a features-dict patch that would make `rule_id` pass, given
    the current features — or None if this domain doesn't know how to
    neutralize that rule (Trace must then route the case to human review
    rather than guess).
    """
    fn = _PASSING_PATCHES.get(rule_id)
    if fn is None:
        return None
    return fn(features)


# Justify metadata: how Trace's rule_ids should be talked about, and how
# strictly the faithfulness checker should hold the sentence to it. Day/count
# rules get exact-number enforcement ("nine days after delivery");
# confidence-scored classifier rules are checked for topical coverage
# instead of a raw float, describing them qualitatively ("did not clearly
# show the manufacturing defect claimed") rather than quoting 0.61 at a
# customer who has no way to interpret it.
JUSTIFY_METADATA: dict[str, dict] = {
    "WINDOW-STANDARD-01": {
        "keywords": ["day", "window"],
        "requires_exact_numbers": True,
        "plain_description": "the return was filed after the standard return window",
    },
    "DEFECT-EXCEPTION-02": {
        "keywords": ["photo", "defect", "image", "picture"],
        "requires_exact_numbers": False,
        "plain_description": "the submitted photo did not clearly show the claimed manufacturing defect",
    },
    "FOOTWEAR-EXCEPTION-03": {
        "keywords": ["wear", "worn", "footwear"],
        "requires_exact_numbers": False,
        "plain_description": "the item showed visible signs of outdoor wear",
    },
    "FINAL-SALE-EXCLUSION": {
        "keywords": ["final sale", "non-returnable", "promotion"],
        "requires_exact_numbers": False,
        "plain_description": "the item was purchased under a non-returnable Final Sale promotion",
    },
    "BULK-ORDER-RESTRICTION-04": {
        "keywords": ["quantity", "bulk", "order"],
        "requires_exact_numbers": True,
        "plain_description": "the order quantity exceeded the per-order limit eligible for standard return",
    },
}

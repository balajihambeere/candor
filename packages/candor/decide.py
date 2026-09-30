"""Decide: the first stage of the Candor pipeline.

Captures the verdict and every rule evaluated to reach it, in one pass, from
whatever deterministic rules catalog the caller's domain provides. There is
no second call, no free-text explanation, no raw-context dump — the record
*is* the reasoning, tied to the same values the rules engine actually
computed. Domain-agnostic on purpose: it knows nothing about returns,
footwear, or kurtas, only that it's given a category, some features, and a
function that turns those into RuleResults.
"""

from collections.abc import Callable

from packages.candor.models import DecisionRecord, RuleResult, Verdict

RuleEvaluator = Callable[[str, dict], list[RuleResult]]


def decide(category: str, features: dict, evaluate_case: RuleEvaluator) -> DecisionRecord:
    reasons = evaluate_case(category, features)
    verdict = Verdict.DENIED if any(not r.passed for r in reasons) else Verdict.APPROVED
    return DecisionRecord(verdict=verdict, reasons=reasons)

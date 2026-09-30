"""Trace: the second stage of the Candor pipeline.

Verifies Decide's record by counterfactual replay instead of trusting it.
For every failing reason, every *other* failing reason is neutralized to a
passing counterfactual value, this one is left exactly as it was, and the
case is replayed. If the case is still denied — because of this reason,
specifically — the reason is confirmed independently sufficient
("determinative"). This is deliberately not a single-cause pick: Reema's
case has two reasons that each pass this probe on their own, which is
exactly what a naive first pass gets wrong by picking only the
first-evaluated rule.

Anything Trace can't cleanly probe — the domain doesn't know how to
neutralize a rule, or a probe comes back ambiguous — leaves the case
UNRESOLVED. Unresolved records are never disclosed; they're routed to a
human instead, the same discipline applied everywhere Trace can't back up
a claim.
"""

from collections.abc import Callable

from packages.candor.decide import RuleEvaluator
from packages.candor.models import (
    CounterfactualCheck,
    DecisionRecord,
    TraceOutcome,
    VerificationStatus,
)

PassingPatchResolver = Callable[[str, dict], dict | None]


def trace(
    category: str,
    features: dict,
    decision: DecisionRecord,
    evaluate_case: RuleEvaluator,
    passing_patch: PassingPatchResolver,
) -> TraceOutcome:
    failing = decision.failing_reasons
    if not failing:
        # Nothing was denied; there's nothing to attribute a denial to.
        return TraceOutcome(
            determinative_reasons=[], verification_status=VerificationStatus.VERIFIED, counterfactual_log=[]
        )

    log: list[CounterfactualCheck] = []
    determinative: list[str] = []
    unresolved = False

    for reason in failing:
        others = [r for r in failing if r.rule_id != reason.rule_id]

        cf_features = dict(features)
        patch_failed = False
        for other in others:
            patch = passing_patch(other.rule_id, cf_features)
            if patch is None:
                patch_failed = True
                break
            cf_features.update(patch)

        if patch_failed:
            unresolved = True
            continue

        cf_reasons = evaluate_case(category, cf_features)
        cf_by_id = {r.rule_id: r for r in cf_reasons}
        this_under_counterfactual = cf_by_id.get(reason.rule_id)

        if this_under_counterfactual is None:
            # The domain's rule set changed shape under the counterfactual
            # (shouldn't happen for a fixed category) — can't trust the probe.
            unresolved = True
            continue

        still_denied = any(not r.passed for r in cf_reasons)
        sufficient = still_denied and not this_under_counterfactual.passed

        log.append(
            CounterfactualCheck(
                rule_id=reason.rule_id,
                neutralized_other_reasons=[o.rule_id for o in others],
                still_denied=sufficient,
            )
        )
        if sufficient:
            determinative.append(reason.rule_id)

    status = (
        VerificationStatus.VERIFIED
        if determinative and not unresolved
        else VerificationStatus.UNRESOLVED
    )
    return TraceOutcome(determinative_reasons=determinative, verification_status=status, counterfactual_log=log)

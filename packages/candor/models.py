"""Core data shapes shared by every Candor stage.

These are domain-agnostic: a rules catalog (like domains/returns) produces
RuleResults, Decide assembles them into a DecisionRecord, Trace produces a
TraceOutcome, Justify produces a JustificationResult. Nothing here knows
anything about returns, footwear, or kurtas.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Verdict(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"


Comparator = str  # one of "<=", ">=", "==", ">", "<"


class RuleResult(BaseModel):
    """One rule's evaluation: the exact value it checked, against the exact
    threshold, and whether it blocked the decision. This is the only unit of
    information Decide is allowed to produce — never free text.
    """

    rule_id: str
    evaluated_value: float | int | bool
    threshold: float | int | bool
    comparator: Comparator
    passed: bool
    """True = this rule did not block the decision (not a reason for denial)."""


class DecisionRecord(BaseModel):
    """Decide's output: a verdict plus every rule that was evaluated to reach
    it. Deliberately holds *all* evaluated rules, not just one 'determinative'
    pick — Reema's case is exactly why: two rules can each independently and
    correctly deny the same case.
    """

    verdict: Verdict
    reasons: list[RuleResult]

    @property
    def failing_reasons(self) -> list[RuleResult]:
        """Reasons that actually contributed to a denial."""
        return [r for r in self.reasons if not r.passed]


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    UNRESOLVED = "unresolved"


class CounterfactualCheck(BaseModel):
    """One Trace probe for a failing reason: every *other* failing reason is
    neutralized to a passing counterfactual value, this reason is left at
    its original (failing) value, and the case is replayed. `still_denied`
    True means this reason, on its own, is enough to cause the denial —
    Reema's window and defect-exception reasons both pass this probe
    independently, which is what makes them both determinative.
    """

    rule_id: str
    neutralized_other_reasons: list[str]
    still_denied: bool


class TraceOutcome(BaseModel):
    """Trace's output: which failing reasons are genuinely, independently
    sufficient to cause the denial (confirmed by counterfactual replay, not
    asserted), and the full audit log of the probes that established that.
    """

    determinative_reasons: list[str]
    verification_status: VerificationStatus
    counterfactual_log: list[CounterfactualCheck]


class JustificationStatus(str, Enum):
    VERIFIED = "verified"
    FAILED_REVIEW = "failed_review"


class JustificationResult(BaseModel):
    """Justify's output: one sentence, generated only from the Trace-verified
    record, plus the fixed boundary line that separates 'this decision,
    explained' from 'an adjacent concern, logged separately' (the False
    Clarity fix). status=FAILED_REVIEW means neither field should ever reach
    a customer — it's routed to the review queue instead.
    """

    sentence: str
    boundary_line: str
    faithfulness_check_passed: bool
    plain_language_check_passed: bool
    status: JustificationStatus

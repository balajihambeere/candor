"""Persistence for the Candor pipeline. Turns the pure PipelineResult
(packages/candor/pipeline.py) into rows, and decides — mechanically, not by
guessing — whether a case needs a human: any Trace-unresolved or
Justify-failed-review result is queued, never disclosed automatically.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from database.models import (
    Case,
    Decision,
    Disclosure,
    DisclosureChannel,
    Justification,
    JustificationStatus as ORMJustificationStatus,
    ReopenRequest,
    ReviewItem,
    ReviewReason,
    ReviewStatus,
    TraceResult,
    VerificationStatus as ORMVerificationStatus,
)
from packages.candor.models import JustificationStatus, VerificationStatus
from packages.candor.pipeline import PipelineResult


def create_case(db: Session, domain: str, category: str, input_payload: dict) -> Case:
    case = Case(domain=domain, category=category, input_payload=input_payload)
    db.add(case)
    db.flush()
    return case


def persist_pipeline_result(db: Session, case: Case, result: PipelineResult) -> Decision:
    decision = Decision(
        case_id=case.id,
        verdict=result.decision.verdict.value,
        reasons=[r.model_dump() for r in result.decision.reasons],
    )
    db.add(decision)
    db.flush()

    trace_row = TraceResult(
        decision_id=decision.id,
        determinative_reasons=result.trace_outcome.determinative_reasons,
        verification_status=(
            ORMVerificationStatus.VERIFIED
            if result.trace_outcome.verification_status == VerificationStatus.VERIFIED
            else ORMVerificationStatus.UNRESOLVED
        ),
        counterfactual_log=[c.model_dump() for c in result.trace_outcome.counterfactual_log],
    )
    db.add(trace_row)

    justification_row = Justification(
        decision_id=decision.id,
        sentence=result.justification.sentence,
        boundary_line=result.justification.boundary_line,
        faithfulness_check_passed=result.justification.faithfulness_check_passed,
        plain_language_check_passed=result.justification.plain_language_check_passed,
        status=(
            ORMJustificationStatus.VERIFIED
            if result.justification.status == JustificationStatus.VERIFIED
            else ORMJustificationStatus.FAILED_REVIEW
        ),
    )
    db.add(justification_row)

    review_reason = _review_reason_for(result)
    if review_reason is not None:
        db.add(ReviewItem(decision_id=decision.id, reason=review_reason))

    db.flush()
    return decision


def _review_reason_for(result: PipelineResult) -> ReviewReason | None:
    if result.trace_outcome.verification_status != VerificationStatus.VERIFIED:
        return ReviewReason.TRACE_UNRESOLVED
    if result.justification.status != JustificationStatus.VERIFIED:
        if not result.justification.faithfulness_check_passed:
            return ReviewReason.JUSTIFY_FAITHFULNESS_FAILED
        if not result.justification.plain_language_check_passed:
            return ReviewReason.JUSTIFY_PLAIN_LANGUAGE_FAILED
    return None


def get_decision(db: Session, decision_id: uuid.UUID) -> Decision | None:
    return db.get(Decision, decision_id)


def get_summary_stats(db: Session) -> dict:
    total = db.query(Decision).count()
    approved = db.query(Decision).filter(Decision.verdict == "approved").count()
    denied = db.query(Decision).filter(Decision.verdict == "denied").count()
    pending_review = db.query(ReviewItem).filter(ReviewItem.status == ReviewStatus.PENDING).count()
    disclosed_decisions = db.query(Disclosure.decision_id).distinct().count()
    return {
        "total_decisions": total,
        "approved": approved,
        "denied": denied,
        "pending_review": pending_review,
        "disclosed_decisions": disclosed_decisions,
    }


def list_decisions(db: Session, limit: int = 50, offset: int = 0) -> tuple[list[Decision], int]:
    total = db.query(Decision).count()
    items = (
        db.query(Decision)
        .order_by(Decision.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def list_review_queue(db: Session, status: ReviewStatus = ReviewStatus.PENDING) -> list[ReviewItem]:
    return db.query(ReviewItem).filter(ReviewItem.status == status).order_by(ReviewItem.created_at.asc()).all()


def get_review_item(db: Session, item_id: uuid.UUID) -> ReviewItem | None:
    return db.get(ReviewItem, item_id)


def resolve_review_item(
    db: Session, item: ReviewItem, assigned_to: str, resolution_notes: str
) -> ReviewItem:
    item.status = ReviewStatus.RESOLVED
    item.assigned_to = assigned_to
    item.resolution_notes = resolution_notes
    item.resolved_at = datetime.now(UTC)
    db.flush()
    return item


def create_disclosure(
    db: Session,
    decision_id: uuid.UUID,
    channel: DisclosureChannel,
    disclosed_by: str,
    sentence_sent: str,
    delay_owned: bool,
    customer_response: str | None = None,
    held_up: bool | None = None,
) -> Disclosure:
    disclosure = Disclosure(
        decision_id=decision_id,
        channel=channel,
        disclosed_by=disclosed_by,
        sentence_sent=sentence_sent,
        delay_owned=delay_owned,
        customer_response=customer_response,
        held_up=held_up,
    )
    db.add(disclosure)
    db.flush()
    return disclosure


class UnverifiedJustificationError(ValueError):
    """Raised when disclosing a decision whose justification was never
    verified, and no human-reviewed sentence_override was supplied. Shared
    by both the API and the dashboard, so the "never disclosed
    automatically" rule can't be bypassed by going through the UI instead
    of the API.
    """


def disclose_decision(
    db: Session,
    decision: Decision,
    channel: DisclosureChannel,
    disclosed_by: str,
    delay_owned: bool,
    sentence_override: str | None = None,
    customer_response: str | None = None,
    held_up: bool | None = None,
) -> Disclosure:
    justification = decision.justification
    if justification.status != ORMJustificationStatus.VERIFIED and not sentence_override:
        raise UnverifiedJustificationError(
            "this decision's justification was not verified — "
            "resolve it in the review queue and supply a reviewed sentence to disclose it"
        )

    sentence_sent = sentence_override or f"{justification.sentence} {justification.boundary_line}".strip()

    return create_disclosure(
        db,
        decision_id=decision.id,
        channel=channel,
        disclosed_by=disclosed_by,
        sentence_sent=sentence_sent,
        delay_owned=delay_owned,
        customer_response=customer_response,
        held_up=held_up,
    )


def list_disclosures(db: Session, decision_id: uuid.UUID | None = None) -> list[Disclosure]:
    query = db.query(Disclosure)
    if decision_id is not None:
        query = query.filter(Disclosure.decision_id == decision_id)
    return query.order_by(Disclosure.disclosed_at.desc()).all()


def create_reopen_request(
    db: Session, original_decision_id: uuid.UUID, new_evidence: dict
) -> ReopenRequest:
    reopen = ReopenRequest(original_decision_id=original_decision_id, new_evidence=new_evidence)
    db.add(reopen)
    db.flush()
    return reopen


def link_reopen_to_new_decision(db: Session, reopen: ReopenRequest, new_decision_id: uuid.UUID) -> ReopenRequest:
    reopen.triggered_decision_id = new_decision_id
    db.flush()
    return reopen

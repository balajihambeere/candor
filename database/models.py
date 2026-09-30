"""SQLAlchemy models for the Candor pipeline.

Table-per-stage, mirroring the pipeline's own four-stage shape:
Decide -> decisions, Trace -> trace_results, Justify -> justifications,
Disclose -> disclosures. `review_queue` and `reopen_requests` are the two
supporting mechanisms this requires: unverifiable records never reach a
customer (review_queue), and new evidence on a decided case must re-enter
the pipeline instead of vanishing (reopen_requests).
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class VerificationStatus(str, enum.Enum):
    VERIFIED = "verified"
    UNRESOLVED = "unresolved"


class JustificationStatus(str, enum.Enum):
    VERIFIED = "verified"
    FAILED_REVIEW = "failed_review"


class ReviewReason(str, enum.Enum):
    TRACE_UNRESOLVED = "trace_unresolved"
    JUSTIFY_FAITHFULNESS_FAILED = "justify_faithfulness_failed"
    JUSTIFY_PLAIN_LANGUAGE_FAILED = "justify_plain_language_failed"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    RESOLVED = "resolved"


class DisclosureChannel(str, enum.Enum):
    CALL = "call"
    EMAIL = "email"
    CHAT = "chat"


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = _uuid_pk()
    domain: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    input_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    decisions: Mapped[list["Decision"]] = relationship(back_populates="case")


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    reasons: Mapped[list] = mapped_column(JSONB, nullable=False)
    """List of {rule_id, evaluated_value, threshold, comparator, passed}."""
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    case: Mapped["Case"] = relationship(back_populates="decisions")
    trace_result: Mapped["TraceResult | None"] = relationship(back_populates="decision", uselist=False)
    justification: Mapped["Justification | None"] = relationship(back_populates="decision", uselist=False)
    review_items: Mapped[list["ReviewItem"]] = relationship(back_populates="decision")
    disclosures: Mapped[list["Disclosure"]] = relationship(back_populates="decision")


class TraceResult(Base):
    __tablename__ = "trace_results"

    id: Mapped[uuid.UUID] = _uuid_pk()
    decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decisions.id"), nullable=False, unique=True)
    determinative_reasons: Mapped[list] = mapped_column(JSONB, nullable=False)
    """List of rule_ids confirmed, by counterfactual replay, to independently flip the verdict."""
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status"), nullable=False
    )
    counterfactual_log: Mapped[list] = mapped_column(JSONB, nullable=False)
    """List of {rule_id, counterfactual_value, verdict_flipped} — the audit trail Trace ran."""
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    decision: Mapped["Decision"] = relationship(back_populates="trace_result")


class Justification(Base):
    __tablename__ = "justifications"

    id: Mapped[uuid.UUID] = _uuid_pk()
    decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decisions.id"), nullable=False, unique=True)
    sentence: Mapped[str] = mapped_column(Text, nullable=False)
    boundary_line: Mapped[str] = mapped_column(Text, nullable=False)
    faithfulness_check_passed: Mapped[bool] = mapped_column(nullable=False)
    plain_language_check_passed: Mapped[bool] = mapped_column(nullable=False)
    status: Mapped[JustificationStatus] = mapped_column(
        Enum(JustificationStatus, name="justification_status"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    decision: Mapped["Decision"] = relationship(back_populates="justification")


class ReviewItem(Base):
    __tablename__ = "review_queue"

    id: Mapped[uuid.UUID] = _uuid_pk()
    decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decisions.id"), nullable=False)
    reason: Mapped[ReviewReason] = mapped_column(Enum(ReviewReason, name="review_reason"), nullable=False)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status"), nullable=False, default=ReviewStatus.PENDING
    )
    assigned_to: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    decision: Mapped["Decision"] = relationship(back_populates="review_items")


class Disclosure(Base):
    __tablename__ = "disclosures"

    id: Mapped[uuid.UUID] = _uuid_pk()
    decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decisions.id"), nullable=False)
    channel: Mapped[DisclosureChannel] = mapped_column(Enum(DisclosureChannel, name="disclosure_channel"), nullable=False)
    disclosed_by: Mapped[str] = mapped_column(String(128), nullable=False)
    disclosed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    delay_owned: Mapped[bool] = mapped_column(nullable=False, default=False)
    sentence_sent: Mapped[str] = mapped_column(Text, nullable=False)
    customer_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    held_up: Mapped[bool | None] = mapped_column(nullable=True)
    """Null until a follow-up (or its absence) lets us say whether the explanation held up."""

    decision: Mapped["Decision"] = relationship(back_populates="disclosures")


class ReopenRequest(Base):
    __tablename__ = "reopen_requests"

    id: Mapped[uuid.UUID] = _uuid_pk()
    original_decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decisions.id"), nullable=False)
    new_evidence: Mapped[dict] = mapped_column(JSONB, nullable=False)
    triggered_decision_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("decisions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

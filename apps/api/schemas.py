import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DecisionCreateRequest(BaseModel):
    domain: str = Field(examples=["returns"])
    category: str = Field(examples=["defect_claim", "footwear", "final_sale", "bulk_order", "general"])
    features: dict = Field(examples=[{"days_since_delivery": 9, "defect_confidence": 0.61}])


class ReasonSchema(BaseModel):
    rule_id: str
    evaluated_value: float | int | bool
    threshold: float | int | bool
    comparator: str
    passed: bool


class TraceSchema(BaseModel):
    determinative_reasons: list[str]
    verification_status: str
    counterfactual_log: list[dict]


class JustificationSchema(BaseModel):
    sentence: str
    boundary_line: str
    faithfulness_check_passed: bool
    plain_language_check_passed: bool
    status: str


class DecisionResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    verdict: str
    reasons: list[ReasonSchema]
    trace: TraceSchema
    justification: JustificationSchema
    needs_review: bool
    created_at: datetime


class DecisionSummaryResponse(BaseModel):
    id: uuid.UUID
    domain: str
    category: str
    verdict: str
    needs_review: bool
    created_at: datetime


class DecisionListResponse(BaseModel):
    items: list[DecisionSummaryResponse]
    total: int
    limit: int
    offset: int


class StatsSummaryResponse(BaseModel):
    total_decisions: int
    approved: int
    denied: int
    pending_review: int
    disclosed_decisions: int


class CounterfactualRequest(BaseModel):
    feature_overrides: dict = Field(
        examples=[{"days_since_delivery": 6, "defect_confidence": 0.89}],
        description="Feature values to override on the original case before re-evaluating.",
    )


class CounterfactualResponse(BaseModel):
    original_verdict: str
    counterfactual_verdict: str
    would_flip: bool
    counterfactual_reasons: list[ReasonSchema]


class ReviewItemResponse(BaseModel):
    id: uuid.UUID
    decision_id: uuid.UUID
    reason: str
    status: str
    assigned_to: str | None
    resolution_notes: str | None
    resolved_at: datetime | None
    created_at: datetime


class ReviewResolveRequest(BaseModel):
    assigned_to: str
    resolution_notes: str


class DisclosureCreateRequest(BaseModel):
    channel: str = Field(examples=["call", "email", "chat"])
    disclosed_by: str = Field(examples=["uttara"])
    delay_owned: bool = Field(
        default=False, description="Did the message own the delay before giving the answer?"
    )
    sentence_override: str | None = Field(
        default=None,
        description="Required if the justification isn't VERIFIED — a human-reviewed sentence to send instead.",
    )
    customer_response: str | None = None
    held_up: bool | None = Field(
        default=None, description="Did the explanation hold up against the customer's follow-up questions?"
    )


class DisclosureResponse(BaseModel):
    id: uuid.UUID
    decision_id: uuid.UUID
    channel: str
    disclosed_by: str
    disclosed_at: datetime
    delay_owned: bool
    sentence_sent: str
    customer_response: str | None
    held_up: bool | None


class ReopenCreateRequest(BaseModel):
    new_evidence: dict = Field(
        examples=[{"defect_confidence": 0.89}],
        description="Corrected or new feature values that should trigger a fresh Decide/Trace/Justify pass.",
    )


class ReopenResponse(BaseModel):
    reopen_request_id: uuid.UUID
    original_decision_id: uuid.UUID
    new_decision: DecisionResponse

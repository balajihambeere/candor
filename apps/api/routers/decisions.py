import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from apps.api.auth import require_api_key
from apps.api.deps import get_db, get_llm_client
from apps.api.rate_limit import limiter, llm_endpoint_limit
from apps.api.schemas import (
    CounterfactualRequest,
    CounterfactualResponse,
    DecisionCreateRequest,
    DecisionResponse,
    ReasonSchema,
)
from apps.api.serializers import decision_to_response_dict
from database.repository import create_case, get_decision, persist_pipeline_result
from domains.registry import UnknownDomainError, get_domain
from packages.candor.decide import decide
from packages.candor.llm import JustifyLLMClient
from packages.candor.pipeline import run_pipeline

router = APIRouter(prefix="/v1/decisions", tags=["decisions"])


@router.post("", response_model=DecisionResponse, status_code=201, dependencies=[Depends(require_api_key)])
@limiter.limit(llm_endpoint_limit)
def create_decision(
    request: Request,
    body: DecisionCreateRequest,
    db: Session = Depends(get_db),
    llm_client: JustifyLLMClient = Depends(get_llm_client),
):
    try:
        domain = get_domain(body.domain)
    except UnknownDomainError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        result = run_pipeline(domain, body.category, body.features, llm_client)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"missing required feature: {exc}") from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid feature value: {exc}") from exc

    case = create_case(db, body.domain, body.category, body.features)
    decision = persist_pipeline_result(db, case, result)
    db.commit()
    db.refresh(decision)

    return decision_to_response_dict(decision)


@router.get("/{decision_id}", response_model=DecisionResponse)
def read_decision(decision_id: uuid.UUID, db: Session = Depends(get_db)):
    decision = get_decision(db, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")
    return decision_to_response_dict(decision)


@router.post("/{decision_id}/counterfactual", response_model=CounterfactualResponse)
def counterfactual(decision_id: uuid.UUID, body: CounterfactualRequest, db: Session = Depends(get_db)):
    """Answers Reema's own question: "if I'd sent that photo on day 6,
    would you have approved it?" — re-runs Decide against the original
    case's features with the given overrides, using the same deterministic
    rules the original decision used.
    """
    decision = get_decision(db, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")

    case = decision.case
    try:
        domain = get_domain(case.domain)
    except UnknownDomainError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    counterfactual_features = {**case.input_payload, **body.feature_overrides}
    try:
        cf_record = decide(case.category, counterfactual_features, domain.evaluate_case)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"missing required feature: {exc}") from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid feature value: {exc}") from exc

    return CounterfactualResponse(
        original_verdict=decision.verdict,
        counterfactual_verdict=cf_record.verdict.value,
        would_flip=cf_record.verdict.value != decision.verdict,
        counterfactual_reasons=[ReasonSchema(**r.model_dump()) for r in cf_record.reasons],
    )

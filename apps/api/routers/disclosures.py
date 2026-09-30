import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from apps.api.auth import require_api_key
from apps.api.deps import get_db, get_llm_client
from apps.api.rate_limit import limiter, llm_endpoint_limit
from apps.api.schemas import (
    DisclosureCreateRequest,
    DisclosureResponse,
    ReopenCreateRequest,
    ReopenResponse,
)
from apps.api.serializers import decision_to_response_dict
from database.models import DisclosureChannel
from database.repository import (
    UnverifiedJustificationError,
    create_case,
    create_reopen_request,
    disclose_decision,
    get_decision,
    link_reopen_to_new_decision,
    list_disclosures,
    persist_pipeline_result,
)
from domains.registry import get_domain
from packages.candor.llm import JustifyLLMClient
from packages.candor.pipeline import run_pipeline

router = APIRouter(prefix="/v1/decisions", tags=["disclose"])


@router.post(
    "/{decision_id}/disclose",
    response_model=DisclosureResponse,
    status_code=201,
    dependencies=[Depends(require_api_key)],
)
def disclose(decision_id: uuid.UUID, body: DisclosureCreateRequest, db: Session = Depends(get_db)):
    decision = get_decision(db, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")

    try:
        channel = DisclosureChannel(body.channel)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail=f"invalid channel {body.channel!r}, expected one of call/email/chat"
        ) from exc

    try:
        disclosure = disclose_decision(
            db,
            decision,
            channel=channel,
            disclosed_by=body.disclosed_by,
            delay_owned=body.delay_owned,
            sentence_override=body.sentence_override,
            customer_response=body.customer_response,
            held_up=body.held_up,
        )
    except UnverifiedJustificationError as exc:
        # An unverified explanation is never disclosed as-is. A human who
        # reviewed the case can still disclose a corrected sentence
        # explicitly.
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db.commit()
    db.refresh(disclosure)

    return {
        "id": disclosure.id,
        "decision_id": disclosure.decision_id,
        "channel": disclosure.channel.value,
        "disclosed_by": disclosure.disclosed_by,
        "disclosed_at": disclosure.disclosed_at,
        "delay_owned": disclosure.delay_owned,
        "sentence_sent": disclosure.sentence_sent,
        "customer_response": disclosure.customer_response,
        "held_up": disclosure.held_up,
    }


@router.get("/{decision_id}/disclosures", response_model=list[DisclosureResponse])
def read_disclosures(decision_id: uuid.UUID, db: Session = Depends(get_db)):
    decision = get_decision(db, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")

    return [
        {
            "id": d.id,
            "decision_id": d.decision_id,
            "channel": d.channel.value,
            "disclosed_by": d.disclosed_by,
            "disclosed_at": d.disclosed_at,
            "delay_owned": d.delay_owned,
            "sentence_sent": d.sentence_sent,
            "customer_response": d.customer_response,
            "held_up": d.held_up,
        }
        for d in list_disclosures(db, decision_id)
    ]


@router.post(
    "/{decision_id}/reopen",
    response_model=ReopenResponse,
    status_code=201,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(llm_endpoint_limit)
def reopen(
    request: Request,
    decision_id: uuid.UUID,
    body: ReopenCreateRequest,
    db: Session = Depends(get_db),
    llm_client: JustifyLLMClient = Depends(get_llm_client),
):
    """Handles an open gap: a corrected submission (Reema's sharper photo,
    arriving after the original denial) must re-enter the pipeline instead
    of vanishing into a thread nobody revisits.
    """
    decision = get_decision(db, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")

    case = decision.case
    domain = get_domain(case.domain)

    reopen_request = create_reopen_request(db, original_decision_id=decision.id, new_evidence=body.new_evidence)

    new_features = {**case.input_payload, **body.new_evidence}
    try:
        result = run_pipeline(domain, case.category, new_features, llm_client)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"missing required feature: {exc}") from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid feature value: {exc}") from exc

    new_case = create_case(db, case.domain, case.category, new_features)
    new_decision = persist_pipeline_result(db, new_case, result)
    link_reopen_to_new_decision(db, reopen_request, new_decision.id)

    db.commit()
    db.refresh(new_decision)
    db.refresh(reopen_request)

    return {
        "reopen_request_id": reopen_request.id,
        "original_decision_id": decision.id,
        "new_decision": decision_to_response_dict(new_decision),
    }

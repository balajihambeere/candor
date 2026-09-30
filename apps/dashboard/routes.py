import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from apps.api.deps import get_db, get_llm_client
from apps.dashboard.auth import require_dashboard_login
from database.models import DisclosureChannel, ReviewStatus
from database.repository import (
    UnverifiedJustificationError,
    create_case,
    create_reopen_request,
    disclose_decision,
    get_decision,
    get_review_item,
    link_reopen_to_new_decision,
    list_disclosures,
    list_review_queue,
    persist_pipeline_result,
    resolve_review_item,
)
from domains.registry import get_domain
from packages.candor.llm import JustifyLLMClient
from packages.candor.pipeline import run_pipeline

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(require_dashboard_login)])

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@router.get("/")
def index():
    return RedirectResponse(url="/dashboard/review-queue")


@router.get("/review-queue")
def review_queue_page(request: Request, db: Session = Depends(get_db)):
    items = list_review_queue(db, ReviewStatus.PENDING)
    return templates.TemplateResponse(
        request, "review_queue.html", {"items": [{"decision_id": i.decision_id, "reason": i.reason.value, "status": i.status.value, "created_at": i.created_at} for i in items]}
    )


@router.get("/decisions/{decision_id}")
def decision_detail_page(decision_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    decision = get_decision(db, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")

    pending_review_items = [i for i in decision.review_items if i.status == ReviewStatus.PENDING]
    disclosures = list_disclosures(db, decision_id)

    return templates.TemplateResponse(
        request,
        "decision_detail.html",
        {
            "decision": decision,
            "trace_result": decision.trace_result,
            "justification": decision.justification,
            "pending_review_items": pending_review_items,
            "disclosures": disclosures,
            "error": request.query_params.get("error"),
            "message": request.query_params.get("message"),
        },
    )


@router.post("/decisions/{decision_id}/resolve-review/{item_id}")
def resolve_review_page(
    decision_id: uuid.UUID,
    item_id: uuid.UUID,
    assigned_to: str = Form(...),
    resolution_notes: str = Form(...),
    db: Session = Depends(get_db),
):
    item = get_review_item(db, item_id)
    if item is None or item.decision_id != decision_id:
        raise HTTPException(status_code=404, detail="review item not found")

    resolve_review_item(db, item, assigned_to=assigned_to, resolution_notes=resolution_notes)
    db.commit()
    return RedirectResponse(url=f"/dashboard/decisions/{decision_id}?message=Review+item+resolved", status_code=303)


@router.post("/decisions/{decision_id}/disclose")
def disclose_page(
    decision_id: uuid.UUID,
    channel: str = Form(...),
    disclosed_by: str = Form(...),
    delay_owned: bool = Form(False),
    sentence_override: str = Form(""),
    customer_response: str = Form(""),
    db: Session = Depends(get_db),
):
    decision = get_decision(db, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")

    try:
        disclose_decision(
            db,
            decision,
            channel=DisclosureChannel(channel),
            disclosed_by=disclosed_by,
            delay_owned=delay_owned,
            sentence_override=sentence_override or None,
            customer_response=customer_response or None,
        )
        db.commit()
    except UnverifiedJustificationError as exc:
        db.rollback()
        return RedirectResponse(url=f"/dashboard/decisions/{decision_id}?error={exc}", status_code=303)

    return RedirectResponse(url=f"/dashboard/decisions/{decision_id}?message=Disclosure+logged", status_code=303)


@router.post("/decisions/{decision_id}/reopen")
def reopen_page(
    decision_id: uuid.UUID,
    new_evidence_json: str = Form(...),
    db: Session = Depends(get_db),
    llm_client: JustifyLLMClient = Depends(get_llm_client),
):
    decision = get_decision(db, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")

    try:
        new_evidence = json.loads(new_evidence_json)
    except json.JSONDecodeError as exc:
        return RedirectResponse(
            url=f"/dashboard/decisions/{decision_id}?error=Invalid+JSON:+{exc}", status_code=303
        )

    case = decision.case
    domain = get_domain(case.domain)
    reopen_request = create_reopen_request(db, original_decision_id=decision.id, new_evidence=new_evidence)

    new_features = {**case.input_payload, **new_evidence}
    try:
        result = run_pipeline(domain, case.category, new_features, llm_client)
    except KeyError as exc:
        db.rollback()
        return RedirectResponse(
            url=f"/dashboard/decisions/{decision_id}?error=Missing+feature:+{exc}", status_code=303
        )

    new_case = create_case(db, case.domain, case.category, new_features)
    new_decision = persist_pipeline_result(db, new_case, result)
    link_reopen_to_new_decision(db, reopen_request, new_decision.id)
    db.commit()

    return RedirectResponse(url=f"/dashboard/decisions/{new_decision.id}?message=Reopened", status_code=303)


@router.get("/disclosures")
def disclosure_ledger_page(request: Request, db: Session = Depends(get_db)):
    disclosures = list_disclosures(db)
    return templates.TemplateResponse(request, "disclosure_ledger.html", {"disclosures": disclosures})

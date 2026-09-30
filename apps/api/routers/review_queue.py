import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from apps.api.auth import require_api_key
from apps.api.deps import get_db
from apps.api.schemas import ReviewItemResponse, ReviewResolveRequest
from database.models import ReviewStatus
from database.repository import get_review_item, list_review_queue, resolve_review_item

router = APIRouter(prefix="/v1/review-queue", tags=["review-queue"])


def _to_response(item) -> dict:
    return {
        "id": item.id,
        "decision_id": item.decision_id,
        "reason": item.reason.value,
        "status": item.status.value,
        "assigned_to": item.assigned_to,
        "resolution_notes": item.resolution_notes,
        "resolved_at": item.resolved_at,
        "created_at": item.created_at,
    }


@router.get("", response_model=list[ReviewItemResponse])
def list_pending(decision_id: uuid.UUID | None = Query(default=None), db: Session = Depends(get_db)):
    items = list_review_queue(db, ReviewStatus.PENDING)
    if decision_id is not None:
        items = [item for item in items if item.decision_id == decision_id]
    return [_to_response(item) for item in items]


@router.post("/{item_id}/resolve", response_model=ReviewItemResponse, dependencies=[Depends(require_api_key)])
def resolve(item_id: uuid.UUID, body: ReviewResolveRequest, db: Session = Depends(get_db)):
    item = get_review_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="review item not found")
    if item.status == ReviewStatus.RESOLVED:
        raise HTTPException(status_code=409, detail="review item already resolved")

    resolve_review_item(db, item, assigned_to=body.assigned_to, resolution_notes=body.resolution_notes)
    db.commit()
    db.refresh(item)
    return _to_response(item)

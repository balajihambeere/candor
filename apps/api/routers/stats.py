from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas import StatsSummaryResponse
from database.repository import get_summary_stats

router = APIRouter(prefix="/v1/stats", tags=["stats"])


@router.get("/summary", response_model=StatsSummaryResponse)
def summary(db: Session = Depends(get_db)):
    return get_summary_stats(db)

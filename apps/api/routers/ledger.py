from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas import DisclosureResponse
from database.repository import list_disclosures

router = APIRouter(prefix="/v1/disclosures", tags=["disclose"])


@router.get("", response_model=list[DisclosureResponse])
def read_all_disclosures(db: Session = Depends(get_db)):
    """The global disclosure ledger — every explanation given, to whom,
    when, and whether it held up, across every decision.
    """
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
        for d in list_disclosures(db)
    ]

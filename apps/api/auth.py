"""API-key auth. This is a machine-to-machine decision service other
systems call (the way Zuxpert's return-eligibility check would call it),
not an end-user login system — so it's a shared-secret header, not sessions
or OAuth. Applied only to write endpoints; reads (including the review
queue and disclosure ledger) stay open so a dashboard or another internal
service can query them freely.
"""

from fastapi import Header, HTTPException, status

from config.settings import get_settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not x_api_key or x_api_key not in settings.api_key_set:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or missing API key")

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from apps.api.observability import install_observability
from apps.api.rate_limit import limiter
from apps.api.routers import decisions, disclosures, ledger, review_queue
from database.session import get_engine

app = FastAPI(
    title="Candor",
    description=(
        "A Decide/Trace/Justify/Disclose engine for verified, disclosed AI decision explanations."
    ),
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

install_observability(app)

app.include_router(decisions.router)
app.include_router(disclosures.router)
app.include_router(ledger.router)
app.include_router(review_queue.router)


@app.exception_handler(RuntimeError)
def runtime_error_handler(request: Request, exc: RuntimeError):
    # Currently only raised by get_llm_client when ANTHROPIC_API_KEY is
    # unset — a configuration problem, not a client error or a bug.
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/health", tags=["health"])
def health():
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "unreachable"

    overall = "ok" if db_status == "ok" else "degraded"
    return {"status": overall, "database": db_status}

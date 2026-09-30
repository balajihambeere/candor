"""Structured logging, request correlation, and metrics. Deliberately plain:
one middleware, one counter, one histogram, one /metrics endpoint in
Prometheus text format — enough for someone operating this in production to
see request volume, latency, and error rate without pulling in a bigger
observability stack than a reference implementation warrants.
"""

import logging
import time
import uuid

import structlog
from fastapi import FastAPI, Request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from config.settings import get_settings

REQUEST_COUNT = Counter(
    "candor_requests_total", "Total HTTP requests", ["method", "path", "status_code"]
)
REQUEST_LATENCY = Histogram(
    "candor_request_duration_seconds", "Request latency in seconds", ["method", "path"]
)


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.log_level)),
        logger_factory=structlog.PrintLoggerFactory(),
    )


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)
        log = structlog.get_logger("candor.request")

        start = time.perf_counter()
        # Use the matched route template (e.g. "/v1/decisions/{decision_id}")
        # rather than the raw path, so metrics don't explode one series per UUID.
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration = time.perf_counter() - start
            path_template = request.scope.get("route").path if request.scope.get("route") else request.url.path
            status_code = response.status_code if response is not None else 500

            REQUEST_COUNT.labels(method=request.method, path=path_template, status_code=status_code).inc()
            REQUEST_LATENCY.labels(method=request.method, path=path_template).observe(duration)

            log.info(
                "request_completed",
                method=request.method,
                path=path_template,
                status_code=status_code,
                duration_ms=round(duration * 1000, 2),
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id
            structlog.contextvars.clear_contextvars()


def install_observability(app: FastAPI) -> None:
    configure_logging()
    app.add_middleware(ObservabilityMiddleware)

    @app.get("/metrics", tags=["health"], include_in_schema=False)
    def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

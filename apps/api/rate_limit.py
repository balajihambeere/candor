"""Rate limiting for the two endpoints that call Anthropic (create_decision,
reopen) — the actual cost/abuse surface. Read endpoints and the review-queue
resolve action aren't rate limited; they don't touch a paid external API.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from config.settings import get_settings

limiter = Limiter(key_func=get_remote_address)


def llm_endpoint_limit() -> str:
    return f"{get_settings().rate_limit_per_minute}/minute"

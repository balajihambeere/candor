from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.orm import Session

from config.settings import get_settings
from database.session import get_db as _get_db
from packages.candor.llm import AnthropicJustifyClient, JustifyLLMClient


def get_db() -> Generator[Session, None, None]:
    yield from _get_db()


@lru_cache
def _anthropic_client() -> AnthropicJustifyClient:
    return AnthropicJustifyClient()


def get_llm_client() -> JustifyLLMClient:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Justify needs it to generate customer-facing sentences."
        )
    return _anthropic_client()

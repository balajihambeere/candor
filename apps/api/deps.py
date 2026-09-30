from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.orm import Session

from database.session import get_db as _get_db
from packages.candor.llm import JustifyLLMClient, build_llm_client


def get_db() -> Generator[Session, None, None]:
    yield from _get_db()


@lru_cache
def _cached_llm_client() -> JustifyLLMClient:
    return build_llm_client()


def get_llm_client() -> JustifyLLMClient:
    return _cached_llm_client()

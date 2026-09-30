from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://candor:candor@localhost:5432/candor"

    llm_provider: str = "anthropic"
    """Which LLM backs the Justify stage: "anthropic" or "openai". Decide and
    Trace never call an LLM regardless of this setting."""

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"
    anthropic_timeout_seconds: float = 20.0
    anthropic_max_retries: int = 2

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 20.0
    openai_max_retries: int = 2

    api_keys: str = "dev-local-key"
    """Comma-separated list of accepted API keys."""

    rate_limit_per_minute: int = 120

    log_level: str = "INFO"

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()

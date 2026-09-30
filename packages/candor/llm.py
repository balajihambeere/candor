"""The only network-calling, non-deterministic piece of the pipeline.
Decide and Trace never touch an LLM; Justify's sentence-writing step is the
one place the pipeline uses one, and only over the Trace-verified record —
never the raw case.
"""

from typing import Protocol

from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import get_settings

JUSTIFY_SYSTEM_PROMPT = """You write one sentence explaining an automated decision to the person it affected.

You will be given a JSON list of reasons that caused a denial. Each reason has a plain-language description and, for some reasons, exact numeric values that were compared.

Rules, without exception:
1. Address every reason in the list. Do not summarize multiple reasons into a single vague phrase like "did not meet our policy requirements" — name each one specifically.
2. If a reason includes exact numeric values, state them exactly (e.g. "nine days after delivery, two days past our seven-day window"). Never paraphrase a number into a vague phrase like "close to the limit" or "just under the threshold".
3. Never use internal jargon: no rule IDs, no words like "determinative" or "non-determinative", no field names.
4. Write directly to the customer ("your return"), in plain, respectful language.
5. If more than one reason is present, say plainly that each one independently would have led to the same result, if that is true.
6. Output ONLY the sentence. No preamble, no quotation marks, no explanation of what you did.
"""


class JustifyLLMClient(Protocol):
    def generate_sentence(self, reasons_payload: list[dict]) -> str: ...


class AnthropicJustifyClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = Anthropic(api_key=settings.anthropic_api_key, timeout=settings.anthropic_timeout_seconds)
        self._model = settings.anthropic_model
        self._max_retries = settings.anthropic_max_retries

    def generate_sentence(self, reasons_payload: list[dict]) -> str:
        return self._call_with_retry(reasons_payload)

    def _call_with_retry(self, reasons_payload: list[dict]) -> str:
        @retry(stop=stop_after_attempt(self._max_retries + 1), wait=wait_exponential(multiplier=1, max=8))
        def _call() -> str:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=300,
                system=JUSTIFY_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": str(reasons_payload)}],
            )
            return "".join(block.text for block in response.content if block.type == "text").strip()

        return _call()

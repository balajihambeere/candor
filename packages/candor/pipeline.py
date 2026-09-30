"""Runs Decide -> Trace -> Justify as one pass over a case. Pure and
domain-agnostic — no database, no HTTP. Persisting the result and deciding
whether it needs a human (review queue) is the API layer's job
(apps/api + database/repository.py): the pipeline proves what it can and
can't verify; what happens to an unverifiable case is a policy decision,
not the pipeline's own.
"""

from dataclasses import dataclass

from domains.registry import DomainConfig
from packages.candor.decide import decide
from packages.candor.justify import justify
from packages.candor.llm import JustifyLLMClient
from packages.candor.models import DecisionRecord, JustificationResult, TraceOutcome
from packages.candor.trace import trace


@dataclass(frozen=True)
class PipelineResult:
    decision: DecisionRecord
    trace_outcome: TraceOutcome
    justification: JustificationResult

    @property
    def needs_review(self) -> bool:
        from packages.candor.models import JustificationStatus

        return self.justification.status is JustificationStatus.FAILED_REVIEW


def run_pipeline(
    domain: DomainConfig, category: str, features: dict, llm_client: JustifyLLMClient
) -> PipelineResult:
    decision = decide(category, features, domain.evaluate_case)
    trace_outcome = trace(category, features, decision, domain.evaluate_case, domain.passing_patch)
    justification = justify(decision, trace_outcome, llm_client, domain.justify_metadata)
    return PipelineResult(decision=decision, trace_outcome=trace_outcome, justification=justification)

"""Registry of domains Candor can explain decisions for. Each domain plugs
into the engine by supplying three things: how to evaluate a case into
RuleResults, how to neutralize a given rule for Trace's counterfactual
probes, and how Justify should talk about each rule. The engine
(packages/candor) never imports a domain directly — only through this shape.
"""

from dataclasses import dataclass

from packages.candor.decide import RuleEvaluator
from packages.candor.trace import PassingPatchResolver


@dataclass(frozen=True)
class DomainConfig:
    name: str
    evaluate_case: RuleEvaluator
    passing_patch: PassingPatchResolver
    justify_metadata: dict[str, dict]


def _load_returns_domain() -> DomainConfig:
    from domains.returns.catalog import JUSTIFY_METADATA, evaluate_case, passing_patch

    return DomainConfig(
        name="returns",
        evaluate_case=evaluate_case,
        passing_patch=passing_patch,
        justify_metadata=JUSTIFY_METADATA,
    )


DOMAINS: dict[str, DomainConfig] = {
    "returns": _load_returns_domain(),
}


class UnknownDomainError(ValueError):
    pass


def get_domain(name: str) -> DomainConfig:
    domain = DOMAINS.get(name)
    if domain is None:
        raise UnknownDomainError(f"no domain registered: {name!r}")
    return domain

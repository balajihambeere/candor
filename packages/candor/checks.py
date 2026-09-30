"""Sentence-level checks for Justify's output.

Trace verifies the *record* is faithful. These check the *sentence* is
faithful to that record — a separate property, because a faithful record can
still produce an unfaithful sentence (a two-reason record, summarized down
to "did not meet our return policy requirements", passes
faithfulness-of-record and still says nothing). Both checks are plain
pattern-matching, deliberately: the whole point of Decide/Trace was to stop
trusting a model's account of itself, and a second model grading the first
model's sentence would just reintroduce the same problem one layer up.
"""

import re

from packages.candor.models import RuleResult

VAGUE_HEDGE_PHRASES = [
    "just under",
    "just over",
    "close to",
    "well within",
    "roughly",
    "approximately",
    "around the",
    "a bit over",
    "a bit under",
    "more or less",
]

JARGON_TERMS = [
    "non-determinative",
    "determinative",
    "rule evaluated",
    "evaluated_value",
    "threshold:",
    "counterfactual",
    "trace confirmed",
]

_NUMBER_WORDS = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
    11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen",
    16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty",
}


def _number_mentioned(sentence_lower: str, value) -> bool:
    if isinstance(value, bool):
        return True  # booleans have no numeral form to check
    try:
        as_int = int(value)
    except (TypeError, ValueError):
        return False
    if str(as_int) in sentence_lower:
        return True
    word = _NUMBER_WORDS.get(as_int)
    return bool(word) and word in sentence_lower


class FaithfulnessResult:
    def __init__(self, passed: bool, issues: list[str]):
        self.passed = passed
        self.issues = issues


def check_faithfulness(
    sentence: str, failing_reasons: list[RuleResult], justify_metadata: dict[str, dict]
) -> FaithfulnessResult:
    issues: list[str] = []
    lowered = sentence.lower()

    for phrase in VAGUE_HEDGE_PHRASES:
        if phrase in lowered:
            issues.append(f"vague hedge phrase present: {phrase!r}")

    for reason in failing_reasons:
        meta = justify_metadata.get(reason.rule_id)
        if meta is None:
            issues.append(f"no justify metadata registered for {reason.rule_id}")
            continue

        if not any(kw in lowered for kw in meta["keywords"]):
            issues.append(f"sentence never addresses {reason.rule_id} (missing all of {meta['keywords']})")

        if meta["requires_exact_numbers"]:
            if not _number_mentioned(lowered, reason.evaluated_value):
                issues.append(f"sentence omits the exact evaluated value for {reason.rule_id}")
            if not _number_mentioned(lowered, reason.threshold):
                issues.append(f"sentence omits the exact threshold for {reason.rule_id}")

    return FaithfulnessResult(passed=not issues, issues=issues)


class PlainLanguageResult:
    def __init__(self, passed: bool, issues: list[str]):
        self.passed = passed
        self.issues = issues


def check_plain_language(sentence: str, failing_reasons: list[RuleResult]) -> PlainLanguageResult:
    issues: list[str] = []
    lowered = sentence.lower()

    for term in JARGON_TERMS:
        if term in lowered:
            issues.append(f"internal jargon present: {term!r}")

    for reason in failing_reasons:
        if reason.rule_id.lower() in lowered:
            issues.append(f"raw rule id leaked into sentence: {reason.rule_id!r}")

    # A bare, unqualified field-style token (all caps with hyphens) reads as
    # an internal identifier even if it isn't a known rule id.
    if re.search(r"\b[A-Z]{3,}-[A-Z0-9-]+\b", sentence):
        issues.append("sentence contains what looks like an internal identifier")

    return PlainLanguageResult(passed=not issues, issues=issues)

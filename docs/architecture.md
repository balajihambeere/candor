# Architecture

## System overview

```text
                    ┌─────────────────────────────────────────────┐
                    │                 FastAPI app                  │
                    │                                               │
  caller ──POST──▶  │  /v1/decisions  ──▶  run_pipeline()           │
  (e.g. Zuxpert's   │       │                  │                    │
  return-eligibility│       │           ┌──────┴──────┐             │
  service)          │       │           │             │             │
                    │       │        decide()      trace()          │
                    │       │      (deterministic)  (deterministic, │
                    │       │                         counterfactual│
                    │       │                         replay)       │
                    │       │             │             │           │
                    │       │             └──────┬──────┘           │
                    │       │                 justify()             │
                    │       │              (Claude call +           │
                    │       │            faithfulness/plain-        │
                    │       │              language checks)         │
                    │       ▼                                       │
                    │  persist to Postgres:                         │
                    │  cases, decisions, trace_results,              │
                    │  justifications, review_queue (if unverified)  │
                    │                                                │
                    │  /v1/decisions/{id}/disclose  ──▶ disclosures  │
                    │  /v1/decisions/{id}/reopen    ──▶ fresh pass,  │
                    │                                    linked via  │
                    │                                 reopen_requests│
                    │                                                │
                    │  /dashboard/*  (HTTP Basic) ──▶ same DB, same  │
                    │                                  service layer │
                    └─────────────────────────────────────────────┘
```

## Why one service, not several

The core architecture lesson (from the table/templates failures) is that
Decide, Trace, and Justify have to run as one pipeline with a shared, typed
handoff — a table exposing Decide's raw record and a template library
guessing at Justify's sentence both failed for the same reason: splitting
the stages apart let each one drift from what the others had actually
verified. A single Python process with three plain function calls
(`decide()` → `trace()` → `justify()`) keeps that handoff a type, not a
network call or a queue message that can silently drop a field.

## The engine is domain-agnostic; the domain is injected

`packages/candor/` never imports `domains/returns/`. Every stage takes the
domain's behavior as parameters:

- `decide(category, features, evaluate_case)` — `evaluate_case` is the
  domain's rule catalog.
- `trace(category, features, decision, evaluate_case, passing_patch)` —
  `passing_patch` is how the domain says "here's what would make this rule
  pass," used to neutralize every *other* failing reason when testing
  whether one reason is independently sufficient.
- `justify(decision, trace_outcome, llm_client, justify_metadata)` —
  `justify_metadata` is the domain's vocabulary: plain-language
  descriptions, which rule topics require exact numbers vs. qualitative
  description, and the keywords the faithfulness checker uses to confirm a
  sentence actually addresses a given rule.

`domains/registry.py` is the only place that wires a concrete domain
(`returns`) to these three injection points. Adding a second domain means
writing a new `domains/<name>/` package with the same three exports — the
engine itself doesn't change.

## Trace's counterfactual test, precisely

For a failing reason `R`, Trace asks: *if every other failing reason were
fixed, would `R` alone still cause a denial?* It builds a counterfactual
feature set by patching every *other* currently-failing reason to a passing
value (via the domain's `passing_patch`), re-evaluates the case, and checks
whether the verdict is still `denied` **and** `R` itself is still failing
under that counterfactual. If both hold, `R` is confirmed independently
sufficient — added to `determinative_reasons`.

This is deliberately the *sufficiency* test, not a *necessity* test
(flip `R` alone, holding others as originally evaluated). The necessity
test fails on Reema's case: flipping the window alone, with the
defect-confidence still low, still denies — which doesn't mean the window
isn't a real, independent cause; it means a single-cause framing was
already wrong. The sufficiency test is what correctly recovers "both facts
were independently sufficient."

If the domain doesn't know how to neutralize a rule (`passing_patch`
returns `None`), or a probe comes back ambiguous, Trace marks the whole
record `UNRESOLVED` rather than guessing — the case goes to the review
queue, never disclosed.

## Justify's two checks are separate from Trace's

Trace verifies the *record*. A faithful record can still produce an
unfaithful *sentence* (a two-reason record, summarized into "did not meet
our return policy requirements"). `packages/candor/checks.py` runs two
independent, rule-based checks on the generated sentence:

- **Faithfulness** — every failing reason's topic must be addressed
  (keyword match against domain-supplied metadata); reasons flagged
  `requires_exact_numbers` (day/count rules) must have their exact
  evaluated value and threshold present in the sentence; a fixed blocklist
  of vague-hedge phrases ("just under", "close to", "roughly", …) always
  fails the check.
- **Plain language** — a blocklist of internal jargon ("determinative",
  "non-determinative", raw rule IDs) and a regex for anything that looks
  like an internal identifier token.

Both checks are plain pattern-matching on purpose: using a second model to
grade the first model's sentence would reintroduce the same
faithfulness risk Decide/Trace exist to eliminate.

## The boundary line is not generated

`BOUNDARY_LINE` in `packages/candor/justify.py` is a fixed string, appended
deterministically — never asked of the LLM. This is the concrete fix for
**False Clarity**: a verified, faithful sentence about *this decision* can
still imply it resolved a different, adjacent question (is the policy
fair, could this have been prevented). Generating the boundary line would
risk the same blurring this design explicitly guards against.

## Data model

See `database/models.py`. One table per pipeline artifact
(`decisions`, `trace_results`, `justifications`, `disclosures`), plus
`review_queue` (anything Trace or Justify couldn't verify) and
`reopen_requests` (links a corrected submission's new decision back to the
original one it corrects).

## Deployment shape

Two containers: `api` (this FastAPI app, serving both the JSON API and the
server-rendered dashboard) and `db` (Postgres). See `docker-compose.yml` and
`docs/operations.md`.

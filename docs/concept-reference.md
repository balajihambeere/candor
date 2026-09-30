# Concept Reference

Where every core concept in the Decide/Trace/Justify/Disclose pipeline is
actually implemented, and the test that proves it. Status terms:
**SPECIFIED** (a defined requirement of the design), **ENGINEERING-DECISION**
(chosen during implementation, not otherwise mandated), **ASSUMPTION**
(required because the design didn't specify it).

| Concept | Application Component | Implementation | Test |
|---|---|---|---|
| Black Box Verdict (a correct decision nobody can check) | The problem the whole pipeline exists to solve | N/A — motivation, not a component | — |
| False Clarity (a verified answer to the wrong question) | Fixed boundary line | `packages/candor/justify.py::BOUNDARY_LINE` | `tests/golden/test_worked_scenarios.py::TestIndoreCase` |
| Decide — structured, multi-reason record, captured in one pass | Decide stage | `packages/candor/decide.py` | `tests/unit/test_decide.py` |
| A decision can have >1 independently sufficient reason | `DecisionRecord.reasons` (not a single "determinative" field) | `packages/candor/models.py::DecisionRecord` | `tests/unit/test_trace.py::test_reema_case_both_reasons_independently_sufficient` |
| Post-hoc explanation of a past decision is unreliable | Design constraint: Justify only ever runs on a Trace-*verified* record, never asked to explain a past decision from scratch | `packages/candor/justify.py` (guard on `trace_outcome.verification_status`) | `tests/unit/test_justify.py::TestGuardrails::test_unresolved_trace_never_calls_the_llm` |
| Raw-context capture is honest but unreadable/unaffordable at scale | Decide never stores raw case context — only the structured record | `packages/candor/decide.py` (signature takes `features: dict`, returns typed `RuleResult`s only) | `tests/unit/test_decide.py` |
| Trace — counterfactual verification of which reasons are genuinely determinative | Trace stage | `packages/candor/trace.py` | `tests/unit/test_trace.py` |
| Unverifiable records are never disclosed, routed to a human instead | `VerificationStatus.UNRESOLVED` → `review_queue` | `database/repository.py::_review_reason_for`, `persist_pipeline_result` | `tests/integration/test_repository.py::test_failed_faithfulness_routes_to_review_queue_not_disclosure` |
| A raw record/table is honest but not an answer | Rejected design, documented as the reason Justify exists as its own stage | `packages/candor/justify.py` docstring | — (design rationale; the rejection itself isn't a runtime component) |
| A pre-written template library doesn't scale to real rule combinations | Rejected design; Justify generates fresh every time instead | `packages/candor/justify.py` (no template lookup) | `tests/unit/test_justify.py::test_single_cause_template_that_drops_the_second_reason_is_rejected` |
| Justify — one fresh sentence from the verified record only | Justify stage | `packages/candor/justify.py` | `tests/unit/test_justify.py`, `tests/golden/test_worked_scenarios.py` |
| Justify must name every reason, not summarize | Faithfulness check, keyword coverage | `packages/candor/checks.py::check_faithfulness` | `tests/unit/test_justify.py::test_omission_by_summary_is_rejected` |
| Justify must state exact numbers, never round into vague language | Faithfulness check, vague-hedge blocklist + exact-number requirement | `packages/candor/checks.py::VAGUE_HEDGE_PHRASES`, `_number_mentioned` | `tests/unit/test_justify.py::test_vague_rounding_is_rejected` |
| Justify must avoid internal jargon | Plain-language check | `packages/candor/checks.py::check_plain_language` | `tests/unit/test_justify.py::test_internal_jargon_leak_is_rejected` |
| Every pipeline needs a failure path — unresolved cases queue for a human | Review queue | `database/models.py::ReviewItem`, `apps/api/routers/review_queue.py` | `tests/integration/test_repository.py`, `tests/integration/test_api.py::test_failed_review_case_appears_in_review_queue_and_resolves` |
| A verified, faithful sentence can still not answer the real question (False Clarity) | Fixed, separately-generated boundary line, never blurred into the sentence itself | `packages/candor/justify.py::BOUNDARY_LINE` | `tests/golden/test_worked_scenarios.py::TestIndoreCase::test_final_sale_denial_carries_the_boundary_line` |
| Disclose — the actual delivery, resists full automation | Disclosure ledger endpoint + dashboard checklist | `apps/api/routers/disclosures.py`, `apps/dashboard/app/decisions/[id]/page.tsx` | `tests/integration/test_disclose_and_reopen.py` |
| Never disclose an unverified justification automatically | `UnverifiedJustificationError`, requires human `sentence_override` | `database/repository.py::disclose_decision` | `tests/integration/test_disclose_and_reopen.py::test_cannot_disclose_an_unverified_justification_without_a_reviewed_sentence` |
| "Own the delay before the answer" | `delay_owned` field on every disclosure record; dashboard checklist text | `database/models.py::Disclosure.delay_owned` | `tests/golden/test_worked_scenarios.py::test_uttaras_disclosure_call` |
| A skeptical customer's own counterfactual question must be answerable on demand | Counterfactual endpoint | `apps/api/routers/decisions.py::counterfactual` | `tests/integration/test_api.py::test_reemas_own_counterfactual_question` |
| New evidence on a decided case must re-enter the pipeline, not vanish | Reopen endpoint, linked via `reopen_requests` | `apps/api/routers/disclosures.py::reopen` | `tests/integration/test_disclose_and_reopen.py::test_reopen_with_sharper_photo_still_denied_by_window_alone` |
| The disclosure ledger — "every explanation given, to whom, when, whether it held up" | `disclosures` table + global/per-decision ledger pages | `database/models.py::Disclosure`, `apps/dashboard/app/disclosures/page.tsx` | `tests/integration/test_disclose_and_reopen.py::test_global_disclosure_ledger_lists_across_decisions` |
| Cost of wrongness vs. cost of unexplainedness | **Not implemented** — needs support-ticket/CSAT/resubmission data this project has no source for; fabricating it would violate the no-invented-facts rule | — | — |
| A ritual question ("could we answer this to her face, in one sentence?") | Human discipline, surfaced as on-screen text in the dashboard's Disclose section, not a runtime check | `apps/dashboard/app/decisions/[id]/page.tsx` | manual — this is explicitly a judgment call, not a checkable property |

## Engineering decisions

| Decision | Why |
|---|---|
| Deterministic rule engine for Decide (not an LLM) | The return-eligibility service was already rule-based (date comparisons, threshold checks); Decide's innovation is capturing structure, not changing how the decision is made |
| Trace's *sufficiency* test (not a *necessity* test) | A necessity test — flipping one reason alone, holding the other's original failing value — never flips a multi-cause verdict, so it can't recover "both facts were independently sufficient." The sufficiency test (neutralize every *other* reason, keep this one at its original value) does. See `docs/architecture.md`. |
| 5 concrete rules for the `returns` domain (window, defect-exception, footwear-wear, final-sale, bulk-order) | These five are fully specified in the worked scenarios; a mention of "five other category-specific rules" exists without naming them all — those aren't implemented, since inventing their specifics would violate the no-guessing rule |
| API-key auth for write endpoints, signed session cookie for the dashboard login | Two different trust boundaries: a calling service (Zuxpert) vs. a human ops user |
| Next.js dashboard as a separate service, not server-rendered from the API process | Server Components/Actions give a typed, no-client-JS-required UI without a hand-rolled REST client layer; the API key stays server-side and never reaches the browser |

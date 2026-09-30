# Candor

Cuts the time between an automated denial and a verified, checkable reason
a customer will actually believe — from days of specialist reconstruction
(or a public complaint) down to under two seconds, with every explanation
checked before it ships, not after.

**Why it matters:** a correct decision nobody outside engineering can
explain costs a company twice — once in the rare cases it's actually
wrong, and far more often in the agent-hours spent re-litigating decisions
that were already right, because nobody could say why fast enough to be
believed. Candor closes that gap for any rule-based decision service: it
captures the real reason at decision time, verifies it's genuinely what
drove the outcome (not a guess dressed as an explanation), writes it in
one honest sentence, and keeps a permanent record of what was told to
whom. Unverifiable or unclear cases are automatically held back for a
human — nothing unchecked ever reaches a customer.

**A production reference implementation**, worked through zUdyog
Fashion's return-eligibility system.

## How it works

A correct automated decision that nobody outside engineering can check is
a failure mode of its own (**Black Box Verdict**), distinct from the
decision being wrong — and a verified, faithful explanation can *still*
fail if it answers a narrower question than the one the person actually
asked (**False Clarity**). Candor implements the four-stage fix:

1. **Decide** — capture the verdict and every rule evaluated to reach it, in
   one deterministic pass. No free text, no post-hoc guess.
2. **Trace** — verify the record by counterfactual replay: for each failing
   reason, neutralize every *other* failing reason and confirm this one
   alone still causes the denial. Unresolvable cases are never disclosed.
3. **Justify** — turn the *verified* record into one customer-facing
   sentence (via Claude), checked for faithfulness (names every reason,
   exact numbers) and plain language (no internal jargon). A fixed boundary
   line, generated separately, keeps a verified answer from implying it
   resolved a question it never heard.
4. **Disclose** — the ledger of what was actually sent to whom, when, and
   whether it held up — plus a reopen path so new evidence re-enters the
   pipeline instead of vanishing into a thread.

See `docs/concept-reference.md` for exactly where each core concept lives in
this codebase, and `docs/architecture.md` for the system design.

## Quickstart

```bash
cp .env.example .env
# fill in ANTHROPIC_API_KEY in .env — required for Justify to run

docker compose up --build
```

The API is at `http://localhost:8000` (docs at `/docs`), the dashboard at
`http://localhost:3000` (login with `DASHBOARD_USERNAME`/`DASHBOARD_PASSWORD`
from `apps/dashboard/.env` — see `apps/dashboard/.env.example`).

## Local development (without Docker)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

docker compose up -d db          # Postgres only
alembic -c database/alembic.ini upgrade head

cp .env.example .env             # then point DATABASE_URL at the db port
                                  # docker compose exposes (see docker-compose.yml)

uvicorn apps.api.main:app --reload
```

## Testing

```bash
pytest                    # unit + integration + golden (all deterministic, LLM mocked)
```

- `tests/unit/` — rules, Decide, Trace, Justify's checkers. No database, no network.
- `tests/integration/` — full API surface against a real Postgres, LLM mocked via dependency override.
- `tests/golden/` — three worked cases (Reema, Kochi, Indore) reproduced end-to-end through the live API, asserting against their actual shipped sentences.

Every automated test mocks the LLM client for determinism and cost — see
"Known limitations" below for what that does and doesn't verify.

## Architecture

Python API service (FastAPI + Postgres, Claude used only for Justify) plus
a separate Next.js dashboard that talks to it over HTTP. Full detail in
`docs/architecture.md`.

```text
packages/candor/    the engine: decide.py, trace.py, justify.py, checks.py, models.py
domains/returns/    the example domain: rules, category catalog, justify metadata
apps/api/           FastAPI app: routers, auth, rate limiting, observability
apps/dashboard/     Next.js dashboard: review queue / decision detail / disclosure ledger
database/           SQLAlchemy models, Alembic migrations, repository functions
tests/               unit / integration / golden
docs/                architecture, API reference, concept reference, operations
```

## Technology stack

| Piece | Choice | Why |
|---|---|---|
| API | Python + FastAPI | async-friendly, good fit for the LLM-orchestration step in Justify |
| Database | Postgres + SQLAlchemy + Alembic | real persistence + migrations — Decide/Trace/Justify/Disclose records are never in-memory |
| LLM | Anthropic Claude or OpenAI (`LLM_PROVIDER`), Justify only | Anthropic's own published faithfulness research motivates keeping Decide and Trace deliberately deterministic, regardless of which provider Justify uses |
| Dashboard | Next.js (App Router) + TypeScript + Tailwind CSS | Server Components for reads, Server Actions for writes — no separate REST client layer, no API key exposed to the browser |
| Auth | API key (backend write endpoints) + signed session cookie (dashboard login) | machine-to-machine service vs. a human-facing internal tool are different trust boundaries |
| Observability | structlog (JSON logs) + prometheus-client (`/metrics`) | enough to operate this without a bigger stack than a reference implementation warrants |

## Environment variables

See `.env.example` for the full list with comments. The ones that matter
most: `LLM_PROVIDER` (`anthropic` or `openai`, default `anthropic`) and that
provider's API key — without it, `POST /v1/decisions` and
`POST /v1/decisions/{id}/reopen` return `503` (Justify can't run). Everything
else (Decide, Trace, the review queue, the disclosure ledger) works without
it. Switching providers is a config change only — `packages/candor/llm.py`
exposes both `AnthropicJustifyClient` and `OpenAIJustifyClient` behind the
same `JustifyLLMClient` protocol, and `build_llm_client()` picks one from
`LLM_PROVIDER`.

## Known limitations

- **Justify's live Claude call is not exercised by the automated test
  suite.** Every test mocks the LLM client for determinism, cost, and
  no-network-in-CI. This is `UNKNOWN`, not `VERIFIED`, until a real key is
  used for a manual smoke call — see `docs/operations.md` for how to run
  one.
- **Trace's counterfactual patches are domain-owned and rule-specific**
  (`domains/returns/catalog.py`'s `passing_patch`). Adding a new domain
  means writing both the rules *and* how to neutralize each one — Trace
  will not guess; it routes to the review queue instead.
- **Disclose is partly a discipline, not a tool**: the ledger and the
  reopen path are built; the judgment of *how* to disclose (channel, tone,
  owning the delay) is surfaced to a human in the dashboard, not automated.
- A cost analysis (cost-of-wrongness vs. cost-of-unexplainedness) is
  documented as motivation in `docs/concept-reference.md`, not implemented
  as a feature — it needs support-ticket and CSAT data this project has no
  source for, and faking that data would violate the "no invented facts"
  rule this whole project is trying to demonstrate.

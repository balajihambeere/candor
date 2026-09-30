# Operations

## Deployment

```bash
cp .env.example .env
# set LLM_PROVIDER (anthropic or openai), that provider's API key, and API_KEYS

cp apps/dashboard/.env.example apps/dashboard/.env
# set DASHBOARD_USERNAME, DASHBOARD_PASSWORD, SESSION_SECRET, and
# CANDOR_API_KEY (one of the backend's API_KEYS above)
# — change all of these before deploying anywhere real, the defaults are dev-only.

docker compose up --build -d
```

This starts three containers:
- `db` — Postgres 16, with a named volume (`candor_pgdata`) so data survives restarts.
- `api` — runs `alembic upgrade head` on startup, then serves the FastAPI app on port 8000.
- `web` — the Next.js dashboard, on port 3000, talking to `api` over the compose network.

## Environment variables

See `.env.example`. Nothing has a hardcoded secret in source — verified by
grepping the codebase for common key patterns (`sk-ant`, `sk-proj`, `AKIA`,
private-key headers) before every release; none found as of this writing.

## Health and readiness

`GET /health` returns `{"status": "ok", "database": "ok"}` when the API can
reach Postgres, `{"status": "degraded", "database": "unreachable"}`
otherwise (still `200` — a load balancer should check the JSON body, not
just the status code, since a degraded-but-responding process is a
different failure mode than a dead one).

## Metrics

`GET /metrics` — Prometheus text format. `candor_requests_total` (by method,
route template, status code) and `candor_request_duration_seconds`
(histogram, by method and route template). Point a Prometheus scraper at it
directly; no extra configuration needed.

## Logs

Structured JSON to stdout via `structlog`, one line per request, tagged with
a `request_id` that's also returned as the `X-Request-ID` response header —
use it to correlate a specific customer-facing sentence back to its request
if something looks wrong in the disclosure ledger.

## Rate limits

`POST /v1/decisions` and `POST /v1/decisions/{id}/reopen` — the two
endpoints that call Claude — are rate-limited per client IP
(`RATE_LIMIT_PER_MINUTE`, default 120/min). A `429` includes a
`Retry-After`-style message in the body. Every other endpoint is
unlimited — they don't touch a paid external API.

## Running a real Justify smoke test

The automated test suite mocks the LLM client everywhere — it verifies the
*pipeline's* correctness (rules, Trace's counterfactual logic, the
faithfulness/plain-language checkers), not that a real model's output
passes those checks. To verify that end to end, with either provider:

```bash
# Anthropic (LLM_PROVIDER=anthropic, the default)
export ANTHROPIC_API_KEY=sk-ant-...

# — or — OpenAI
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...

curl -X POST localhost:8000/v1/decisions \
  -H "X-API-Key: dev-local-key" -H "Content-Type: application/json" \
  -d '{"domain":"returns","category":"defect_claim","features":{"days_since_delivery":9,"defect_confidence":0.61}}'
```

Check the response's `justification.status` — `"verified"` means the real
model call passed both checks on the first try; `"failed_review"` means it
didn't, and the case is now sitting in `GET /v1/review-queue` for a human,
exactly as designed. Either outcome is useful signal; neither should be
assumed without actually running it.

## Common failures

| Symptom | Cause | Fix |
|---|---|---|
| `503` on `POST /v1/decisions` | the configured provider's API key is unset (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`, depending on `LLM_PROVIDER`) | set it in `.env`, restart the `api` container |
| `503` mentioning "Unknown LLM_PROVIDER" | `LLM_PROVIDER` isn't `anthropic` or `openai` | fix the value in `.env` |
| `401` on any `/v1/*` write endpoint | missing/wrong `X-API-Key` header | check `API_KEYS` in `.env` matches what the caller sends |
| Dashboard redirects everything to `/login` | missing/expired session cookie, or `SESSION_SECRET` changed | log in again; a changed `SESSION_SECRET` invalidates every existing session |
| Dashboard pages show a fetch error | `web`'s `CANDOR_API_BASE_URL` can't reach `api`, or `CANDOR_API_KEY` doesn't match one of the backend's `API_KEYS` | check `apps/dashboard/.env` against the backend's `.env` |
| `409` on `POST /v1/decisions/{id}/disclose` | justification wasn't `verified` | resolve it in the review queue first, or pass `sentence_override` |
| High `justify_faithfulness_failed` rate in the review queue | Claude's sentence is dropping a reason or hedging a number | check `packages/candor/checks.py`'s issues via the review queue detail — the failing check's specific reason is logged, not just pass/fail |
| Migration fails on startup | Postgres not ready yet | `docker-compose.yml`'s `depends_on.db.condition: service_healthy` should prevent this; if it still happens, check `docker compose logs db` |

## Backup / recovery

Postgres data lives in the `candor_pgdata` named volume. Standard
`pg_dump`/`pg_restore` against the `db` container applies; there's nothing
Candor-specific about backup here — the schema is small (7 tables, all
append-mostly except `review_queue.status` and `reopen_requests`'s link).

## Rollback

Standard Alembic: `alembic -c database/alembic.ini downgrade -1` reverses
the most recent migration. There's currently one migration
(`initial_schema`), so this drops everything — fine for this reference
implementation's stage, worth revisiting once a second migration exists.

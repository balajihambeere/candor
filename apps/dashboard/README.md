# Candor Dashboard

Next.js (App Router, TypeScript, Tailwind CSS) dashboard for Candor's
review queue, decision detail, and disclosure ledger — the human-facing
counterpart to the FastAPI backend in `../..`.

## Local development

```bash
cp .env.example .env.local   # point CANDOR_API_BASE_URL at a running backend
npm install
npm run dev
```

Requires the FastAPI backend running and reachable at `CANDOR_API_BASE_URL`
(see the repo root `README.md` for bringing that up via Docker Compose).

## How auth works

Two separate credentials, two separate purposes:

- **`CANDOR_API_KEY`** — server-side only, attached to every write call this
  app makes to the backend (disclose/reopen/resolve). Never sent to the
  browser.
- **`DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD`** — gate a human logging
  into this dashboard. A successful login sets a signed, HTTP-only session
  cookie (`lib/session.ts`, HMAC-SHA256 via `SESSION_SECRET`); `proxy.ts`
  (Next.js's edge middleware convention) rejects any request without a
  valid one, redirecting to `/login`.

All mutating actions (resolve a review item, log a disclosure, reopen a
decision) are Next.js Server Actions (`lib/actions.ts`) — plain HTML forms,
no client-side JavaScript required, progressively enhanced.

## Structure

```text
app/
  login/               login form
  review-queue/        pending items needing a human
  decisions/[id]/       full decision detail: record, trace, justification,
                        resolve/disclose/reopen forms, per-decision ledger
  disclosures/          global disclosure ledger
lib/
  api.ts               server-only fetch client for the FastAPI backend
  actions.ts           Server Actions (login/logout/resolve/disclose/reopen)
  session.ts           signed session cookie (Web Crypto, edge-compatible)
  types.ts             shared TS types matching the backend's response shapes
components/            Badge, Card, Flash — small shared UI pieces
proxy.ts               Next.js 16's middleware convention; gates every
                        route except /login on a valid session cookie
```

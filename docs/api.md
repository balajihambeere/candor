# Candor API

Base URL (local): `http://localhost:8000`

All write endpoints require an API key (see [operations.md](operations.md) once
Phase 9 auth lands) via the `X-API-Key` header. `/health` and reads are open.

## `POST /v1/decisions`

Runs Decide → Trace → Justify over a case in one call.

**Request**
```json
{
  "domain": "returns",
  "category": "defect_claim",
  "features": {"days_since_delivery": 9, "defect_confidence": 0.61}
}
```

`category` determines which category-specific rule runs alongside the
universal window rule. See `domains/returns/catalog.py` for the full list
(`general`, `defect_claim`, `footwear`, `final_sale`, `bulk_order`) and the
features each one requires.

**Response `201`**
```json
{
  "id": "…",
  "case_id": "…",
  "verdict": "denied",
  "reasons": [
    {"rule_id": "WINDOW-STANDARD-01", "evaluated_value": 9, "threshold": 7, "comparator": "<=", "passed": false},
    {"rule_id": "DEFECT-EXCEPTION-02", "evaluated_value": 0.61, "threshold": 0.75, "comparator": ">=", "passed": false}
  ],
  "trace": {
    "determinative_reasons": ["WINDOW-STANDARD-01", "DEFECT-EXCEPTION-02"],
    "verification_status": "verified",
    "counterfactual_log": [ … ]
  },
  "justification": {
    "sentence": "Your return was not approved for two separate reasons: …",
    "boundary_line": "If your concern is about this specific decision, …",
    "faithfulness_check_passed": true,
    "plain_language_check_passed": true,
    "status": "verified"
  },
  "needs_review": false,
  "created_at": "…"
}
```

`needs_review: true` means Trace couldn't verify the record, or Justify's
sentence failed a check — the case has been routed to the review queue and
**must not** be shown to the customer as-is.

Errors: `422` for an unknown domain/category or a missing required feature;
`503` if `ANTHROPIC_API_KEY` isn't configured (Justify can't run).

## `GET /v1/decisions/{id}`

Returns the same shape as the `POST` response, for a previously-created
decision.

## `POST /v1/decisions/{id}/counterfactual`

Answers the question Reema asks Uttara — "if I'd sent this evidence
instead, would you have approved it?" — by re-running Decide against the
original case's features with the given overrides.

**Request**
```json
{"feature_overrides": {"defect_confidence": 0.89}}
```

**Response**
```json
{
  "original_verdict": "denied",
  "counterfactual_verdict": "denied",
  "would_flip": false,
  "counterfactual_reasons": [ … ]
}
```

## `GET /v1/review-queue`

Lists pending review items — decisions Trace couldn't verify or Justify
couldn't produce a clean sentence for.

## `POST /v1/review-queue/{id}/resolve`

**Request**
```json
{"assigned_to": "uttara", "resolution_notes": "rewrote the sentence by hand"}
```

Marks the item resolved. `409` if it's already resolved.

## `POST /v1/decisions/{id}/disclose`

Records that a justification was actually delivered to the person it's
about — the ledger Uttara starts keeping. This is the one stage that
resists automation: the endpoint records the disclosure, it doesn't decide
how or when to make it.

**Request**
```json
{
  "channel": "call",
  "disclosed_by": "uttara",
  "delay_owned": true,
  "customer_response": "That's it? That's the actual reason? Both of those?",
  "held_up": true
}
```

By default, `sentence_sent` is the justification's sentence plus its
boundary line, verbatim. If the justification's `status` is not `verified`
(Trace unresolved, or a Justify check failed), the endpoint returns `409`
unless `sentence_override` is supplied — a human-reviewed sentence, written
after resolving the case in the review queue. This is the API-level
enforcement of "never disclosed automatically."

Errors: `404` unknown decision, `422` invalid `channel`, `409` unverified
justification with no override.

## `GET /v1/decisions/{id}/disclosures`

Lists every disclosure recorded against a decision, most recent first.

## `POST /v1/decisions/{id}/reopen`

The gap Reema's own last question exposes: new evidence on an
already-decided case (her sharper photo, submitted after the fact) has to
re-enter the pipeline instead of disappearing into a thread. This endpoint
runs a **fresh** Decide → Trace → Justify pass over the original case's
features merged with `new_evidence`, persists it as a new decision, and
links it back to the original via a `reopen_requests` row.

**Request**
```json
{"new_evidence": {"defect_confidence": 0.89}}
```

**Response `201`**
```json
{
  "reopen_request_id": "…",
  "original_decision_id": "…",
  "new_decision": { "...": "same shape as POST /v1/decisions" }
}
```

Reproducing Reema's own case: submitting only her sharper photo as new
evidence still results in `"verdict": "denied"`, with
`determinative_reasons: ["WINDOW-STANDARD-01"]` — the window failure never
depended on the photo. Errors: `404` unknown decision, `422` missing
required feature, `503` if `ANTHROPIC_API_KEY` isn't configured.

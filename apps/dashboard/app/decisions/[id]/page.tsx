import { notFound } from "next/navigation";

import { ApiError, apiGet } from "@/lib/api";
import { discloseDecision, reopenDecision, resolveReviewItem } from "@/lib/actions";
import type { Decision, Disclosure, ReviewItem } from "@/lib/types";
import { Badge, statusTone, verdictTone } from "@/components/Badge";
import { Card } from "@/components/Card";
import { Flash } from "@/components/Flash";

export const dynamic = "force-dynamic";

export default async function DecisionDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ error?: string; message?: string }>;
}) {
  const { id } = await params;
  const { error, message } = await searchParams;

  let decision: Decision;
  try {
    decision = await apiGet<Decision>(`/v1/decisions/${id}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  const [pendingReviewItems, disclosures] = await Promise.all([
    apiGet<ReviewItem[]>(`/v1/review-queue?decision_id=${id}`),
    apiGet<Disclosure[]>(`/v1/decisions/${id}/disclosures`),
  ]);

  const discloseAction = discloseDecision.bind(null, id);
  const reopenAction = reopenDecision.bind(null, id);

  return (
    <div className="space-y-6">
      <Flash error={error} message={message} />

      <div>
        <h1 className="font-mono text-lg font-bold">{decision.id}</h1>
        <p className="mt-1 text-sm text-slate-500">
          <Badge tone={verdictTone(decision.verdict)}>{decision.verdict}</Badge>{" "}
          <span className="ml-2">{new Date(decision.created_at).toLocaleString()}</span>
        </p>
      </div>

      <Card title="Decide — the record">
        <table>
          <thead>
            <tr>
              <th>Rule</th>
              <th>Evaluated value</th>
              <th>Threshold</th>
              <th>Comparator</th>
              <th>Passed</th>
            </tr>
          </thead>
          <tbody>
            {decision.reasons.map((r) => (
              <tr key={r.rule_id}>
                <td className="font-mono text-xs">{r.rule_id}</td>
                <td>{String(r.evaluated_value)}</td>
                <td>{String(r.threshold)}</td>
                <td>{r.comparator}</td>
                <td>{r.passed ? "yes" : "no"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card title="Trace — verification">
        <p className="mb-3 text-sm">
          Status: <Badge tone={statusTone(decision.trace.verification_status)}>{decision.trace.verification_status}</Badge>
        </p>
        <p className="mb-1 text-sm font-medium text-slate-700">
          Determinative reasons (independently sufficient, confirmed by counterfactual replay):
        </p>
        {decision.trace.determinative_reasons.length === 0 ? (
          <p className="text-sm text-slate-500">none</p>
        ) : (
          <ul className="mb-3 list-inside list-disc text-sm">
            {decision.trace.determinative_reasons.map((ruleId) => (
              <li key={ruleId} className="font-mono text-xs">
                {ruleId}
              </li>
            ))}
          </ul>
        )}
        <details className="mt-2">
          <summary className="cursor-pointer text-xs text-slate-500">
            counterfactual log ({decision.trace.counterfactual_log.length} probes)
          </summary>
          <pre className="mt-2 overflow-x-auto rounded bg-slate-50 p-3 text-xs">
            {JSON.stringify(decision.trace.counterfactual_log, null, 2)}
          </pre>
        </details>
      </Card>

      <Card title="Justify — the sentence">
        <p className="mb-3 text-sm">
          Status: <Badge tone={statusTone(decision.justification.status)}>{decision.justification.status}</Badge>
        </p>
        {decision.justification.sentence && (
          <>
            <p className="mb-2 font-medium">{decision.justification.sentence}</p>
            {decision.justification.boundary_line && (
              <p className="mb-3 text-sm text-slate-500">{decision.justification.boundary_line}</p>
            )}
          </>
        )}
        <p className="text-xs text-slate-500">
          faithfulness: {decision.justification.faithfulness_check_passed ? "passed" : "FAILED"} · plain
          language: {decision.justification.plain_language_check_passed ? "passed" : "FAILED"}
        </p>
      </Card>

      {pendingReviewItems.length > 0 && (
        <Card title="Pending review">
          {pendingReviewItems.map((item) => (
            <div key={item.id} className="mb-4 last:mb-0">
              <p className="mb-2 text-sm">
                Reason: <Badge tone="warn">{item.reason}</Badge>
              </p>
              <form action={resolveReviewItem.bind(null, item.id, id)} className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700">Assigned to</label>
                  <input
                    name="assigned_to"
                    required
                    className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700">Resolution notes</label>
                  <textarea
                    name="resolution_notes"
                    required
                    rows={3}
                    className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
                <button
                  type="submit"
                  className="rounded bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
                >
                  Mark resolved
                </button>
              </form>
            </div>
          ))}
        </Card>
      )}

      <Card title="Disclose">
        <p className="mb-4 text-sm text-slate-500">
          Discipline before you submit this: lead with the answer, own the delay before you give it, and
          don&apos;t let a verified answer to &quot;why&quot; quietly stand in for an answer to a different
          question the customer actually asked (False Clarity).
        </p>
        <form action={discloseAction} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-slate-700">Channel</label>
            <select name="channel" className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm">
              <option value="call">call</option>
              <option value="email">email</option>
              <option value="chat">chat</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Disclosed by</label>
            <input
              name="disclosed_by"
              required
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" name="delay_owned" className="h-4 w-4" />
            Delay was owned before giving the answer
          </label>
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Sentence override
              {decision.justification.status !== "verified" ? " (required — justification was not verified)" : " (optional)"}
            </label>
            <textarea
              name="sentence_override"
              required={decision.justification.status !== "verified"}
              rows={2}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Customer response (optional)</label>
            <textarea name="customer_response" rows={2} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <button
            type="submit"
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
          >
            Log disclosure
          </button>
        </form>
      </Card>

      <Card title="Disclosure ledger for this decision">
        {disclosures.length === 0 ? (
          <p className="text-sm text-slate-500">Not yet disclosed to anyone.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Channel</th>
                <th>By</th>
                <th>When</th>
                <th>Sentence sent</th>
              </tr>
            </thead>
            <tbody>
              {disclosures.map((d) => (
                <tr key={d.id}>
                  <td>{d.channel}</td>
                  <td>{d.disclosed_by}</td>
                  <td className="text-xs text-slate-500">{new Date(d.disclosed_at).toLocaleString()}</td>
                  <td>{d.sentence_sent}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card title="Reopen with new evidence">
        <p className="mb-4 text-sm text-slate-500">
          New evidence on a decided case (a sharper photo, a corrected field) has to re-enter the
          pipeline, not vanish into a thread. This runs a fresh Decide → Trace → Justify pass and links
          it back here.
        </p>
        <form action={reopenAction} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-slate-700">
              New evidence (JSON — only the fields that changed)
            </label>
            <textarea
              name="new_evidence_json"
              required
              rows={3}
              placeholder='{"defect_confidence": 0.89}'
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 font-mono text-sm"
            />
          </div>
          <button
            type="submit"
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
          >
            Reopen
          </button>
        </form>
      </Card>
    </div>
  );
}

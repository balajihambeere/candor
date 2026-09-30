import { notFound } from "next/navigation";

import { ApiError, apiGet } from "@/lib/api";
import { discloseDecision, reopenDecision, resolveReviewItem } from "@/lib/actions";
import type { Decision, Disclosure, ReviewItem } from "@/lib/types";
import { Badge, statusTone, verdictTone } from "@/components/Badge";
import { Card } from "@/components/Card";
import { Flash } from "@/components/Flash";

export const dynamic = "force-dynamic";

const FIELD_CLASS =
  "mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100";

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

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-400 dark:text-slate-500">Decision</p>
          <h1 className="font-mono text-lg font-bold text-slate-900 dark:text-slate-100">{decision.id}</h1>
        </div>
        <div className="flex items-center gap-3">
          <Badge tone={verdictTone(decision.verdict)}>{decision.verdict}</Badge>
          <span className="text-sm text-slate-500 dark:text-slate-400">{new Date(decision.created_at).toLocaleString()}</span>
        </div>
      </div>

      <Card title="Decide" subtitle="The structured record captured at decision time">
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
                <td>
                  <Badge tone={r.passed ? "good" : "bad"}>{r.passed ? "Passed" : "Failed"}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card
        title="Trace"
        subtitle="Counterfactual verification of the record"
        action={<Badge tone={statusTone(decision.trace.verification_status)}>{decision.trace.verification_status}</Badge>}
      >
        <p className="mb-1.5 text-sm font-medium text-slate-700 dark:text-slate-300">
          Determinative reasons (independently sufficient, confirmed by counterfactual replay)
        </p>
        {decision.trace.determinative_reasons.length === 0 ? (
          <p className="text-sm text-slate-400 dark:text-slate-500">none</p>
        ) : (
          <ul className="mb-3 flex flex-wrap gap-2">
            {decision.trace.determinative_reasons.map((ruleId) => (
              <li
                key={ruleId}
                className="rounded-md bg-slate-100 px-2 py-1 font-mono text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300"
              >
                {ruleId}
              </li>
            ))}
          </ul>
        )}
        <details className="mt-2 group">
          <summary className="cursor-pointer text-xs font-medium text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300">
            Counterfactual log ({decision.trace.counterfactual_log.length} probes)
          </summary>
          <pre className="mt-2 overflow-x-auto rounded-lg border border-slate-100 bg-slate-50 p-3 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-800/60 dark:text-slate-400">
            {JSON.stringify(decision.trace.counterfactual_log, null, 2)}
          </pre>
        </details>
      </Card>

      <Card
        title="Justify"
        subtitle="Customer-facing sentence generated from the verified record"
        action={<Badge tone={statusTone(decision.justification.status)}>{decision.justification.status}</Badge>}
      >
        {decision.justification.sentence && (
          <div className="mb-3 rounded-lg border border-slate-100 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-800/60">
            <p className="font-medium text-slate-900 dark:text-slate-100">{decision.justification.sentence}</p>
            {decision.justification.boundary_line && (
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{decision.justification.boundary_line}</p>
            )}
          </div>
        )}
        <div className="flex flex-wrap gap-2">
          <Badge tone={decision.justification.faithfulness_check_passed ? "good" : "bad"}>
            Faithfulness {decision.justification.faithfulness_check_passed ? "passed" : "FAILED"}
          </Badge>
          <Badge tone={decision.justification.plain_language_check_passed ? "good" : "bad"}>
            Plain language {decision.justification.plain_language_check_passed ? "passed" : "FAILED"}
          </Badge>
        </div>
      </Card>

      {pendingReviewItems.length > 0 && (
        <Card title="Pending review" subtitle={`${pendingReviewItems.length} item${pendingReviewItems.length === 1 ? "" : "s"} need human resolution`}>
          {pendingReviewItems.map((item, i) => (
            <div key={item.id} className={i > 0 ? "mt-5 border-t border-slate-100 pt-5 dark:border-slate-800" : ""}>
              <p className="mb-3 text-sm">
                Reason: <Badge tone="warn">{item.reason}</Badge>
              </p>
              <form action={resolveReviewItem.bind(null, item.id, id)} className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Assigned to</label>
                  <input name="assigned_to" required className={FIELD_CLASS} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Resolution notes</label>
                  <textarea name="resolution_notes" required rows={3} className={FIELD_CLASS} />
                </div>
                <button
                  type="submit"
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700"
                >
                  Mark resolved
                </button>
              </form>
            </div>
          ))}
        </Card>
      )}

      <Card title="Disclose" subtitle="Deliver the explanation and log it to the ledger">
        <p className="mb-4 rounded-lg border border-amber-100 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300">
          Discipline before you submit this: lead with the answer, own the delay before you give it, and
          don&apos;t let a verified answer to &quot;why&quot; quietly stand in for an answer to a different
          question the customer actually asked (False Clarity).
        </p>
        <form action={discloseAction} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Channel</label>
            <select name="channel" className={FIELD_CLASS}>
              <option value="call">call</option>
              <option value="email">email</option>
              <option value="chat">chat</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Disclosed by</label>
            <input name="disclosed_by" required className={FIELD_CLASS} />
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input
              type="checkbox"
              name="delay_owned"
              className="h-4 w-4 rounded border-slate-300 bg-white text-indigo-600 dark:border-slate-700 dark:bg-slate-900"
            />
            Delay was owned before giving the answer
          </label>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
              Sentence override
              {decision.justification.status !== "verified" ? " (required — justification was not verified)" : " (optional)"}
            </label>
            <textarea
              name="sentence_override"
              required={decision.justification.status !== "verified"}
              rows={2}
              className={FIELD_CLASS}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Customer response (optional)</label>
            <textarea name="customer_response" rows={2} className={FIELD_CLASS} />
          </div>
          <button
            type="submit"
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700"
          >
            Log disclosure
          </button>
        </form>
      </Card>

      <Card title="Disclosure ledger" subtitle="History for this decision">
        {disclosures.length === 0 ? (
          <p className="text-sm text-slate-400 dark:text-slate-500">Not yet disclosed to anyone.</p>
        ) : (
          <ul className="space-y-3">
            {disclosures.map((d) => (
              <li key={d.id} className="rounded-lg border border-slate-100 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-800/60">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-sm">
                    <Badge tone="neutral">{d.channel}</Badge>
                    <span className="font-medium text-slate-700 dark:text-slate-300">{d.disclosed_by}</span>
                  </div>
                  <span className="text-xs text-slate-400 dark:text-slate-500">{new Date(d.disclosed_at).toLocaleString()}</span>
                </div>
                <p className="mt-3 border-l-2 border-slate-200 pl-3 text-sm text-slate-600 dark:border-slate-800 dark:text-slate-400">
                  {d.sentence_sent}
                </p>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Reopen" subtitle="Re-enter the pipeline with new evidence">
        <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
          New evidence on a decided case (a sharper photo, a corrected field) has to re-enter the
          pipeline, not vanish into a thread. This runs a fresh Decide → Trace → Justify pass and links
          it back here.
        </p>
        <form action={reopenAction} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
              New evidence (JSON — only the fields that changed)
            </label>
            <textarea
              name="new_evidence_json"
              required
              rows={3}
              placeholder='{"defect_confidence": 0.89}'
              className={`${FIELD_CLASS} font-mono`}
            />
          </div>
          <button
            type="submit"
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700"
          >
            Reopen
          </button>
        </form>
      </Card>
    </div>
  );
}

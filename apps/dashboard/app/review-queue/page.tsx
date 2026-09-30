import Link from "next/link";

import { apiGet } from "@/lib/api";
import type { ReviewItem } from "@/lib/types";
import { Badge } from "@/components/Badge";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ArrowRightIcon, InboxZeroIcon } from "@/components/icons";

export const dynamic = "force-dynamic";

export default async function ReviewQueuePage() {
  const items = await apiGet<ReviewItem[]>("/v1/review-queue");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Review Queue</h1>
        <p className="mt-1.5 max-w-2xl text-sm text-slate-500">
          Every case here failed a check the pipeline runs on itself — Trace couldn&apos;t verify a
          reason, or Justify&apos;s sentence didn&apos;t pass faithfulness or plain language. Nothing here
          has been disclosed to anyone yet.
        </p>
      </div>

      <Card
        title="Pending"
        subtitle={`${items.length} case${items.length === 1 ? "" : "s"} waiting on human review`}
        action={<Badge tone={items.length === 0 ? "good" : "warn"}>{items.length === 0 ? "All clear" : "Needs attention"}</Badge>}
      >
        {items.length === 0 ? (
          <EmptyState
            icon={<InboxZeroIcon className="h-8 w-8" />}
            title="Nothing pending"
            description="Every recent decision was Trace-verified and Justify-clean."
          />
        ) : (
          <table>
            <thead>
              <tr>
                <th>Decision</th>
                <th>Reason</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td className="font-mono text-xs">{item.decision_id}</td>
                  <td>
                    <Badge tone="warn">{item.reason}</Badge>
                  </td>
                  <td className="text-xs text-slate-500">{new Date(item.created_at).toLocaleString()}</td>
                  <td>
                    <Link
                      href={`/decisions/${item.decision_id}`}
                      className="inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-700"
                    >
                      Review
                      <ArrowRightIcon className="h-3.5 w-3.5" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

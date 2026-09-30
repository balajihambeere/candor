import Link from "next/link";

import { apiGet } from "@/lib/api";
import type { ReviewItem } from "@/lib/types";
import { Badge } from "@/components/Badge";
import { Card } from "@/components/Card";

export const dynamic = "force-dynamic";

export default async function ReviewQueuePage() {
  const items = await apiGet<ReviewItem[]>("/v1/review-queue");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Review Queue</h1>
        <p className="mt-1 text-sm text-slate-500">
          Every case here failed a check the pipeline runs on itself — Trace couldn&apos;t verify a
          reason, or Justify&apos;s sentence didn&apos;t pass faithfulness or plain language. Nothing here
          has been disclosed to anyone yet.
        </p>
      </div>

      <Card title={`Pending (${items.length})`}>
        {items.length === 0 ? (
          <p className="text-sm text-slate-500">
            Nothing pending. Every recent decision was Trace-verified and Justify-clean.
          </p>
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
                    <Link href={`/decisions/${item.decision_id}`} className="text-indigo-600 hover:underline">
                      Review →
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

import Link from "next/link";

import { apiGet } from "@/lib/api";
import type { DecisionList, StatsSummary } from "@/lib/types";
import { Badge, verdictTone } from "@/components/Badge";
import { Card } from "@/components/Card";
import { StatCard } from "@/components/StatCard";
import { ArrowRightIcon, DecisionsIcon, LedgerIcon, QueueIcon } from "@/components/icons";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [stats, recent] = await Promise.all([
    apiGet<StatsSummary>("/v1/stats/summary"),
    apiGet<DecisionList>("/v1/decisions?limit=5&offset=0"),
  ]);

  const approvedPct = stats.total_decisions === 0 ? 0 : Math.round((stats.approved / stats.total_decisions) * 100);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Overview</h1>
        <p className="mt-1.5 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
          What the pipeline has decided, what still needs a human, and what&apos;s already been
          disclosed to a customer.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          href="/decisions"
          icon={<DecisionsIcon className="h-4.5 w-4.5" />}
          label="Total decisions"
          value={stats.total_decisions}
          detail={`${stats.approved} approved · ${stats.denied} denied`}
          accent="indigo"
        />
        <StatCard
          href="/review-queue"
          icon={<QueueIcon className="h-4.5 w-4.5" />}
          label="Pending review"
          value={stats.pending_review}
          detail={stats.pending_review === 0 ? "All caught up" : "Needs a human decision"}
          accent={stats.pending_review === 0 ? "emerald" : "amber"}
        />
        <StatCard
          href="/disclosures"
          icon={<LedgerIcon className="h-4.5 w-4.5" />}
          label="Disclosed to customers"
          value={stats.disclosed_decisions}
          detail={`of ${stats.total_decisions} total decisions`}
          accent="slate"
        />
        <StatCard
          href="/decisions"
          icon={<DecisionsIcon className="h-4.5 w-4.5" />}
          label="Approval rate"
          value={`${approvedPct}%`}
          detail={`${stats.approved} of ${stats.total_decisions} decisions`}
          accent="emerald"
        />
      </div>

      <Card
        title="Recent decisions"
        subtitle="The 5 most recently decided cases"
        action={
          <Link
            href="/decisions"
            className="inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
          >
            View all
            <ArrowRightIcon className="h-3.5 w-3.5" />
          </Link>
        }
      >
        {recent.items.length === 0 ? (
          <p className="text-sm text-slate-400 dark:text-slate-500">No decisions yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Decision</th>
                <th>Category</th>
                <th>Verdict</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {recent.items.map((item) => (
                <tr key={item.id}>
                  <td className="font-mono text-xs">
                    <Link
                      href={`/decisions/${item.id}`}
                      className="text-indigo-600 hover:text-indigo-700 hover:underline dark:text-indigo-400 dark:hover:text-indigo-300"
                    >
                      {item.id}
                    </Link>
                  </td>
                  <td className="capitalize">{item.category.replace(/_/g, " ")}</td>
                  <td>
                    <Badge tone={verdictTone(item.verdict)}>{item.verdict}</Badge>
                  </td>
                  <td>
                    {item.needs_review ? <Badge tone="warn">Needs review</Badge> : <Badge tone="good">Clean</Badge>}
                  </td>
                  <td className="text-xs text-slate-500 dark:text-slate-400">{new Date(item.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

import Link from "next/link";

import { apiGet } from "@/lib/api";
import type { DecisionList } from "@/lib/types";
import { Badge, verdictTone } from "@/components/Badge";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ArrowRightIcon, DecisionsIcon } from "@/components/icons";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 25;

export default async function DecisionsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const { page } = await searchParams;
  const currentPage = Math.max(1, Number(page) || 1);
  const offset = (currentPage - 1) * PAGE_SIZE;

  const { items, total } = await apiGet<DecisionList>(`/v1/decisions?limit=${PAGE_SIZE}&offset=${offset}`);
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">All Decisions</h1>
        <p className="mt-1.5 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
          Every case the pipeline has decided, newest first — verified and disclosed, still pending
          review, or simply never surfaced to a customer yet.
        </p>
      </div>

      <Card
        title="Decisions"
        subtitle={`${total} total`}
        action={
          totalPages > 1 ? (
            <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
              <Link
                href={`/decisions?page=${Math.max(1, currentPage - 1)}`}
                aria-disabled={currentPage <= 1}
                className={`rounded-md px-2 py-1 ${
                  currentPage <= 1
                    ? "pointer-events-none text-slate-300 dark:text-slate-700"
                    : "hover:bg-slate-100 hover:text-slate-900 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                }`}
              >
                Prev
              </Link>
              <span className="text-xs">
                {currentPage} / {totalPages}
              </span>
              <Link
                href={`/decisions?page=${Math.min(totalPages, currentPage + 1)}`}
                aria-disabled={currentPage >= totalPages}
                className={`rounded-md px-2 py-1 ${
                  currentPage >= totalPages
                    ? "pointer-events-none text-slate-300 dark:text-slate-700"
                    : "hover:bg-slate-100 hover:text-slate-900 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                }`}
              >
                Next
              </Link>
            </div>
          ) : undefined
        }
      >
        {items.length === 0 ? (
          <EmptyState
            icon={<DecisionsIcon className="h-8 w-8" />}
            title="No decisions yet"
            description="Decisions submitted to the pipeline will show up here."
          />
        ) : (
          <table>
            <thead>
              <tr>
                <th>Decision</th>
                <th>Category</th>
                <th>Verdict</th>
                <th>Status</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td className="font-mono text-xs">{item.id}</td>
                  <td className="capitalize">{item.category.replace(/_/g, " ")}</td>
                  <td>
                    <Badge tone={verdictTone(item.verdict)}>{item.verdict}</Badge>
                  </td>
                  <td>
                    {item.needs_review ? (
                      <Badge tone="warn">Needs review</Badge>
                    ) : (
                      <Badge tone="good">Clean</Badge>
                    )}
                  </td>
                  <td className="text-xs text-slate-500 dark:text-slate-400">{new Date(item.created_at).toLocaleString()}</td>
                  <td>
                    <Link
                      href={`/decisions/${item.id}`}
                      className="inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
                    >
                      View
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

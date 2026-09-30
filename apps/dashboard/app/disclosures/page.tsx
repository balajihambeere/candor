import Link from "next/link";

import { apiGet } from "@/lib/api";
import type { Disclosure } from "@/lib/types";
import { Badge } from "@/components/Badge";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { LedgerEmptyIcon } from "@/components/icons";

export const dynamic = "force-dynamic";

export default async function DisclosuresPage() {
  const disclosures = await apiGet<Disclosure[]>("/v1/disclosures");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Disclosure Ledger</h1>
        <p className="mt-1.5 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
          Every explanation given, to whom, when, and whether it held up — the record Uttara started
          keeping the first time it mattered, meant to outlast any one call by years.
        </p>
      </div>

      <Card
        title="All disclosures"
        subtitle={`${disclosures.length} explanation${disclosures.length === 1 ? "" : "s"} delivered`}
      >
        {disclosures.length === 0 ? (
          <EmptyState
            icon={<LedgerEmptyIcon className="h-8 w-8" />}
            title="No disclosures logged yet"
            description="Once a decision is explained to a customer, it will show up here."
          />
        ) : (
          <table>
            <thead>
              <tr>
                <th>Decision</th>
                <th>Channel</th>
                <th>By</th>
                <th>When</th>
                <th>Delay owned</th>
                <th>Held up</th>
              </tr>
            </thead>
            <tbody>
              {disclosures.map((d) => (
                <tr key={d.id}>
                  <td className="font-mono text-xs">
                    <Link
                      href={`/decisions/${d.decision_id}`}
                      className="text-indigo-600 hover:text-indigo-700 hover:underline dark:text-indigo-400 dark:hover:text-indigo-300"
                    >
                      {d.decision_id}
                    </Link>
                  </td>
                  <td className="capitalize">{d.channel}</td>
                  <td>{d.disclosed_by}</td>
                  <td className="text-xs text-slate-500 dark:text-slate-400">{new Date(d.disclosed_at).toLocaleString()}</td>
                  <td>
                    <Badge tone={d.delay_owned ? "good" : "neutral"}>{d.delay_owned ? "Owned" : "No delay"}</Badge>
                  </td>
                  <td>
                    {d.held_up === null ? (
                      <span className="text-xs text-slate-400 dark:text-slate-500">—</span>
                    ) : (
                      <Badge tone={d.held_up ? "good" : "bad"}>{d.held_up ? "Held up" : "Did not hold"}</Badge>
                    )}
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

import Link from "next/link";

import { apiGet } from "@/lib/api";
import type { Disclosure } from "@/lib/types";
import { Card } from "@/components/Card";

export const dynamic = "force-dynamic";

export default async function DisclosuresPage() {
  const disclosures = await apiGet<Disclosure[]>("/v1/disclosures");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Disclosure Ledger</h1>
        <p className="mt-1 text-sm text-slate-500">
          Every explanation given, to whom, when, and whether it held up — the record Uttara started
          keeping the first time it mattered, meant to outlast any one call by years.
        </p>
      </div>

      <Card title={`All disclosures (${disclosures.length})`}>
        {disclosures.length === 0 ? (
          <p className="text-sm text-slate-500">No disclosures logged yet.</p>
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
                    <Link href={`/decisions/${d.decision_id}`} className="text-indigo-600 hover:underline">
                      {d.decision_id}
                    </Link>
                  </td>
                  <td>{d.channel}</td>
                  <td>{d.disclosed_by}</td>
                  <td className="text-xs text-slate-500">{new Date(d.disclosed_at).toLocaleString()}</td>
                  <td>{d.delay_owned ? "yes" : "no"}</td>
                  <td>{d.held_up === null ? "—" : d.held_up ? "yes" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

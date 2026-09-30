import Link from "next/link";

const ACCENTS = {
  indigo: "bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400",
  amber: "bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-400",
  emerald: "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400",
  slate: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
} as const;

export function StatCard({
  href,
  icon,
  label,
  value,
  detail,
  accent = "indigo",
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
  value: number | string;
  detail?: string;
  accent?: keyof typeof ACCENTS;
}) {
  return (
    <Link
      href={href}
      className="group flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition-all hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-slate-900 dark:shadow-none dark:hover:shadow-none"
    >
      <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${ACCENTS[accent]}`}>{icon}</div>
      <div>
        <p className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{value}</p>
        <p className="mt-0.5 text-sm font-medium text-slate-500 group-hover:text-slate-700 dark:text-slate-400 dark:group-hover:text-slate-200">
          {label}
        </p>
        {detail && <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">{detail}</p>}
      </div>
    </Link>
  );
}

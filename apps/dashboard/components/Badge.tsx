const TONES = {
  good: {
    bg: "bg-emerald-50 dark:bg-emerald-500/10",
    text: "text-emerald-700 dark:text-emerald-400",
    dot: "bg-emerald-500",
    ring: "ring-emerald-600/10 dark:ring-emerald-400/20",
  },
  bad: {
    bg: "bg-red-50 dark:bg-red-500/10",
    text: "text-red-700 dark:text-red-400",
    dot: "bg-red-500",
    ring: "ring-red-600/10 dark:ring-red-400/20",
  },
  warn: {
    bg: "bg-amber-50 dark:bg-amber-500/10",
    text: "text-amber-700 dark:text-amber-400",
    dot: "bg-amber-500",
    ring: "ring-amber-600/10 dark:ring-amber-400/20",
  },
  neutral: {
    bg: "bg-slate-100 dark:bg-slate-800",
    text: "text-slate-600 dark:text-slate-300",
    dot: "bg-slate-400",
    ring: "ring-slate-600/10 dark:ring-slate-400/20",
  },
} as const;

export function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: keyof typeof TONES;
}) {
  const t = TONES[tone];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${t.bg} ${t.text} ${t.ring}`}
    >
      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${t.dot}`} />
      {children}
    </span>
  );
}

export function verdictTone(verdict: string): keyof typeof TONES {
  return verdict === "denied" ? "bad" : "good";
}

export function statusTone(status: string): keyof typeof TONES {
  if (status === "verified" || status === "resolved") return "good";
  return "warn";
}

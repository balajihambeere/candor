const TONES = {
  good: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", ring: "ring-emerald-600/10" },
  bad: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", ring: "ring-red-600/10" },
  warn: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500", ring: "ring-amber-600/10" },
  neutral: { bg: "bg-slate-100", text: "text-slate-600", dot: "bg-slate-400", ring: "ring-slate-600/10" },
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

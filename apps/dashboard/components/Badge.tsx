const TONES = {
  good: "bg-emerald-100 text-emerald-800",
  bad: "bg-red-100 text-red-800",
  warn: "bg-amber-100 text-amber-800",
  neutral: "bg-slate-100 text-slate-700",
} as const;

export function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: keyof typeof TONES;
}) {
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${TONES[tone]}`}>
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

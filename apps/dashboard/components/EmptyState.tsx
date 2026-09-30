export function EmptyState({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-50 text-slate-300">
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium text-slate-700">{title}</p>
        <p className="mt-1 max-w-sm text-sm text-slate-400">{description}</p>
      </div>
    </div>
  );
}

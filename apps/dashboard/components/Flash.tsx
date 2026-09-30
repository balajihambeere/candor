export function Flash({ error, message }: { error?: string; message?: string }) {
  if (!error && !message) return null;
  return (
    <div className="mb-4">
      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}
      {message && (
        <div className="rounded border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {message}
        </div>
      )}
    </div>
  );
}

type Props = { lastSyncAt: string | null; lastError: string | null };

function ago(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const min = Math.floor(ms / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return `${Math.floor(hr / 24)}d ago`;
}

export function StalenessBadge({ lastSyncAt, lastError }: Props) {
  if (lastError) {
    return (
      <span className="inline-flex items-center rounded px-2 py-0.5 text-xs font-mono bg-red-50 text-red-700 border border-red-200">
        error
      </span>
    );
  }
  if (!lastSyncAt) {
    return (
      <span className="inline-flex items-center rounded px-2 py-0.5 text-xs font-mono bg-ink-100 text-ink-500 border border-ink-200">
        no sync yet
      </span>
    );
  }
  const ms = Date.now() - new Date(lastSyncAt).getTime();
  const stale = ms > 30 * 60 * 1000;
  const cls = stale
    ? "bg-amber-50 text-amber-800 border-amber-200"
    : "bg-emerald-50 text-emerald-800 border-emerald-200";
  return (
    <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-mono border ${cls}`}>
      {ago(lastSyncAt)}
    </span>
  );
}

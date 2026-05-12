"use client";

import { useEffect, useState } from "react";
import { api, type Overview } from "@/lib/api";
import { StalenessBadge } from "@/components/StalenessBadge";

function fmt(n: string | number) {
  const num = typeof n === "string" ? Number(n) : n;
  return num.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export default function OverviewPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.overview().then(setData).catch((e) => setErr(String(e)));
  }, []);

  if (err) return <p className="text-red-600 font-mono text-sm">{err}</p>;
  if (!data) return <p className="text-ink-500 text-sm">loading…</p>;

  return (
    <div className="space-y-8">
      <section>
        <h2 className="text-sm uppercase tracking-wide text-ink-500 mb-3">Per-currency totals</h2>
        {data.buckets.length === 0 ? (
          <p className="text-ink-400 text-sm">No positions yet. Add one in <a className="underline" href="/positions/new">Positions → New</a> or run a refresh in <a className="underline" href="/connectors">Connectors</a>.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.buckets.map((b) => (
              <div key={b.currency_bucket} className="rounded border border-ink-200 bg-white p-4">
                <div className="text-xs font-mono text-ink-500">{b.currency_bucket}</div>
                <div className="text-2xl font-mono mt-1">{fmt(b.total_value)}</div>
                <div className="text-xs text-ink-400 mt-1">{b.position_count} position{b.position_count === 1 ? "" : "s"}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-sm uppercase tracking-wide text-ink-500 mb-3">By account</h2>
        <div className="rounded border border-ink-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-ink-500 border-b border-ink-200">
                <th className="px-4 py-2 font-medium">Source</th>
                <th className="px-4 py-2 font-medium">Account</th>
                <th className="px-4 py-2 font-medium">Bucket</th>
                <th className="px-4 py-2 font-medium text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {data.by_venue.map((v, i) => (
                <tr key={i} className="border-b border-ink-100 last:border-0">
                  <td className="px-4 py-2 font-mono">{v.source_venue}</td>
                  <td className="px-4 py-2 font-mono text-ink-500">{v.account_label}</td>
                  <td className="px-4 py-2 font-mono text-ink-500">{v.currency_bucket}</td>
                  <td className="px-4 py-2 font-mono text-right">{fmt(v.total_value)}</td>
                </tr>
              ))}
              {data.by_venue.length === 0 && (
                <tr><td colSpan={3} className="px-4 py-3 text-ink-400 text-center">—</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-sm uppercase tracking-wide text-ink-500 mb-3">Connectors</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.connectors.map((c) => (
            <div key={c.venue} className="rounded border border-ink-200 bg-white p-4 flex items-center justify-between">
              <div>
                <div className="font-mono text-sm">{c.venue}</div>
                <div className="text-xs text-ink-400 mt-1">{c.enabled ? "enabled" : "disabled"}</div>
              </div>
              <StalenessBadge lastSyncAt={c.last_sync_at} lastError={c.last_error} />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

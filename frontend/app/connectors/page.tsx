"use client";

import { useEffect, useState } from "react";
import { api, type ConnectorHealth } from "@/lib/api";
import { StalenessBadge } from "@/components/StalenessBadge";

export default function ConnectorsPage() {
  const [rows, setRows] = useState<ConnectorHealth[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    try {
      setRows(await api.connectors());
    } catch (e) {
      setErr(String(e));
    }
  }

  useEffect(() => { load(); }, []);

  async function refresh(venue: string) {
    setBusy(venue);
    setErr(null);
    try {
      await api.refresh(venue);
      await load();
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(null);
    }
  }

  if (err) return <p className="text-red-600 font-mono text-sm">{err}</p>;
  if (!rows) return <p className="text-ink-500 text-sm">loading…</p>;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {rows.map((c) => (
          <div key={c.venue} className="rounded border border-ink-200 bg-white p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-mono text-sm">{c.venue}</div>
                <div className="text-xs text-ink-400 mt-1">{c.enabled ? "enabled" : "disabled"}</div>
              </div>
              <StalenessBadge lastSyncAt={c.last_sync_at} lastError={c.last_error} />
            </div>
            {c.last_error && (
              <pre className="mt-3 text-xs text-red-700 bg-red-50 border border-red-200 rounded p-2 whitespace-pre-wrap break-all">
                {c.last_error}
              </pre>
            )}
            <div className="mt-3 flex gap-2">
              <button
                disabled={busy === c.venue}
                onClick={() => refresh(c.venue)}
                className="rounded border border-ink-300 bg-white px-3 py-1.5 text-xs hover:bg-ink-50 disabled:opacity-50">
                {busy === c.venue ? "refreshing…" : "refresh now"}
              </button>
              {c.venue === "binance" && !c.enabled && (
                <span className="text-xs text-ink-500 self-center">add API keys to .env to enable</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

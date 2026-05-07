"use client";

import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";
import { api, type Overview, type History } from "@/lib/api";

const RANGES = ["1d", "1w", "1m", "ytd", "max"] as const;

export default function HistoryPage() {
  const [buckets, setBuckets] = useState<string[]>([]);
  const [bucket, setBucket] = useState<string>("");
  const [range, setRange] = useState<(typeof RANGES)[number]>("1m");
  const [data, setData] = useState<History | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.overview().then((o: Overview) => {
      const bs = o.buckets.map((b) => b.currency_bucket);
      setBuckets(bs);
      if (bs.length && !bucket) setBucket(bs[0]);
    }).catch((e) => setErr(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!bucket) return;
    api.history(bucket, range).then(setData).catch((e) => setErr(String(e)));
  }, [bucket, range]);

  if (err) return <p className="text-red-600 font-mono text-sm">{err}</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <select value={bucket} onChange={(e) => setBucket(e.target.value)}
          className="rounded border border-ink-200 bg-white px-3 py-2 text-sm font-mono">
          {buckets.map((b) => <option key={b} value={b}>{b}</option>)}
        </select>
        <div className="flex gap-1">
          {RANGES.map((r) => (
            <button key={r}
              onClick={() => setRange(r)}
              className={`rounded px-3 py-1.5 text-xs font-mono border ${
                range === r ? "bg-ink-900 text-white border-ink-900" : "bg-white text-ink-700 border-ink-200 hover:bg-ink-50"
              }`}>
              {r}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded border border-ink-200 bg-white p-4 h-80">
        {data && data.points.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.points.map((p) => ({ ts: p.ts_utc, value: Number(p.total_value) }))}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis dataKey="ts" tick={{ fontSize: 10, fill: "#64748b" }}
                tickFormatter={(t) => new Date(t).toLocaleDateString()} />
              <YAxis tick={{ fontSize: 10, fill: "#64748b" }} width={80}
                tickFormatter={(v) => Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })} />
              <Tooltip
                formatter={(v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                labelFormatter={(t) => new Date(t).toLocaleString()} />
              <Line type="monotone" dataKey="value" stroke="#0f172a" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-sm text-ink-400">
            no snapshots in range yet
          </div>
        )}
      </div>
    </div>
  );
}

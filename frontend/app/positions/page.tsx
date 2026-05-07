"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, type Position } from "@/lib/api";

function fmt(n: string | number | null) {
  if (n === null) return "—";
  const num = typeof n === "string" ? Number(n) : n;
  if (Number.isNaN(num)) return "—";
  return num.toLocaleString(undefined, { maximumFractionDigits: 6 });
}

function pct(p: number | null) {
  if (p === null) return "—";
  return `${(p * 100).toFixed(2)}%`;
}

function toCsv(rows: Position[]): string {
  const cols = [
    "symbol", "source_venue", "account_label", "asset_type",
    "quantity", "quote_currency", "currency_bucket",
    "mark_price", "cost_basis_per_unit", "cost_basis_currency",
    "market_value", "pnl_absolute", "pnl_pct", "as_of_utc",
  ] as const;
  const head = cols.join(",");
  const body = rows.map((r) => cols.map((c) => {
    const v = (r as Record<string, unknown>)[c];
    return v === null || v === undefined ? "" : String(v);
  }).join(",")).join("\n");
  return `${head}\n${body}`;
}

export default function PositionsPage() {
  const [rows, setRows] = useState<Position[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    api.positions().then(setRows).catch((e) => setErr(String(e)));
  }, []);

  const visible = useMemo(() => {
    if (!rows) return [];
    const f = filter.trim().toLowerCase();
    if (!f) return rows;
    return rows.filter((r) =>
      r.symbol.toLowerCase().includes(f) ||
      r.source_venue.toLowerCase().includes(f) ||
      r.currency_bucket.toLowerCase().includes(f)
    );
  }, [rows, filter]);

  function downloadCsv() {
    const blob = new Blob([toCsv(visible)], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "positions.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  if (err) return <p className="text-red-600 font-mono text-sm">{err}</p>;
  if (!rows) return <p className="text-ink-500 text-sm">loading…</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="filter by symbol, venue, bucket"
          className="flex-1 rounded border border-ink-200 bg-white px-3 py-2 text-sm font-mono"
        />
        <button onClick={downloadCsv} className="rounded border border-ink-300 bg-white px-3 py-2 text-sm hover:bg-ink-50">
          export CSV
        </button>
        <Link href="/positions/new" className="rounded bg-ink-900 px-3 py-2 text-sm text-white hover:bg-ink-800">
          + manual position
        </Link>
      </div>

      <div className="rounded border border-ink-200 bg-white overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-ink-500 border-b border-ink-200">
              <th className="px-3 py-2 font-medium">Symbol</th>
              <th className="px-3 py-2 font-medium">Venue</th>
              <th className="px-3 py-2 font-medium">Bucket</th>
              <th className="px-3 py-2 font-medium text-right">Qty</th>
              <th className="px-3 py-2 font-medium text-right">Mark</th>
              <th className="px-3 py-2 font-medium text-right">Cost</th>
              <th className="px-3 py-2 font-medium text-right">Value</th>
              <th className="px-3 py-2 font-medium text-right">P/L</th>
              <th className="px-3 py-2 font-medium text-right">P/L %</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => {
              const pnl = r.pnl_absolute !== null ? Number(r.pnl_absolute) : null;
              const pnlClass = pnl === null ? "" : pnl >= 0 ? "text-emerald-700" : "text-red-700";
              return (
                <tr key={r.id} className="border-b border-ink-100 last:border-0 font-mono">
                  <td className="px-3 py-2">{r.symbol}</td>
                  <td className="px-3 py-2 text-ink-500">{r.source_venue}</td>
                  <td className="px-3 py-2 text-ink-500">{r.currency_bucket}</td>
                  <td className="px-3 py-2 text-right">{fmt(r.quantity)}</td>
                  <td className="px-3 py-2 text-right">{fmt(r.mark_price)}</td>
                  <td className="px-3 py-2 text-right">{fmt(r.cost_basis_per_unit)}</td>
                  <td className="px-3 py-2 text-right">{fmt(r.market_value)}</td>
                  <td className={`px-3 py-2 text-right ${pnlClass}`}>{fmt(r.pnl_absolute)}</td>
                  <td className={`px-3 py-2 text-right ${pnlClass}`}>{pct(r.pnl_pct)}</td>
                </tr>
              );
            })}
            {visible.length === 0 && (
              <tr><td colSpan={9} className="px-3 py-3 text-ink-400 text-center">no positions</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

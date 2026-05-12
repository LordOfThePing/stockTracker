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


function num(v: string | number | null) {
  if (v === null) return null;
  const n = typeof v === "string" ? Number(v) : v;
  return Number.isNaN(n) ? null : n;
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

type EditState = {
  manualId: number;
  provider: string;
  symbol: string;
  assetType: string;
  quoteCurrency: string;
  quantity: string;
  costBasis: string;
  costCurrency: string;
  notes: string;
};

export default function PositionsPage() {
  const [rows, setRows] = useState<Position[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [editing, setEditing] = useState<EditState | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setRows(await api.positions());
    } catch (e) {
      setErr(String(e));
    }
  }

  useEffect(() => { load(); }, []);

  const visible = useMemo(() => {
    if (!rows) return [];
    const f = filter.trim().toLowerCase();
    if (!f) return rows;
    return rows.filter((r) =>
      r.symbol.toLowerCase().includes(f) ||
      r.source_venue.toLowerCase().includes(f) ||
      r.account_label.toLowerCase().includes(f) ||
      r.asset_type.toLowerCase().includes(f) ||
      r.currency_bucket.toLowerCase().includes(f)
    );
  }, [rows, filter]);

  const totals = useMemo(() => {
    let cost = 0;
    let value = 0;
    let pnl = 0;
    for (const r of visible) {
      const qty = num(r.quantity);
      const unitCost = num(r.cost_basis_per_unit);
      const marketValue = num(r.market_value);
      const pnlAbs = num(r.pnl_absolute);
      if (marketValue !== null) {
        value += marketValue;
        // No cost basis → treat cost = value so it doesn't skew the totals row
        cost += (qty !== null && unitCost !== null) ? qty * unitCost : marketValue;
      }
      if (pnlAbs !== null) pnl += pnlAbs;
    }
    const pnlPct = cost > 0 ? pnl / cost : null;
    return { cost, value, pnl, pnlPct };
  }, [visible]);

  function downloadCsv() {
    const blob = new Blob([toCsv(visible)], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "positions.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleDelete(r: Position) {
    if (!r.manual_position_id) return;
    if (!confirm(`Delete manual position ${r.symbol}?`)) return;
    try {
      await api.deleteManual(r.manual_position_id);
      await api.refresh("manual");
      await load();
    } catch (e) {
      setErr(String(e));
    }
  }

  function startEdit(r: Position) {
    if (!r.manual_position_id) return;
    setEditing({
      manualId: r.manual_position_id,
      provider: r.account_label,
      symbol: r.symbol,
      assetType: r.asset_type,
      quoteCurrency: r.quote_currency,
      quantity: r.quantity,
      costBasis: r.cost_basis_per_unit ?? "",
      costCurrency: r.cost_basis_currency ?? "",
      notes: "",
    });
  }

  async function saveEdit() {
    if (!editing) return;
    setBusy(true);
    try {
      await api.patchManual(editing.manualId, {
        account_label: editing.provider,
        symbol: editing.symbol,
        asset_type: editing.assetType,
        quote_currency: editing.quoteCurrency,
        quantity: editing.quantity,
        cost_basis_per_unit: editing.costBasis,
        cost_basis_currency: editing.costCurrency,
        notes: editing.notes || null,
      });
      await api.refresh("manual");
      setEditing(null);
      await load();
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  if (err) return <p className="text-red-600 font-mono text-sm">{err}</p>;
  if (!rows) return <p className="text-ink-500 text-sm">loading…</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="filter by symbol, provider, type, bucket"
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
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-ink-500 border-b border-ink-200 whitespace-nowrap">
              <th className="px-3 py-2 font-medium">Symbol</th>
              <th className="px-3 py-2 font-medium">Source</th>
              <th className="px-3 py-2 font-medium">Account</th>
              <th className="px-3 py-2 font-medium">Asset Type</th>
              <th className="px-3 py-2 font-medium">Bucket</th>
              <th className="px-3 py-2 font-medium text-right">Qty</th>
              <th className="px-3 py-2 font-medium text-right">Mark</th>
              <th className="px-3 py-2 font-medium text-right">Cost</th>
              <th className="px-3 py-2 font-medium text-right">Value</th>
              <th className="px-3 py-2 font-medium text-right">P/L</th>
              <th className="px-3 py-2 font-medium text-right">P/L %</th>
              <th className="px-3 py-2 font-medium text-right w-20"></th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => {
              const pnl = r.pnl_absolute !== null ? Number(r.pnl_absolute) : null;
              const pnlClass = pnl === null ? "" : pnl >= 0 ? "text-emerald-700" : "text-red-700";
              const isManual = r.source_venue === "manual" && r.manual_position_id !== null;
              return (
                <tr key={`${r.source_venue}-${r.id}`} className="border-b border-ink-100 last:border-0 font-mono whitespace-nowrap">
                  <td className="px-3 py-2">{r.symbol}</td>
                  <td className="px-3 py-2 text-ink-500">{r.source_venue}</td>
                  <td className="px-3 py-2 text-ink-500 max-w-[10rem]">
                    <span className="block truncate" title={r.account_label}>{r.account_label}</span>
                  </td>
                  <td className="px-3 py-2 text-ink-500">{r.asset_type}</td>
                  <td className="px-3 py-2 text-ink-500">{r.currency_bucket}</td>
                  <td className="px-3 py-2 text-right">{fmt(r.quantity)}</td>
                  <td className="px-3 py-2 text-right">{fmt(r.mark_price)}</td>
                  <td className="px-3 py-2 text-right">{fmt(r.cost_basis_per_unit)}</td>
                  <td className="px-3 py-2 text-right">{fmt(r.market_value)}</td>
                  <td className={`px-3 py-2 text-right ${pnlClass}`}>{fmt(r.pnl_absolute)}</td>
                  <td className={`px-3 py-2 text-right ${pnlClass}`}>{pct(r.pnl_pct)}</td>
                  <td className="px-3 py-2 text-right">
                    {isManual && (
                      <span className="inline-flex gap-2">
                        <button onClick={() => startEdit(r)}
                          className="text-xs text-ink-500 hover:text-ink-900" title="edit">edit</button>
                        <button onClick={() => handleDelete(r)}
                          className="text-xs text-ink-500 hover:text-red-700" title="delete">×</button>
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
            {visible.length > 0 && (
              <tr className="font-mono bg-ink-50/60 border-t border-ink-200 whitespace-nowrap">
                <td className="px-3 py-2 text-ink-700" colSpan={7}>Totals</td>
                <td className="px-3 py-2 text-right">{fmt(totals.cost)}</td>
                <td className="px-3 py-2 text-right">{fmt(totals.value)}</td>
                <td className={`px-3 py-2 text-right ${totals.pnl >= 0 ? "text-emerald-700" : "text-red-700"}`}>{fmt(totals.pnl)}</td>
                <td className={`px-3 py-2 text-right ${totals.pnlPct === null ? "" : totals.pnlPct >= 0 ? "text-emerald-700" : "text-red-700"}`}>{pct(totals.pnlPct)}</td>
                <td className="px-3 py-2 text-right"></td>
              </tr>
            )}
            {visible.length === 0 && (
              <tr><td colSpan={11} className="px-3 py-3 text-ink-400 text-center">no positions</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {editing && (
        <div className="fixed inset-0 bg-ink-900/40 flex items-center justify-center z-10" onClick={() => setEditing(null)}>
          <div className="bg-white rounded shadow-lg p-5 w-full max-w-md space-y-3" onClick={(e) => e.stopPropagation()}>
            <h2 className="font-mono text-sm">Edit manual position: {editing.symbol}</h2>
            <label className="block text-sm">
              <div className="text-ink-500 mb-1">Provider</div>
              <input value={editing.provider}
                onChange={(e) => setEditing({ ...editing, provider: e.target.value })}
                className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono" />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block text-sm">
                <div className="text-ink-500 mb-1">Symbol</div>
                <input value={editing.symbol}
                  onChange={(e) => setEditing({ ...editing, symbol: e.target.value.toUpperCase() })}
                  className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono" />
              </label>
              <label className="block text-sm">
                <div className="text-ink-500 mb-1">Asset type</div>
                <select value={editing.assetType}
                  onChange={(e) => setEditing({ ...editing, assetType: e.target.value })}
                  className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono">
                  <option value="crypto">crypto</option>
                  <option value="equity">equity</option>
                  <option value="other">other</option>
                </select>
              </label>
            </div>
            <label className="block text-sm">
              <div className="text-ink-500 mb-1">Quote currency</div>
              <input value={editing.quoteCurrency}
                onChange={(e) => setEditing({ ...editing, quoteCurrency: e.target.value.toUpperCase() })}
                className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono" />
            </label>
            <label className="block text-sm">
              <div className="text-ink-500 mb-1">Quantity</div>
              <input value={editing.quantity}
                onChange={(e) => setEditing({ ...editing, quantity: e.target.value })}
                inputMode="decimal"
                className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono" />
            </label>
            <label className="block text-sm">
              <div className="text-ink-500 mb-1">Cost basis (per unit)</div>
              <input value={editing.costBasis}
                onChange={(e) => setEditing({ ...editing, costBasis: e.target.value })}
                inputMode="decimal"
                className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono" />
            </label>
            <label className="block text-sm">
              <div className="text-ink-500 mb-1">Cost basis currency</div>
              <input value={editing.costCurrency}
                onChange={(e) => setEditing({ ...editing, costCurrency: e.target.value.toUpperCase() })}
                className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono" />
            </label>
            <label className="block text-sm">
              <div className="text-ink-500 mb-1">Notes</div>
              <textarea value={editing.notes}
                onChange={(e) => setEditing({ ...editing, notes: e.target.value })}
                rows={2}
                className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono" />
            </label>
            <div className="flex gap-2 justify-end pt-2">
              <button onClick={() => setEditing(null)}
                className="rounded border border-ink-300 bg-white px-3 py-1.5 text-sm hover:bg-ink-50">cancel</button>
              <button onClick={saveEdit} disabled={busy}
                className="rounded bg-ink-900 px-3 py-1.5 text-sm text-white hover:bg-ink-800 disabled:opacity-50">
                {busy ? "saving…" : "save"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

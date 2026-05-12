"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { api, type Position } from "@/lib/api";

function fmt(n: string | number | null) {
  if (n === null) return "—";
  const v = typeof n === "string" ? Number(n) : n;
  if (Number.isNaN(v)) return "—";
  return v.toLocaleString(undefined, { maximumFractionDigits: 6 });
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
  const body = rows.map((r) =>
    cols.map((c) => {
      const val = (r as Record<string, unknown>)[c];
      return val === null || val === undefined ? "" : String(val);
    }).join(",")
  ).join("\n");
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

type SortDir = "asc" | "desc";

type ColKey =
  | "symbol" | "source_venue" | "account_label" | "asset_type"
  | "currency_bucket" | "quantity" | "mark_price" | "cost_basis_per_unit"
  | "market_value" | "pnl_absolute" | "pnl_pct";

type ColDef = {
  key: ColKey;
  label: string;
  align: "left" | "right";
  hideable: boolean;
};

const COL_DEFS: ColDef[] = [
  { key: "symbol",              label: "Symbol",     align: "left",  hideable: false },
  { key: "source_venue",        label: "Source",     align: "left",  hideable: true  },
  { key: "account_label",       label: "Account",    align: "left",  hideable: true  },
  { key: "asset_type",          label: "Asset Type", align: "left",  hideable: true  },
  { key: "currency_bucket",     label: "Bucket",     align: "left",  hideable: true  },
  { key: "quantity",            label: "Qty",        align: "right", hideable: true  },
  { key: "mark_price",          label: "Mark",       align: "right", hideable: true  },
  { key: "cost_basis_per_unit", label: "Cost",       align: "right", hideable: true  },
  { key: "market_value",        label: "Value",      align: "right", hideable: true  },
  { key: "pnl_absolute",        label: "P/L",        align: "right", hideable: true  },
  { key: "pnl_pct",             label: "P/L %",      align: "right", hideable: true  },
];

function sortVal(r: Position, key: ColKey): string | number | null {
  switch (key) {
    case "symbol":              return r.symbol;
    case "source_venue":        return r.source_venue;
    case "account_label":       return r.account_label;
    case "asset_type":          return r.asset_type;
    case "currency_bucket":     return r.currency_bucket;
    case "quantity":            return num(r.quantity);
    case "mark_price":          return num(r.mark_price);
    case "cost_basis_per_unit": return num(r.cost_basis_per_unit);
    case "market_value":        return num(r.market_value);
    case "pnl_absolute":        return num(r.pnl_absolute);
    case "pnl_pct":             return r.pnl_pct;
  }
}

export default function PositionsPage() {
  const [rows, setRows] = useState<Position[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [editing, setEditing] = useState<EditState | null>(null);
  const [busy, setBusy] = useState(false);
  const [sortCol, setSortCol] = useState<ColKey | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [hiddenCols, setHiddenCols] = useState<Set<ColKey>>(new Set());
  const [showColPicker, setShowColPicker] = useState(false);
  const colPickerRef = useRef<HTMLDivElement>(null);

  async function load() {
    try {
      setRows(await api.positions());
    } catch (e) {
      setErr(String(e));
    }
  }

  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (!showColPicker) return;
    function onDown(e: MouseEvent) {
      if (colPickerRef.current && !colPickerRef.current.contains(e.target as Node)) {
        setShowColPicker(false);
      }
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [showColPicker]);

  const filtered = useMemo(() => {
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

  const sorted = useMemo(() => {
    if (!sortCol) return filtered;
    return [...filtered].sort((a, b) => {
      const va = sortVal(a, sortCol);
      const vb = sortVal(b, sortCol);
      if (va === null && vb === null) return 0;
      if (va === null) return 1;
      if (vb === null) return -1;
      const cmp = typeof va === "string"
        ? va.localeCompare(vb as string)
        : (va as number) - (vb as number);
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [filtered, sortCol, sortDir]);

  const totals = useMemo(() => {
    let cost = 0, value = 0, pnl = 0;
    for (const r of filtered) {
      const qty = num(r.quantity);
      const unitCost = num(r.cost_basis_per_unit);
      const mv = num(r.market_value);
      const pnlAbs = num(r.pnl_absolute);
      if (mv !== null) {
        value += mv;
        cost += (qty !== null && unitCost !== null) ? qty * unitCost : mv;
      }
      if (pnlAbs !== null) pnl += pnlAbs;
    }
    return { cost, value, pnl, pnlPct: cost > 0 ? pnl / cost : null };
  }, [filtered]);

  function downloadCsv() {
    const blob = new Blob([toCsv(filtered)], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "positions.csv"; a.click();
    URL.revokeObjectURL(url);
  }

  function toggleSort(key: ColKey) {
    if (sortCol === key) {
      if (sortDir === "asc") setSortDir("desc");
      else { setSortCol(null); setSortDir("asc"); }
    } else {
      setSortCol(key); setSortDir("asc");
    }
  }

  function toggleCol(key: ColKey) {
    setHiddenCols((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
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

  const visCols = COL_DEFS.filter((c) => !hiddenCols.has(c.key));

  function sortIcon(key: ColKey) {
    if (sortCol !== key) return <span className="ml-1 opacity-30">↕</span>;
    return <span className="ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>;
  }

  const stickyHeader = "sticky left-0 bg-white z-10 after:absolute after:right-0 after:top-0 after:bottom-0 after:w-px after:bg-ink-200";
  const stickyCell   = "sticky left-0 bg-white z-10 after:absolute after:right-0 after:top-0 after:bottom-0 after:w-px after:bg-ink-100";
  const stickyCellTotals = "sticky left-0 bg-ink-50 z-10 after:absolute after:right-0 after:top-0 after:bottom-0 after:w-px after:bg-ink-200";

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="filter by symbol, provider, type, bucket"
          className="flex-1 rounded border border-ink-200 bg-white px-3 py-2 text-sm font-mono"
        />

        {/* Column picker */}
        <div className="relative" ref={colPickerRef}>
          <button
            onClick={() => setShowColPicker((v) => !v)}
            className="rounded border border-ink-300 bg-white px-3 py-2 text-sm hover:bg-ink-50 select-none"
          >
            columns ▾
          </button>
          {showColPicker && (
            <div className="absolute right-0 top-full mt-1 z-30 bg-white border border-ink-200 rounded shadow-lg p-3 space-y-1.5 min-w-[140px]">
              {COL_DEFS.filter((c) => c.hideable).map((c) => (
                <label key={c.key} className="flex items-center gap-2 text-sm cursor-pointer select-none hover:text-ink-900">
                  <input
                    type="checkbox"
                    checked={!hiddenCols.has(c.key)}
                    onChange={() => toggleCol(c.key)}
                  />
                  {c.label}
                </label>
              ))}
            </div>
          )}
        </div>

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
              {visCols.map((col) => (
                <th
                  key={col.key}
                  onClick={() => toggleSort(col.key)}
                  className={[
                    "px-3 py-2 font-medium cursor-pointer select-none hover:text-ink-900 relative",
                    col.align === "right" ? "text-right" : "",
                    col.key === "symbol" ? stickyHeader : "",
                  ].filter(Boolean).join(" ")}
                >
                  {col.label}{sortIcon(col.key)}
                </th>
              ))}
              <th className="px-3 py-2 font-medium w-20" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => {
              const pnlAbs = r.pnl_absolute !== null ? Number(r.pnl_absolute) : null;
              const pnlClass = pnlAbs === null ? "" : pnlAbs >= 0 ? "text-emerald-700" : "text-red-700";
              const isManual = r.source_venue === "manual" && r.manual_position_id !== null;
              return (
                <tr
                  key={`${r.source_venue}-${r.id}`}
                  className="border-b border-ink-100 last:border-0 font-mono whitespace-nowrap hover:bg-ink-50/40"
                >
                  {visCols.map((col) => {
                    const isSymbol = col.key === "symbol";
                    const isPnl = col.key === "pnl_absolute" || col.key === "pnl_pct";
                    const isAcct = col.key === "account_label";

                    let content: React.ReactNode;
                    switch (col.key) {
                      case "symbol":
                        content = r.symbol;
                        break;
                      case "source_venue":
                        content = <span className="text-ink-500">{r.source_venue}</span>;
                        break;
                      case "account_label":
                        content = (
                          <span className="block truncate text-ink-500" title={r.account_label}>
                            {r.account_label}
                          </span>
                        );
                        break;
                      case "asset_type":
                        content = <span className="text-ink-500">{r.asset_type}</span>;
                        break;
                      case "currency_bucket":
                        content = <span className="text-ink-500">{r.currency_bucket}</span>;
                        break;
                      case "quantity":            content = fmt(r.quantity); break;
                      case "mark_price":          content = fmt(r.mark_price); break;
                      case "cost_basis_per_unit": content = fmt(r.cost_basis_per_unit); break;
                      case "market_value":        content = fmt(r.market_value); break;
                      case "pnl_absolute":        content = fmt(r.pnl_absolute); break;
                      case "pnl_pct":             content = pct(r.pnl_pct); break;
                    }

                    return (
                      <td
                        key={col.key}
                        className={[
                          "px-3 py-2 relative",
                          col.align === "right" ? "text-right" : "",
                          isPnl ? pnlClass : "",
                          isSymbol ? stickyCell : "",
                          isAcct ? "max-w-[10rem]" : "",
                        ].filter(Boolean).join(" ")}
                      >
                        {content}
                      </td>
                    );
                  })}
                  <td className="px-3 py-2 text-right">
                    {isManual && (
                      <span className="inline-flex gap-2">
                        <button
                          onClick={() => startEdit(r)}
                          className="text-xs text-ink-500 hover:text-ink-900"
                        >
                          edit
                        </button>
                        <button
                          onClick={() => handleDelete(r)}
                          className="text-xs text-ink-500 hover:text-red-700"
                        >
                          ×
                        </button>
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}

            {/* Totals */}
            {sorted.length > 0 && (
              <tr className="font-mono bg-ink-50 border-t border-ink-200 whitespace-nowrap">
                {visCols.map((col) => {
                  if (col.key === "symbol") {
                    return (
                      <td key={col.key} className={`px-3 py-2 text-ink-700 relative ${stickyCellTotals}`}>
                        Totals
                      </td>
                    );
                  }
                  if (col.key === "cost_basis_per_unit") {
                    return <td key={col.key} className="px-3 py-2 text-right">{fmt(totals.cost)}</td>;
                  }
                  if (col.key === "market_value") {
                    return <td key={col.key} className="px-3 py-2 text-right">{fmt(totals.value)}</td>;
                  }
                  if (col.key === "pnl_absolute") {
                    return (
                      <td key={col.key} className={`px-3 py-2 text-right ${totals.pnl >= 0 ? "text-emerald-700" : "text-red-700"}`}>
                        {fmt(totals.pnl)}
                      </td>
                    );
                  }
                  if (col.key === "pnl_pct") {
                    return (
                      <td key={col.key} className={`px-3 py-2 text-right ${totals.pnlPct === null ? "" : totals.pnlPct >= 0 ? "text-emerald-700" : "text-red-700"}`}>
                        {pct(totals.pnlPct)}
                      </td>
                    );
                  }
                  return <td key={col.key} className="px-3 py-2" />;
                })}
                <td className="px-3 py-2" />
              </tr>
            )}

            {sorted.length === 0 && (
              <tr>
                <td colSpan={visCols.length + 1} className="px-3 py-3 text-ink-400 text-center">
                  no positions
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {editing && (
        <div
          className="fixed inset-0 bg-ink-900/40 flex items-center justify-center z-10"
          onClick={() => setEditing(null)}
        >
          <div
            className="bg-white rounded shadow-lg p-5 w-full max-w-md space-y-3"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="font-mono text-sm">Edit manual position: {editing.symbol}</h2>
            <label className="block text-sm">
              <div className="text-ink-500 mb-1">Provider</div>
              <input
                value={editing.provider}
                onChange={(e) => setEditing({ ...editing, provider: e.target.value })}
                className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono"
              />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block text-sm">
                <div className="text-ink-500 mb-1">Symbol</div>
                <input
                  value={editing.symbol}
                  onChange={(e) => setEditing({ ...editing, symbol: e.target.value.toUpperCase() })}
                  className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono"
                />
              </label>
              <label className="block text-sm">
                <div className="text-ink-500 mb-1">Asset type</div>
                <select
                  value={editing.assetType}
                  onChange={(e) => setEditing({ ...editing, assetType: e.target.value })}
                  className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono"
                >
                  <option value="crypto">crypto</option>
                  <option value="equity">equity</option>
                  <option value="other">other</option>
                </select>
              </label>
            </div>
            <label className="block text-sm">
              <div className="text-ink-500 mb-1">Quote currency</div>
              <input
                value={editing.quoteCurrency}
                onChange={(e) => setEditing({ ...editing, quoteCurrency: e.target.value.toUpperCase() })}
                className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono"
              />
            </label>
            <label className="block text-sm">
              <div className="text-ink-500 mb-1">Quantity</div>
              <input
                value={editing.quantity}
                onChange={(e) => setEditing({ ...editing, quantity: e.target.value })}
                inputMode="decimal"
                className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono"
              />
            </label>
            <label className="block text-sm">
              <div className="text-ink-500 mb-1">Cost basis (per unit)</div>
              <input
                value={editing.costBasis}
                onChange={(e) => setEditing({ ...editing, costBasis: e.target.value })}
                inputMode="decimal"
                className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono"
              />
            </label>
            <label className="block text-sm">
              <div className="text-ink-500 mb-1">Cost basis currency</div>
              <input
                value={editing.costCurrency}
                onChange={(e) => setEditing({ ...editing, costCurrency: e.target.value.toUpperCase() })}
                className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono"
              />
            </label>
            <label className="block text-sm">
              <div className="text-ink-500 mb-1">Notes</div>
              <textarea
                value={editing.notes}
                onChange={(e) => setEditing({ ...editing, notes: e.target.value })}
                rows={2}
                className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono"
              />
            </label>
            <div className="flex gap-2 justify-end pt-2">
              <button
                onClick={() => setEditing(null)}
                className="rounded border border-ink-300 bg-white px-3 py-1.5 text-sm hover:bg-ink-50"
              >
                cancel
              </button>
              <button
                onClick={saveEdit}
                disabled={busy}
                className="rounded bg-ink-900 px-3 py-1.5 text-sm text-white hover:bg-ink-800 disabled:opacity-50"
              >
                {busy ? "saving…" : "save"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

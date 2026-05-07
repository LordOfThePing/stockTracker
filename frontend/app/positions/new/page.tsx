"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, type InstrumentSearchResult } from "@/lib/api";

const FEEDS = ["coingecko", "stooq"] as const;
const ASSET_TYPES = ["crypto", "equity", "other"] as const;

export default function NewPositionPage() {
  const router = useRouter();
  const [feed, setFeed] = useState<(typeof FEEDS)[number]>("coingecko");
  const [searchQ, setSearchQ] = useState("");
  const [results, setResults] = useState<InstrumentSearchResult[]>([]);
  const [pick, setPick] = useState<InstrumentSearchResult | null>(null);
  const [assetType, setAssetType] = useState<(typeof ASSET_TYPES)[number]>("crypto");
  const [symbol, setSymbol] = useState("");
  const [quoteCurrency, setQuoteCurrency] = useState("USDT");
  const [qty, setQty] = useState("");
  const [costBasis, setCostBasis] = useState("");
  const [costCurrency, setCostCurrency] = useState("USDT");
  const [notes, setNotes] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function search() {
    if (!searchQ.trim()) return;
    try {
      const out = await api.searchInstruments(searchQ, feed);
      setResults(out);
    } catch (e) {
      setErr(String(e));
    }
  }

  function choose(r: InstrumentSearchResult) {
    setPick(r);
    if (!symbol) setSymbol(r.feed_symbol.toUpperCase());
    if (feed === "stooq" && r.feed_symbol.endsWith(".ar")) {
      setQuoteCurrency("ARS");
      setCostCurrency("ARS");
      setAssetType("equity");
    } else if (feed === "coingecko") {
      setQuoteCurrency("USDT");
      setCostCurrency("USDT");
      setAssetType("crypto");
    }
  }

  async function submit() {
    setErr(null);
    if (!pick) { setErr("Pick a feed symbol first."); return; }
    if (!qty || !costBasis) { setErr("Quantity and cost basis are required."); return; }
    setBusy(true);
    try {
      await api.createManual({
        symbol: symbol || pick.feed_symbol,
        asset_type: assetType,
        quote_currency: quoteCurrency,
        price_feed: pick.feed,
        feed_symbol: pick.feed_symbol,
        account_label: "manual",
        quantity: qty,
        cost_basis_per_unit: costBasis,
        cost_basis_currency: costCurrency,
      });
      await api.refresh("manual");
      router.push("/positions");
    } catch (e) {
      setErr(String(e));
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-lg font-mono">Add a manual position</h1>

      <section className="rounded border border-ink-200 bg-white p-4 space-y-3">
        <h2 className="text-xs uppercase tracking-wide text-ink-500">1. Find the instrument</h2>
        <div className="flex gap-2">
          <select value={feed} onChange={(e) => setFeed(e.target.value as typeof feed)}
            className="rounded border border-ink-200 bg-white px-3 py-2 text-sm font-mono">
            {FEEDS.map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
          <input
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); search(); } }}
            placeholder={feed === "stooq" ? "e.g. ggal.ar" : "e.g. bitcoin"}
            className="flex-1 rounded border border-ink-200 bg-white px-3 py-2 text-sm font-mono"
          />
          <button onClick={search} className="rounded border border-ink-300 bg-white px-3 py-2 text-sm hover:bg-ink-50">
            search
          </button>
        </div>
        {results.length > 0 && (
          <ul className="border border-ink-200 rounded divide-y divide-ink-100">
            {results.map((r) => (
              <li key={`${r.feed}:${r.feed_symbol}`}>
                <button
                  onClick={() => choose(r)}
                  className={`w-full text-left px-3 py-2 text-sm font-mono hover:bg-ink-50 ${pick?.feed_symbol === r.feed_symbol ? "bg-ink-50" : ""}`}>
                  <span className="text-ink-500 mr-2">{r.feed}</span>
                  <span className="text-ink-900">{r.feed_symbol}</span>
                  <span className="ml-2 text-ink-500">{r.display_name}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        {pick && (
          <p className="text-sm text-ink-600 font-mono">
            picked: <span className="text-ink-900">{pick.feed}:{pick.feed_symbol}</span>
          </p>
        )}
      </section>

      <section className="rounded border border-ink-200 bg-white p-4 space-y-3">
        <h2 className="text-xs uppercase tracking-wide text-ink-500">2. Position details</h2>
        <div className="grid grid-cols-2 gap-3">
          <label className="text-sm">
            <div className="text-ink-500 mb-1">Symbol (display)</div>
            <input value={symbol} onChange={(e) => setSymbol(e.target.value)}
              className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono" />
          </label>
          <label className="text-sm">
            <div className="text-ink-500 mb-1">Asset type</div>
            <select value={assetType} onChange={(e) => setAssetType(e.target.value as typeof assetType)}
              className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono">
              {ASSET_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          <label className="text-sm">
            <div className="text-ink-500 mb-1">Quote currency</div>
            <input value={quoteCurrency} onChange={(e) => setQuoteCurrency(e.target.value.toUpperCase())}
              className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono" />
          </label>
          <label className="text-sm">
            <div className="text-ink-500 mb-1">Quantity</div>
            <input value={qty} onChange={(e) => setQty(e.target.value)} inputMode="decimal"
              className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono" />
          </label>
          <label className="text-sm">
            <div className="text-ink-500 mb-1">Cost basis (per unit)</div>
            <input value={costBasis} onChange={(e) => setCostBasis(e.target.value)} inputMode="decimal"
              className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono" />
          </label>
          <label className="text-sm">
            <div className="text-ink-500 mb-1">Cost basis currency</div>
            <input value={costCurrency} onChange={(e) => setCostCurrency(e.target.value.toUpperCase())}
              className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono" />
          </label>
        </div>
        <label className="text-sm block">
          <div className="text-ink-500 mb-1">Notes</div>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2}
            className="w-full rounded border border-ink-200 bg-white px-3 py-2 font-mono" />
        </label>
      </section>

      {err && <p className="text-red-600 font-mono text-sm">{err}</p>}

      <div className="flex gap-3">
        <button disabled={busy} onClick={submit}
          className="rounded bg-ink-900 px-4 py-2 text-sm text-white hover:bg-ink-800 disabled:opacity-50">
          {busy ? "saving…" : "save position"}
        </button>
        <button onClick={() => router.push("/positions")}
          className="rounded border border-ink-300 bg-white px-4 py-2 text-sm hover:bg-ink-50">
          cancel
        </button>
      </div>
    </div>
  );
}

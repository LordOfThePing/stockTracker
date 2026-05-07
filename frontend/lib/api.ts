const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type ConnectorHealth = {
  venue: string;
  enabled: boolean;
  last_success_at: string | null;
  last_error: string | null;
  last_sync_at: string | null;
};

export type BucketSubtotal = {
  currency_bucket: string;
  total_value: string;
  position_count: number;
};

export type VenueBreakdown = {
  venue: string;
  currency_bucket: string;
  total_value: string;
};

export type Overview = {
  buckets: BucketSubtotal[];
  by_venue: VenueBreakdown[];
  connectors: ConnectorHealth[];
};

export type Position = {
  id: number;
  source_venue: string;
  account_label: string;
  symbol: string;
  asset_type: string;
  quantity: string;
  quote_currency: string;
  currency_bucket: string;
  mark_price: string | null;
  cost_basis_per_unit: string | null;
  cost_basis_currency: string | null;
  market_value: string | null;
  pnl_absolute: string | null;
  pnl_pct: number | null;
  as_of_utc: string;
};

export type HistoryPoint = { ts_utc: string; total_value: string };
export type History = { currency_bucket: string; points: HistoryPoint[] };

export type InstrumentSearchResult = {
  feed: "binance" | "coingecko" | "stooq" | "none";
  feed_symbol: string;
  display_name: string;
  quote_currency: string | null;
};

async function jget<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
}

async function jpost<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
}

export const api = {
  overview: () => jget<Overview>("/api/overview"),
  positions: (qs?: Record<string, string>) =>
    jget<Position[]>(`/api/positions${qs ? `?${new URLSearchParams(qs)}` : ""}`),
  connectors: () => jget<ConnectorHealth[]>("/api/connectors"),
  history: (bucket: string, range: string) =>
    jget<History>(`/api/history?bucket=${encodeURIComponent(bucket)}&range=${range}`),
  refresh: (venue: string) => jpost<Record<string, string>>(`/api/refresh/${venue}`),
  searchInstruments: (q: string, feed: string) =>
    jget<InstrumentSearchResult[]>(`/api/instruments/search?q=${encodeURIComponent(q)}&feed=${feed}`),
  createManual: (body: unknown) => jpost<{ id: number }>("/api/manual/positions", body),
};

from datetime import datetime, timezone
from decimal import Decimal
import httpx

from ..schemas import InstrumentSearchResult

# Public, documented, no-auth: https://www.coingecko.com/en/api/documentation
_BASE = "https://api.coingecko.com/api/v3"


class CoinGeckoFeed:
    name = "coingecko"

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def get_quote(self, feed_symbol: str, vs_currency: str) -> Decimal | None:
        client = await self._get_client()
        r = await client.get(
            f"{_BASE}/simple/price",
            params={"ids": feed_symbol, "vs_currencies": vs_currency.lower()},
        )
        r.raise_for_status()
        data = r.json()
        node = data.get(feed_symbol)
        if not node:
            return None
        val = node.get(vs_currency.lower())
        return Decimal(str(val)) if val is not None else None

    async def get_history(
        self, feed_symbol: str, vs_currency: str, days: int
    ) -> list[tuple[datetime, Decimal]]:
        client = await self._get_client()
        r = await client.get(
            f"{_BASE}/coins/{feed_symbol}/market_chart",
            params={"vs_currency": vs_currency.lower(), "days": days},
        )
        r.raise_for_status()
        prices = r.json().get("prices", [])
        return [
            (datetime.fromtimestamp(ms / 1000, tz=timezone.utc), Decimal(str(p)))
            for ms, p in prices
        ]

    async def search(self, query: str) -> list[InstrumentSearchResult]:
        client = await self._get_client()
        r = await client.get(f"{_BASE}/search", params={"query": query})
        r.raise_for_status()
        coins = r.json().get("coins", [])[:20]
        return [
            InstrumentSearchResult(
                feed="coingecko",
                feed_symbol=c["id"],
                display_name=f"{c['name']} ({c['symbol'].upper()})",
                quote_currency=None,
            )
            for c in coins
        ]

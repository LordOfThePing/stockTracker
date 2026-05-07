"""Binance public-data feed.

Used for price history of held instruments (kline/candlestick endpoint).
Public endpoints, no authentication required.

Reference: https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-data
"""
from datetime import datetime, timezone
from decimal import Decimal

from ..binance_client import BinanceClient
from ..schemas import InstrumentSearchResult


class BinanceFeed:
    name = "binance"

    def __init__(self, client: BinanceClient | None = None):
        self._client = client or BinanceClient()

    async def get_quote(self, feed_symbol: str, vs_currency: str) -> Decimal | None:
        try:
            row = await self._client.public_get(
                "/api/v3/ticker/price", params={"symbol": feed_symbol}
            )
            return Decimal(row["price"]) if isinstance(row, dict) and "price" in row else None
        except Exception:
            return None

    async def get_history(
        self, feed_symbol: str, vs_currency: str, days: int
    ) -> list[tuple[datetime, Decimal]]:
        rows = await self._client.public_get(
            "/api/v3/klines",
            params={"symbol": feed_symbol, "interval": "1d", "limit": max(1, min(days, 1000))},
        )
        out: list[tuple[datetime, Decimal]] = []
        for r in rows:
            # kline tuple: [openTime, open, high, low, close, volume, closeTime, ...]
            try:
                ts = datetime.fromtimestamp(int(r[0]) / 1000, tz=timezone.utc)
                close = Decimal(str(r[4]))
                out.append((ts, close))
            except Exception:
                continue
        return out

    async def search(self, query: str) -> list[InstrumentSearchResult]:
        # Binance positions come from the adapter, not user search.
        return []

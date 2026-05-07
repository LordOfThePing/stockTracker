from datetime import datetime, timezone
from decimal import Decimal
import csv
import io
import httpx

from ..schemas import InstrumentSearchResult

# Public CSV endpoints, no auth required: https://stooq.com
# Quote:   https://stooq.com/q/l/?s=ggal.ar&f=sd2t2ohlcv&h&e=csv
# History: https://stooq.com/q/d/l/?s=ggal.ar&i=d  (daily, all available)
_QUOTE = "https://stooq.com/q/l/"
_HISTORY = "https://stooq.com/q/d/l/"


class StooqFeed:
    """Used for Argentine equities (e.g. ggal.ar, ypfd.ar) and any other
    equity Stooq covers. Stooq returns prices in the instrument's listed
    currency — for .ar tickers that's ARS.
    """

    name = "stooq"

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def get_quote(self, feed_symbol: str, vs_currency: str) -> Decimal | None:
        client = await self._get_client()
        r = await client.get(
            _QUOTE,
            params={"s": feed_symbol.lower(), "f": "sd2t2ohlcv", "h": "", "e": "csv"},
        )
        r.raise_for_status()
        rows = list(csv.DictReader(io.StringIO(r.text)))
        if not rows:
            return None
        close = rows[0].get("Close")
        if close in (None, "", "N/D"):
            return None
        try:
            return Decimal(close)
        except Exception:
            return None

    async def get_history(
        self, feed_symbol: str, vs_currency: str, days: int
    ) -> list[tuple[datetime, Decimal]]:
        client = await self._get_client()
        r = await client.get(_HISTORY, params={"s": feed_symbol.lower(), "i": "d"})
        r.raise_for_status()
        rows = list(csv.DictReader(io.StringIO(r.text)))
        out: list[tuple[datetime, Decimal]] = []
        for row in rows[-days:]:
            d = row.get("Date")
            close = row.get("Close")
            if not d or close in (None, "", "N/D"):
                continue
            try:
                ts = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                out.append((ts, Decimal(close)))
            except Exception:
                continue
        return out

    async def search(self, query: str) -> list[InstrumentSearchResult]:
        # Stooq has no documented JSON search endpoint. Return the literal query
        # so the user can confirm the symbol they meant; we'll validate it by
        # fetching a quote at insertion time.
        return [
            InstrumentSearchResult(
                feed="stooq",
                feed_symbol=query.lower(),
                display_name=f"{query.upper()} (Stooq, validate by fetching quote)",
                quote_currency=None,
            )
        ]

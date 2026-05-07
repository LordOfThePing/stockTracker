"""Binance Spot adapter (read-only).

Endpoints used (https://binance-docs.github.io/apidocs/spot/en/):
  - GET /api/v3/time             -- server-time sync, weight 1
  - GET /api/v3/account          -- spot balances, weight 20, signed
  - GET /api/v3/ticker/price     -- all prices in one call, weight 4

Cost basis is not provided by these endpoints, so manual entries are the only
way to set cost basis on Binance positions if you want P/L.
"""
from datetime import datetime, timezone
from decimal import Decimal
import logging

from ..binance_client import BinanceClient
from ..config import get_settings
from ..schemas import NormalizedPosition, ConnectorHealth

logger = logging.getLogger(__name__)


class BinanceAdapter:
    venue_id = "binance"

    def __init__(self, client: BinanceClient | None = None):
        settings = get_settings()
        if client is not None:
            self._client: BinanceClient | None = client
            self._enabled = True
        elif settings.binance_enabled:
            self._client = BinanceClient(settings.binance_api_key, settings.binance_api_secret)
            self._enabled = True
        else:
            self._client = None
            self._enabled = False

    async def health_check(self) -> ConnectorHealth:
        if not self._enabled:
            return ConnectorHealth(
                venue=self.venue_id, enabled=False,
                last_error="No API key configured. Add BINANCE_API_KEY/SECRET to .env.",
            )
        return ConnectorHealth(venue=self.venue_id, enabled=True)

    async def fetch_positions(self) -> list[NormalizedPosition]:
        if not self._enabled or self._client is None:
            raise RuntimeError("Binance adapter disabled: missing API credentials.")
        client = self._client

        await client.sync_server_time()
        account = await client.signed_get("/api/v3/account")

        held: dict[str, Decimal] = {}
        for b in account.get("balances", []):
            free = Decimal(b.get("free", "0") or "0")
            locked = Decimal(b.get("locked", "0") or "0")
            total = free + locked
            if total > 0:
                held[b["asset"]] = total

        if not held:
            return []

        all_tickers = await client.public_get("/api/v3/ticker/price")
        price_map: dict[str, Decimal] = {row["symbol"]: Decimal(row["price"]) for row in all_tickers}

        prices: dict[str, Decimal] = {"USDT": Decimal("1")}
        for asset in held:
            if asset == "USDT":
                continue
            p = price_map.get(f"{asset}USDT")
            if p is not None:
                prices[asset] = p

        now = datetime.now(timezone.utc)
        out: list[NormalizedPosition] = []
        for asset, qty in held.items():
            mark = prices.get(asset)
            out.append(NormalizedPosition(
                source_venue=self.venue_id,
                account_label="spot",
                symbol=asset,
                asset_type="crypto",
                quantity=qty,
                quote_currency="USDT",
                mark_price=mark,
                cost_basis_per_unit=None,
                cost_basis_currency=None,
                price_feed="binance",
                feed_symbol=f"{asset}USDT" if asset != "USDT" else "USDT",
                as_of_utc=now,
            ))
        return out

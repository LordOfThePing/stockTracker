"""Binance adapter (read-only).

Endpoints used:
  - GET  /api/v3/time
      https://binance-docs.github.io/apidocs/spot/en/#check-server-time
  - GET  /api/v3/account                       (signed; Spot balances)
      https://binance-docs.github.io/apidocs/spot/en/#account-information-user_data
  - POST /sapi/v1/asset/get-funding-asset      (signed; Funding/"Cripto" wallet)
      https://developers.binance.com/docs/wallet/asset/funding-wallet
  - GET  /api/v3/ticker/price                  (public; all prices in one call)

Spot positions get account_label="spot"; Funding positions get account_label="funding".
Earn/Margin/Futures wallets are NOT covered yet.

Cost basis is not provided by these endpoints, so manual entries remain the only
way to record cost basis on Binance positions for P/L.
"""
from datetime import datetime, timezone
from decimal import Decimal
import logging

from ..binance_client import BinanceClient
from ..config import get_settings
from ..schemas import NormalizedPosition, ConnectorHealth

logger = logging.getLogger(__name__)

# Fiat currencies Binance supports as wallet assets. Treated as their own quote
# currency with mark=1 so they land in their own bucket (e.g. ARS, EUR), instead
# of getting bucketed as USD-stables alongside actual stablecoins.
_FIAT_CODES = {
    "ARS", "BRL", "EUR", "GBP", "RUB", "TRY", "UAH", "ZAR",
    "AUD", "JPY", "MXN", "USD", "RON", "COP", "PEN", "PLN",
}


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

        # (account_label, asset) -> qty
        held: dict[tuple[str, str], Decimal] = {}

        # Spot wallet
        account = await client.signed_get("/api/v3/account")
        for b in account.get("balances", []):
            free = Decimal(b.get("free", "0") or "0")
            locked = Decimal(b.get("locked", "0") or "0")
            total = free + locked
            if total > 0:
                held[("spot", b["asset"])] = total

        # Funding ("Cripto") wallet — separate balance pool from Spot
        try:
            funding = await client.signed_post("/sapi/v1/asset/get-funding-asset")
        except Exception as e:
            logger.warning("Binance funding wallet fetch failed: %s", type(e).__name__)
            funding = []
        if isinstance(funding, list):
            for b in funding:
                free = Decimal(b.get("free", "0") or "0")
                locked = Decimal(b.get("locked", "0") or "0")
                freeze = Decimal(b.get("freeze", "0") or "0")
                withdrawing = Decimal(b.get("withdrawing", "0") or "0")
                total = free + locked + freeze + withdrawing
                if total > 0:
                    held[("funding", b["asset"])] = total

        if not held:
            return []

        all_tickers = await client.public_get("/api/v3/ticker/price")
        price_map: dict[str, Decimal] = {row["symbol"]: Decimal(row["price"]) for row in all_tickers}

        now = datetime.now(timezone.utc)
        out: list[NormalizedPosition] = []
        for (label, asset), qty in held.items():
            if asset == "USDT":
                quote_currency = "USDT"
                mark: Decimal | None = Decimal("1")
                feed_symbol = "USDT"
                asset_type = "crypto"
            elif asset in _FIAT_CODES:
                quote_currency = asset
                mark = Decimal("1")
                feed_symbol = asset
                asset_type = "other"
            else:
                quote_currency = "USDT"
                mark = price_map.get(f"{asset}USDT")
                feed_symbol = f"{asset}USDT"
                asset_type = "crypto"

            out.append(NormalizedPosition(
                source_venue=self.venue_id,
                account_label=label,
                symbol=asset,
                asset_type=asset_type,
                quantity=qty,
                quote_currency=quote_currency,
                mark_price=mark,
                cost_basis_per_unit=None,
                cost_basis_currency=None,
                price_feed="binance",
                feed_symbol=feed_symbol,
                as_of_utc=now,
            ))
        return out

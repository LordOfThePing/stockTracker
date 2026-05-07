from ..schemas import NormalizedPosition, ConnectorHealth


class BinanceAdapter:
    """Phase 2: implement signed read-only Binance Spot integration.

    Endpoints planned (per Binance API docs):
      - GET /api/v3/time      — server-time sync for clock-skew correction
      - GET /api/v3/account   — Spot balances (signed, HMAC-SHA256)
      - GET /api/v3/ticker/price?symbols=[...]  — batch prices for held assets

    Read-only API key required. Trading / withdrawals / futures must be disabled.
    """

    venue_id = "binance"

    async def health_check(self) -> ConnectorHealth:
        return ConnectorHealth(venue=self.venue_id, enabled=False, last_error="not yet implemented (Phase 2)")

    async def fetch_positions(self) -> list[NormalizedPosition]:
        raise NotImplementedError("Binance adapter lands in Phase 2.")

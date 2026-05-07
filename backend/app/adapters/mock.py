from datetime import datetime, timezone
from decimal import Decimal

from ..schemas import NormalizedPosition, ConnectorHealth


class MockAdapter:
    """Returns a small synthetic portfolio so the UI has data on day one
    without any network access."""

    venue_id = "mock"

    async def health_check(self) -> ConnectorHealth:
        return ConnectorHealth(venue=self.venue_id, enabled=True)

    async def fetch_positions(self) -> list[NormalizedPosition]:
        now = datetime.now(timezone.utc)
        return [
            NormalizedPosition(
                source_venue=self.venue_id, account_label="spot",
                symbol="BTC", asset_type="crypto",
                quantity=Decimal("0.05"), quote_currency="USDT",
                mark_price=Decimal("68000"),
                cost_basis_per_unit=Decimal("45000"), cost_basis_currency="USDT",
                price_feed="none", feed_symbol=None, as_of_utc=now,
            ),
            NormalizedPosition(
                source_venue=self.venue_id, account_label="spot",
                symbol="ETH", asset_type="crypto",
                quantity=Decimal("0.4"), quote_currency="USDT",
                mark_price=Decimal("3500"),
                cost_basis_per_unit=Decimal("2000"), cost_basis_currency="USDT",
                price_feed="none", feed_symbol=None, as_of_utc=now,
            ),
            NormalizedPosition(
                source_venue=self.venue_id, account_label="spot",
                symbol="USDT", asset_type="crypto",
                quantity=Decimal("250"), quote_currency="USDT",
                mark_price=Decimal("1"),
                cost_basis_per_unit=Decimal("1"), cost_basis_currency="USDT",
                price_feed="none", feed_symbol=None, as_of_utc=now,
            ),
        ]

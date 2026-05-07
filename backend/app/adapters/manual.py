from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import ManualPosition, Instrument, PriceHistory
from ..schemas import NormalizedPosition, ConnectorHealth


class ManualAdapter:
    """Reads user-entered manual positions and pairs each with the latest known
    mark from the price_history table. Pricing itself is done by the price-feed
    layer; this adapter just stitches state together.
    """

    venue_id = "manual"

    def __init__(self, db: Session):
        self.db = db

    async def health_check(self) -> ConnectorHealth:
        return ConnectorHealth(venue=self.venue_id, enabled=True)

    async def fetch_positions(self) -> list[NormalizedPosition]:
        rows = self.db.query(ManualPosition).all()
        out: list[NormalizedPosition] = []
        now = datetime.now(timezone.utc)
        for r in rows:
            inst: Instrument = r.instrument
            last_price = (
                self.db.query(PriceHistory)
                .filter(PriceHistory.instrument_id == inst.id)
                .order_by(PriceHistory.ts_utc.desc())
                .first()
            )
            out.append(NormalizedPosition(
                source_venue=self.venue_id,
                account_label=r.account_label,
                symbol=inst.symbol,
                asset_type=inst.asset_type,  # type: ignore[arg-type]
                quantity=r.quantity,
                quote_currency=inst.quote_currency,
                mark_price=last_price.close_price if last_price else None,
                cost_basis_per_unit=r.cost_basis_per_unit,
                cost_basis_currency=r.cost_basis_currency,
                price_feed=inst.price_feed,  # type: ignore[arg-type]
                feed_symbol=inst.feed_symbol,
                as_of_utc=last_price.ts_utc if last_price else now,
            ))
        return out

from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Position, Instrument
from ..schemas import PositionOut

router = APIRouter()


def _to_out(pos: Position, inst: Instrument) -> PositionOut:
    market_value = (pos.quantity * pos.mark_price) if pos.mark_price is not None else None
    pnl_abs: Decimal | None = None
    pnl_pct: float | None = None
    if pos.mark_price is not None and pos.cost_basis_per_unit is not None:
        pnl_abs = (pos.mark_price - pos.cost_basis_per_unit) * pos.quantity
        if pos.cost_basis_per_unit != 0:
            pnl_pct = float((pos.mark_price - pos.cost_basis_per_unit) / pos.cost_basis_per_unit)
    return PositionOut(
        id=pos.id,
        source_venue=pos.source_venue,
        account_label=pos.account_label,
        symbol=inst.symbol,
        asset_type=inst.asset_type,
        quantity=pos.quantity,
        quote_currency=pos.quote_currency,
        currency_bucket=inst.currency_bucket,
        mark_price=pos.mark_price,
        cost_basis_per_unit=pos.cost_basis_per_unit,
        cost_basis_currency=pos.cost_basis_currency,
        market_value=market_value,
        pnl_absolute=pnl_abs,
        pnl_pct=pnl_pct,
        as_of_utc=pos.as_of_utc,
    )


@router.get("/api/positions", response_model=list[PositionOut])
async def list_positions(
    venue: str | None = Query(None),
    asset_type: str | None = Query(None),
    bucket: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[PositionOut]:
    q = db.query(Position, Instrument).join(Instrument, Instrument.id == Position.instrument_id)
    if venue:
        q = q.filter(Position.source_venue == venue)
    if asset_type:
        q = q.filter(Instrument.asset_type == asset_type)
    if bucket:
        q = q.filter(Instrument.currency_bucket == bucket)
    return [_to_out(p, i) for p, i in q.all()]

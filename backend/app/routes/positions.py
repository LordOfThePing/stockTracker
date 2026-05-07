from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Position, Instrument, ManualPosition
from ..schemas import PositionOut

router = APIRouter()


def _to_out(pos: Position, inst: Instrument, manual_id: int | None) -> PositionOut:
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
        manual_position_id=manual_id,
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
    rows = q.all()

    # Build (instrument_id, account_label) -> ManualPosition.id map so the UI
    # can wire delete/edit to the right backing record.
    manual_id_by_key: dict[tuple[int, str], int] = {}
    if any(p.source_venue == "manual" for p, _ in rows):
        for m in db.query(ManualPosition).all():
            manual_id_by_key[(m.instrument_id, m.account_label)] = m.id

    out: list[PositionOut] = []
    for p, i in rows:
        manual_id = (
            manual_id_by_key.get((p.instrument_id, p.account_label))
            if p.source_venue == "manual" else None
        )
        out.append(_to_out(p, i, manual_id))
    return out

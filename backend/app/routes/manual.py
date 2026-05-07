from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..currency import bucket_for
from ..db import get_db
from ..models import Instrument, ManualPosition
from ..schemas import ManualPositionIn, ManualPositionPatch

router = APIRouter()


def _ensure_instrument(db: Session, body: ManualPositionIn) -> Instrument:
    inst = (
        db.query(Instrument)
        .filter(Instrument.symbol == body.symbol, Instrument.price_feed == body.price_feed)
        .one_or_none()
    )
    if inst is None:
        inst = Instrument(
            symbol=body.symbol,
            asset_type=body.asset_type,
            quote_currency=body.quote_currency,
            currency_bucket=bucket_for(body.quote_currency),
            price_feed=body.price_feed,
            feed_symbol=body.feed_symbol,
        )
        db.add(inst)
        db.flush()
    return inst


@router.post("/api/manual/positions")
async def create_manual_position(body: ManualPositionIn, db: Session = Depends(get_db)) -> dict:
    inst = _ensure_instrument(db, body)
    mp = ManualPosition(
        instrument_id=inst.id,
        account_label=body.account_label,
        quantity=body.quantity,
        cost_basis_per_unit=body.cost_basis_per_unit,
        cost_basis_currency=body.cost_basis_currency,
        opened_at=body.opened_at,
        notes=body.notes,
    )
    db.add(mp)
    db.commit()
    return {"id": mp.id, "instrument_id": inst.id}


@router.get("/api/manual/positions")
async def list_manual_positions(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(ManualPosition).all()
    return [
        {
            "id": r.id,
            "symbol": r.instrument.symbol,
            "feed": r.instrument.price_feed,
            "feed_symbol": r.instrument.feed_symbol,
            "quantity": str(r.quantity),
            "cost_basis_per_unit": str(r.cost_basis_per_unit),
            "cost_basis_currency": r.cost_basis_currency,
            "account_label": r.account_label,
            "opened_at": r.opened_at.isoformat() if r.opened_at else None,
            "notes": r.notes,
        }
        for r in rows
    ]


@router.patch("/api/manual/positions/{mp_id}")
async def patch_manual_position(mp_id: int, body: ManualPositionPatch, db: Session = Depends(get_db)) -> dict:
    mp = db.get(ManualPosition, mp_id)
    if mp is None:
        raise HTTPException(status_code=404, detail="not found")
    if body.account_label is not None:
        mp.account_label = body.account_label
    if body.symbol is not None:
        mp.instrument.symbol = body.symbol
    if body.asset_type is not None:
        mp.instrument.asset_type = body.asset_type
    if body.quote_currency is not None:
        mp.instrument.quote_currency = body.quote_currency
        mp.instrument.currency_bucket = bucket_for(body.quote_currency)
    if body.quantity is not None:
        mp.quantity = body.quantity
    if body.cost_basis_per_unit is not None:
        mp.cost_basis_per_unit = body.cost_basis_per_unit
    if body.cost_basis_currency is not None:
        mp.cost_basis_currency = body.cost_basis_currency
    if body.notes is not None:
        mp.notes = body.notes
    db.commit()
    return {"id": mp.id}


@router.delete("/api/manual/positions/{mp_id}")
async def delete_manual_position(mp_id: int, db: Session = Depends(get_db)) -> dict:
    mp = db.get(ManualPosition, mp_id)
    if mp is None:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(mp)
    db.commit()
    return {"ok": True}

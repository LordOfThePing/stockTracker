from datetime import datetime, timedelta, timezone
from collections import defaultdict
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Snapshot
from ..schemas import HistoryOut, HistoryPoint

router = APIRouter()


_RANGE_DAYS = {"1d": 1, "1w": 7, "1m": 30, "ytd": None, "max": None}


@router.get("/api/history", response_model=HistoryOut)
async def get_history(
    bucket: str = Query(...),
    range: str = Query("1m"),
    db: Session = Depends(get_db),
) -> HistoryOut:
    days = _RANGE_DAYS.get(range, 30)
    q = db.query(Snapshot).filter(Snapshot.currency_bucket == bucket)
    if range == "ytd":
        cutoff = datetime(datetime.now(timezone.utc).year, 1, 1, tzinfo=timezone.utc)
        q = q.filter(Snapshot.ts_utc >= cutoff)
    elif days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        q = q.filter(Snapshot.ts_utc >= cutoff)
    rows = q.order_by(Snapshot.ts_utc.asc()).all()

    grouped: dict[datetime, Decimal] = defaultdict(lambda: Decimal(0))
    for s in rows:
        grouped[s.ts_utc] += s.total_value
    points = [HistoryPoint(ts_utc=ts, total_value=v) for ts, v in sorted(grouped.items())]
    return HistoryOut(currency_bucket=bucket, points=points)

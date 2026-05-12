from decimal import Decimal
from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Position, Instrument, SyncRun
from ..schemas import OverviewOut, BucketSubtotal, VenueBreakdown, ConnectorHealth
from ..sync import get_adapters

router = APIRouter()


@router.get("/api/overview", response_model=OverviewOut)
async def get_overview(db: Session = Depends(get_db)) -> OverviewOut:
    rows = (
        db.query(Position, Instrument)
        .join(Instrument, Instrument.id == Position.instrument_id)
        .all()
    )

    bucket_total: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    bucket_count: dict[str, int] = defaultdict(int)
    provider_total: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal(0))

    for pos, inst in rows:
        bucket_count[inst.currency_bucket] += 1
        if pos.mark_price is None:
            continue
        mv = pos.quantity * pos.mark_price
        bucket_total[inst.currency_bucket] += mv
        label = pos.account_label or pos.source_venue
        label = label.split("::")[-1] if "::" in label else label
        provider_total[(label, inst.currency_bucket)] += mv

    buckets = [
        BucketSubtotal(currency_bucket=b, total_value=bucket_total[b], position_count=bucket_count[b])
        for b in sorted(bucket_count.keys())
    ]
    by_venue = [
        VenueBreakdown(provider=p, currency_bucket=b, total_value=t)
        for (p, b), t in sorted(provider_total.items())
    ]

    connectors: list[ConnectorHealth] = []
    for adapter in get_adapters(db):
        h = await adapter.health_check()
        last = (
            db.query(SyncRun)
            .filter(SyncRun.venue == adapter.venue_id)
            .order_by(SyncRun.started_at.desc())
            .first()
        )
        if last:
            h.last_sync_at = last.finished_at or last.started_at
            if last.status == "ok":
                h.last_success_at = last.finished_at or last.started_at
            elif last.error_message:
                h.last_error = last.error_message
        connectors.append(h)

    return OverviewOut(buckets=buckets, by_venue=by_venue, connectors=connectors)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import SyncRun
from ..schemas import ConnectorHealth
from ..sync import get_adapters

router = APIRouter()


@router.get("/api/connectors", response_model=list[ConnectorHealth])
async def list_connectors(db: Session = Depends(get_db)) -> list[ConnectorHealth]:
    out: list[ConnectorHealth] = []
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
        out.append(h)
    return out

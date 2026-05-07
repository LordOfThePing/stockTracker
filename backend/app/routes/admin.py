from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Account, Position, SyncRun, Snapshot

router = APIRouter()


@router.delete("/api/admin/venue/{venue}")
async def purge_venue(venue: str, db: Session = Depends(get_db)) -> dict:
    """Delete every row tied to a venue: positions, accounts, sync_runs.
    Snapshots are kept so historical charts stay continuous.

    Use after disabling a connector (e.g. mock) to clear the data it left behind.
    """
    venue = venue.lower()
    if not venue:
        raise HTTPException(status_code=400, detail="venue required")

    pos_count = db.query(Position).filter(Position.source_venue == venue).delete(synchronize_session=False)
    acc_count = db.query(Account).filter(Account.venue == venue).delete(synchronize_session=False)
    run_count = db.query(SyncRun).filter(SyncRun.venue == venue).delete(synchronize_session=False)
    db.commit()
    return {
        "venue": venue,
        "positions_deleted": pos_count,
        "accounts_deleted": acc_count,
        "sync_runs_deleted": run_count,
    }


@router.delete("/api/admin/snapshots/{venue}")
async def purge_snapshots(venue: str, db: Session = Depends(get_db)) -> dict:
    """Drop snapshots for a venue too, if you also want to wipe history."""
    venue = venue.lower()
    n = db.query(Snapshot).filter(Snapshot.venue == venue).delete(synchronize_session=False)
    db.commit()
    return {"venue": venue, "snapshots_deleted": n}

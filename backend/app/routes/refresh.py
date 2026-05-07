from fastapi import APIRouter, HTTPException

from ..sync import run_sync

router = APIRouter()


@router.post("/api/refresh/{venue}")
async def refresh(venue: str) -> dict[str, str]:
    venue = venue.lower()
    if venue == "all":
        return await run_sync()
    result = await run_sync(venue=venue)
    if result.get(venue) == "unknown_venue":
        raise HTTPException(status_code=404, detail=f"Unknown venue: {venue}")
    return result

from fastapi import APIRouter, Query

from ..feeds.coingecko import CoinGeckoFeed
from ..feeds.stooq import StooqFeed
from ..schemas import InstrumentSearchResult

router = APIRouter()


@router.get("/api/instruments/search", response_model=list[InstrumentSearchResult])
async def search_instruments(
    q: str = Query(..., min_length=1),
    feed: str = Query("coingecko"),
) -> list[InstrumentSearchResult]:
    if feed == "coingecko":
        return await CoinGeckoFeed().search(q)
    if feed == "stooq":
        return await StooqFeed().search(q)
    return []

from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from ..schemas import InstrumentSearchResult


@runtime_checkable
class PriceFeed(Protocol):
    name: str

    async def get_quote(self, feed_symbol: str, vs_currency: str) -> Decimal | None: ...

    async def get_history(
        self, feed_symbol: str, vs_currency: str, days: int
    ) -> list[tuple[datetime, Decimal]]: ...

    async def search(self, query: str) -> list[InstrumentSearchResult]: ...

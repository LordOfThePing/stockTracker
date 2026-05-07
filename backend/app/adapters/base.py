from typing import Protocol, runtime_checkable
from ..schemas import NormalizedPosition, ConnectorHealth


@runtime_checkable
class SourceAdapter(Protocol):
    venue_id: str

    async def health_check(self) -> ConnectorHealth: ...

    async def fetch_positions(self) -> list[NormalizedPosition]: ...

from ..schemas import NormalizedPosition, ConnectorHealth


class IEBPlusAdapter:
    """Stub. IEB+ (ARG) has no documented public API for personal automation.

    Use manual entry until that changes.
    """

    venue_id = "iebplus"

    async def health_check(self) -> ConnectorHealth:
        return ConnectorHealth(venue=self.venue_id, enabled=False, last_error="No official API; use manual entry.")

    async def fetch_positions(self) -> list[NormalizedPosition]:
        raise NotImplementedError("No official API; stub per kickoff.")

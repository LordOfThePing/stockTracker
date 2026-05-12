from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


AssetType = Literal["crypto", "equity", "other"]
PriceFeedName = Literal["binance", "coingecko", "stooq", "none"]


class NormalizedPosition(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_venue: str
    account_label: str
    symbol: str
    asset_type: AssetType
    quantity: Decimal
    quote_currency: str
    mark_price: Decimal | None = None
    cost_basis_per_unit: Decimal | None = None
    cost_basis_currency: str | None = None
    price_feed: PriceFeedName = "none"
    feed_symbol: str | None = None
    as_of_utc: datetime


class ConnectorHealth(BaseModel):
    venue: str
    enabled: bool
    last_success_at: datetime | None = None
    last_error: str | None = None
    last_sync_at: datetime | None = None


class ManualPositionIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=64)
    asset_type: AssetType
    quote_currency: str = Field(min_length=1, max_length=16)
    price_feed: PriceFeedName
    feed_symbol: str = Field(min_length=1, max_length=64)
    account_label: str = Field(default="manual", min_length=1, max_length=64)
    quantity: Decimal
    cost_basis_per_unit: Decimal
    cost_basis_currency: str = Field(min_length=1, max_length=16)
    opened_at: datetime | None = None
    notes: str | None = None


class ManualPositionPatch(BaseModel):
    account_label: str | None = None
    symbol: str | None = None
    asset_type: AssetType | None = None
    quote_currency: str | None = None
    quantity: Decimal | None = None
    cost_basis_per_unit: Decimal | None = None
    cost_basis_currency: str | None = None
    notes: str | None = None


class PositionOut(BaseModel):
    id: int
    source_venue: str
    account_label: str
    symbol: str
    asset_type: str
    quantity: Decimal
    quote_currency: str
    currency_bucket: str
    mark_price: Decimal | None
    cost_basis_per_unit: Decimal | None
    cost_basis_currency: str | None
    market_value: Decimal | None
    pnl_absolute: Decimal | None
    pnl_pct: float | None
    as_of_utc: datetime
    manual_position_id: int | None = None


class BucketSubtotal(BaseModel):
    currency_bucket: str
    total_value: Decimal
    position_count: int


class VenueBreakdown(BaseModel):
    source_venue: str
    account_label: str
    currency_bucket: str
    total_value: Decimal


class OverviewOut(BaseModel):
    buckets: list[BucketSubtotal]
    by_venue: list[VenueBreakdown]
    connectors: list[ConnectorHealth]


class HistoryPoint(BaseModel):
    ts_utc: datetime
    total_value: Decimal


class HistoryOut(BaseModel):
    currency_bucket: str
    points: list[HistoryPoint]


class InstrumentSearchResult(BaseModel):
    feed: PriceFeedName
    feed_symbol: str
    display_name: str
    quote_currency: str | None = None

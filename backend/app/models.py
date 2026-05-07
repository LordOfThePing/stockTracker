from datetime import datetime
from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal

from .db import Base


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venue: Mapped[str] = mapped_column(String(32), index=True)
    label: Mapped[str] = mapped_column(String(64))
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    __table_args__ = (UniqueConstraint("venue", "label", name="uq_accounts_venue_label"),)


class Instrument(Base):
    __tablename__ = "instruments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    asset_type: Mapped[str] = mapped_column(String(16))
    quote_currency: Mapped[str] = mapped_column(String(16))
    currency_bucket: Mapped[str] = mapped_column(String(32), index=True)
    price_feed: Mapped[str] = mapped_column(String(16))
    feed_symbol: Mapped[str] = mapped_column(String(64))
    __table_args__ = (UniqueConstraint("symbol", "price_feed", name="uq_instruments_symbol_feed"),)


class ManualPosition(Base):
    __tablename__ = "manual_positions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"))
    account_label: Mapped[str] = mapped_column(String(64), default="manual")
    quantity: Mapped[Decimal] = mapped_column(Numeric(36, 18))
    cost_basis_per_unit: Mapped[Decimal] = mapped_column(Numeric(36, 18))
    cost_basis_currency: Mapped[str] = mapped_column(String(16))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    instrument: Mapped[Instrument] = relationship(Instrument, lazy="joined")


class Position(Base):
    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_venue: Mapped[str] = mapped_column(String(32), index=True)
    account_label: Mapped[str] = mapped_column(String(64))
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(36, 18))
    quote_currency: Mapped[str] = mapped_column(String(16))
    mark_price: Mapped[Decimal | None] = mapped_column(Numeric(36, 18), nullable=True)
    cost_basis_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(36, 18), nullable=True)
    cost_basis_currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    as_of_utc: Mapped[datetime] = mapped_column(DateTime)

    instrument: Mapped[Instrument] = relationship(Instrument, lazy="joined")

    __table_args__ = (
        UniqueConstraint(
            "source_venue", "account_label", "instrument_id",
            name="uq_positions_source_account_instrument",
        ),
    )


class SyncRun(Base):
    __tablename__ = "sync_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venue: Mapped[str] = mapped_column(String(32), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16))
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class Snapshot(Base):
    __tablename__ = "snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts_utc: Mapped[datetime] = mapped_column(DateTime, index=True)
    currency_bucket: Mapped[str] = mapped_column(String(32), index=True)
    venue: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    total_value: Mapped[Decimal] = mapped_column(Numeric(36, 18))


class PriceHistory(Base):
    __tablename__ = "price_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"))
    ts_utc: Mapped[datetime] = mapped_column(DateTime)
    close_price: Mapped[Decimal] = mapped_column(Numeric(36, 18))
    source: Mapped[str] = mapped_column(String(16))
    __table_args__ = (
        UniqueConstraint("instrument_id", "ts_utc", "source", name="uq_price_history_instrument_ts_source"),
        Index("ix_price_history_instrument_ts", "instrument_id", "ts_utc"),
    )


class RawPayload(Base):
    __tablename__ = "raw_payloads"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sync_run_id: Mapped[int] = mapped_column(ForeignKey("sync_runs.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(64))
    body_redacted: Mapped[str] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(DateTime)

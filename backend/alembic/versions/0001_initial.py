"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("venue", sa.String(32), nullable=False),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.UniqueConstraint("venue", "label", name="uq_accounts_venue_label"),
    )
    op.create_index("ix_accounts_venue", "accounts", ["venue"])

    op.create_table(
        "instruments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("asset_type", sa.String(16), nullable=False),
        sa.Column("quote_currency", sa.String(16), nullable=False),
        sa.Column("currency_bucket", sa.String(32), nullable=False),
        sa.Column("price_feed", sa.String(16), nullable=False),
        sa.Column("feed_symbol", sa.String(64), nullable=False),
        sa.UniqueConstraint("symbol", "price_feed", name="uq_instruments_symbol_feed"),
    )
    op.create_index("ix_instruments_symbol", "instruments", ["symbol"])
    op.create_index("ix_instruments_currency_bucket", "instruments", ["currency_bucket"])

    op.create_table(
        "manual_positions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("instrument_id", sa.Integer(), sa.ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_label", sa.String(64), nullable=False, server_default="manual"),
        sa.Column("quantity", sa.Numeric(36, 18), nullable=False),
        sa.Column("cost_basis_per_unit", sa.Numeric(36, 18), nullable=False),
        sa.Column("cost_basis_currency", sa.String(16), nullable=False),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_venue", sa.String(32), nullable=False),
        sa.Column("account_label", sa.String(64), nullable=False),
        sa.Column("instrument_id", sa.Integer(), sa.ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Numeric(36, 18), nullable=False),
        sa.Column("quote_currency", sa.String(16), nullable=False),
        sa.Column("mark_price", sa.Numeric(36, 18), nullable=True),
        sa.Column("cost_basis_per_unit", sa.Numeric(36, 18), nullable=True),
        sa.Column("cost_basis_currency", sa.String(16), nullable=True),
        sa.Column("as_of_utc", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "source_venue", "account_label", "instrument_id",
            name="uq_positions_source_account_instrument",
        ),
    )
    op.create_index("ix_positions_source_venue", "positions", ["source_venue"])

    op.create_table(
        "sync_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("venue", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_sync_runs_venue", "sync_runs", ["venue"])

    op.create_table(
        "snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ts_utc", sa.DateTime(), nullable=False),
        sa.Column("currency_bucket", sa.String(32), nullable=False),
        sa.Column("venue", sa.String(32), nullable=True),
        sa.Column("total_value", sa.Numeric(36, 18), nullable=False),
    )
    op.create_index("ix_snapshots_ts_utc", "snapshots", ["ts_utc"])
    op.create_index("ix_snapshots_currency_bucket", "snapshots", ["currency_bucket"])
    op.create_index("ix_snapshots_venue", "snapshots", ["venue"])

    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("instrument_id", sa.Integer(), sa.ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ts_utc", sa.DateTime(), nullable=False),
        sa.Column("close_price", sa.Numeric(36, 18), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.UniqueConstraint("instrument_id", "ts_utc", "source", name="uq_price_history_instrument_ts_source"),
    )
    op.create_index("ix_price_history_instrument_ts", "price_history", ["instrument_id", "ts_utc"])

    op.create_table(
        "raw_payloads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sync_run_id", sa.Integer(), sa.ForeignKey("sync_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("body_redacted", sa.Text(), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("raw_payloads")
    op.drop_index("ix_price_history_instrument_ts", table_name="price_history")
    op.drop_table("price_history")
    op.drop_index("ix_snapshots_venue", table_name="snapshots")
    op.drop_index("ix_snapshots_currency_bucket", table_name="snapshots")
    op.drop_index("ix_snapshots_ts_utc", table_name="snapshots")
    op.drop_table("snapshots")
    op.drop_index("ix_sync_runs_venue", table_name="sync_runs")
    op.drop_table("sync_runs")
    op.drop_index("ix_positions_source_venue", table_name="positions")
    op.drop_table("positions")
    op.drop_table("manual_positions")
    op.drop_index("ix_instruments_currency_bucket", table_name="instruments")
    op.drop_index("ix_instruments_symbol", table_name="instruments")
    op.drop_table("instruments")
    op.drop_index("ix_accounts_venue", table_name="accounts")
    op.drop_table("accounts")

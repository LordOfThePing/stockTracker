from datetime import datetime, timezone
from decimal import Decimal
import logging
import traceback

from sqlalchemy.orm import Session

from .adapters.base import SourceAdapter
from .adapters.binance import BinanceAdapter
from .adapters.manual import ManualAdapter
from .adapters.mock import MockAdapter
from .config import get_settings
from .currency import bucket_for
from .db import session_scope
from .feeds.base import PriceFeed
from .feeds.binance import BinanceFeed
from .feeds.coingecko import CoinGeckoFeed
from .feeds.stooq import StooqFeed
from .models import Account, Instrument, ManualPosition, Position, PriceHistory, Snapshot, SyncRun
from .redaction import redact_string
from .schemas import NormalizedPosition

logger = logging.getLogger(__name__)


def get_feeds() -> dict[str, PriceFeed]:
    return {
        "coingecko": CoinGeckoFeed(),
        "stooq": StooqFeed(),
        "binance": BinanceFeed(),
    }


def get_adapters(db: Session, *, include_binance: bool | None = None) -> list[SourceAdapter]:
    settings = get_settings()
    if include_binance is None:
        include_binance = settings.binance_enabled

    adapters: list[SourceAdapter] = [ManualAdapter(db)]
    if settings.enable_mock:
        adapters.append(MockAdapter())
    if include_binance:
        adapters.append(BinanceAdapter())
    return adapters


def _vs_currency_for(feed_name: str, quote_currency: str) -> str:
    if feed_name == "coingecko":
        # CoinGecko vs_currency 'usd' covers both USD and USDT for our purposes.
        if quote_currency.upper() in {"USDT", "USDC", "BUSD", "FDUSD", "USD"}:
            return "usd"
        return quote_currency.lower()
    if feed_name == "binance":
        # Symbol already encodes the pair (e.g. BTCUSDT); vs_currency is unused.
        return quote_currency.lower()
    # Stooq returns price in the instrument's listed currency; vs_currency unused.
    return quote_currency.lower()


async def refresh_prices(db: Session) -> int:
    feeds = get_feeds()
    insts = db.query(Instrument).filter(Instrument.price_feed != "none").all()
    written = 0
    now = datetime.now(timezone.utc)
    for inst in insts:
        feed = feeds.get(inst.price_feed)
        if not feed:
            continue
        try:
            price = await feed.get_quote(inst.feed_symbol, _vs_currency_for(inst.price_feed, inst.quote_currency))
        except Exception as e:
            logger.warning("price fetch failed feed=%s sym=%s err=%s", inst.price_feed, inst.feed_symbol, redact_string(str(e)))
            continue
        if price is None:
            continue
        db.add(PriceHistory(
            instrument_id=inst.id,
            ts_utc=now,
            close_price=price,
            source=inst.price_feed,
        ))
        written += 1
    db.commit()
    return written


def _ensure_instrument(db: Session, np: NormalizedPosition) -> Instrument:
    feed = np.price_feed or "none"
    inst = (
        db.query(Instrument)
        .filter(Instrument.symbol == np.symbol, Instrument.price_feed == feed)
        .one_or_none()
    )
    if inst is None:
        inst = Instrument(
            symbol=np.symbol,
            asset_type=np.asset_type,
            quote_currency=np.quote_currency,
            currency_bucket=bucket_for(np.quote_currency),
            price_feed=feed,
            feed_symbol=np.feed_symbol or np.symbol,
        )
        db.add(inst)
        db.flush()
    return inst


def _upsert_account(db: Session, venue: str, label: str) -> Account:
    acct = db.query(Account).filter(Account.venue == venue, Account.label == label).one_or_none()
    if acct is None:
        acct = Account(venue=venue, label=label)
        db.add(acct)
        db.flush()
    return acct


def _upsert_position(db: Session, np: NormalizedPosition, inst: Instrument) -> None:
    pos = (
        db.query(Position)
        .filter(
            Position.source_venue == np.source_venue,
            Position.account_label == np.account_label,
            Position.instrument_id == inst.id,
        )
        .one_or_none()
    )
    if pos is None:
        pos = Position(
            source_venue=np.source_venue,
            account_label=np.account_label,
            instrument_id=inst.id,
            quantity=np.quantity,
            quote_currency=np.quote_currency,
            mark_price=np.mark_price,
            cost_basis_per_unit=np.cost_basis_per_unit,
            cost_basis_currency=np.cost_basis_currency,
            as_of_utc=np.as_of_utc,
        )
        db.add(pos)
    else:
        pos.quantity = np.quantity
        pos.quote_currency = np.quote_currency
        pos.mark_price = np.mark_price
        pos.cost_basis_per_unit = np.cost_basis_per_unit
        pos.cost_basis_currency = np.cost_basis_currency
        pos.as_of_utc = np.as_of_utc


def _prune_stale_positions(
    db: Session,
    venue_id: str,
    keep_keys: set[tuple[str, int]],
) -> None:
    existing = db.query(Position).filter(Position.source_venue == venue_id).all()
    for pos in existing:
        key = (pos.account_label, pos.instrument_id)
        if key not in keep_keys:
            db.delete(pos)


def _write_snapshots(db: Session) -> None:
    now = datetime.now(timezone.utc)
    rows = (
        db.query(Position, Instrument)
        .join(Instrument, Instrument.id == Position.instrument_id)
        .all()
    )
    grouped: dict[tuple[str, str], Decimal] = {}
    for pos, inst in rows:
        if pos.mark_price is None:
            continue
        bucket = inst.currency_bucket
        key = (bucket, pos.source_venue)
        grouped[key] = grouped.get(key, Decimal(0)) + (pos.quantity * pos.mark_price)
    for (bucket, venue), total in grouped.items():
        db.add(Snapshot(ts_utc=now, currency_bucket=bucket, venue=venue, total_value=total))


async def run_sync(venue: str | None = None) -> dict[str, str]:
    """Run a sync for one venue (or all). Returns {venue: status}."""
    results: dict[str, str] = {}
    with session_scope() as db:
        adapters = get_adapters(db)
        if venue is not None:
            adapters = [a for a in adapters if a.venue_id == venue]
            if not adapters:
                return {venue: "unknown_venue"}

        # Refresh marks before reading manual positions, so they see fresh prices.
        await refresh_prices(db)

        for adapter in adapters:
            run = SyncRun(
                venue=adapter.venue_id,
                started_at=datetime.now(timezone.utc),
                status="running",
            )
            db.add(run)
            db.flush()
            try:
                positions = await adapter.fetch_positions()
                keep_keys: set[tuple[str, int]] = set()
                for np in positions:
                    inst = _ensure_instrument(db, np)
                    keep_keys.add((np.account_label, inst.id))
                    _upsert_account(db, np.source_venue, np.account_label)
                    _upsert_position(db, np, inst)
                _prune_stale_positions(db, adapter.venue_id, keep_keys)
                run.status = "ok"
                results[adapter.venue_id] = "ok"
            except NotImplementedError as e:
                run.status = "skipped"
                run.error_message = redact_string(str(e))
                results[adapter.venue_id] = "skipped"
            except Exception as e:
                run.status = "error"
                run.error_message = redact_string(traceback.format_exc(limit=5))
                results[adapter.venue_id] = "error"
                logger.warning("sync failed venue=%s err=%s", adapter.venue_id, redact_string(str(e)))
            finally:
                run.finished_at = datetime.now(timezone.utc)

        _write_snapshots(db)

    return results

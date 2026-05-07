import asyncio
import logging
import random
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import get_settings
from .sync import run_sync

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


async def _tick():
    settings = get_settings()
    jitter = random.randint(0, max(0, settings.sync_jitter_seconds))
    await asyncio.sleep(jitter)
    try:
        results = await run_sync()
        logger.info("scheduled sync done: %s", results)
    except Exception as e:
        logger.exception("scheduled sync failed: %s", e)


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    settings = get_settings()
    sched = AsyncIOScheduler()
    sched.add_job(
        _tick,
        "interval",
        seconds=settings.sync_interval_seconds,
        id="portfolio_sync",
        max_instances=1,
        coalesce=True,
    )
    sched.start()
    _scheduler = sched
    return sched


def stop_scheduler():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None

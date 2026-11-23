"""In-process weekly scheduler (single uvicorn worker => runs exactly once)."""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import PULSE_CRON

log = logging.getLogger("scheduler")
_sched: BackgroundScheduler | None = None


def _job() -> None:
    from pipeline import weekly
    try:
        rid = weekly.run(trigger="schedule")
        log.info("scheduled pulse run started id=%s", rid)
    except RuntimeError as e:
        log.warning("scheduled pulse skipped: %s", e)


def start() -> None:
    global _sched
    if _sched:
        return
    _sched = BackgroundScheduler(timezone="Asia/Kolkata")
    _sched.add_job(_job, CronTrigger.from_crontab(PULSE_CRON, timezone="Asia/Kolkata"), id="weekly_pulse",
                   misfire_grace_time=3600, coalesce=True)
    _sched.start()
    log.info("scheduler started cron=%s", PULSE_CRON)


def next_run() -> str | None:
    if not _sched:
        return None
    j = _sched.get_job("weekly_pulse")
    return j.next_run_time.isoformat() if j and j.next_run_time else None


def shutdown() -> None:
    if _sched:
        _sched.shutdown(wait=False)

import asyncio
import logging

from db import SessionLocal
from services.app_settings import get_schedule_settings, update_schedule_settings

logger = logging.getLogger(__name__)

_config = get_schedule_settings()
_task: asyncio.Task | None = None


def get_schedule_config() -> dict:
    current = get_schedule_settings()
    _config.update(current)
    return {
        **_config,
        'running': _task is not None and not _task.done(),
    }


def update_schedule_config(enabled: bool | None, interval_hours: float | None):
    _config.update(update_schedule_settings(enabled, interval_hours))
    _restart_scheduler()


async def _scheduler_loop():
    while True:
        interval = _config['interval_hours'] * 3600
        await asyncio.sleep(interval)
        if not _config['enabled']:
            continue
        try:
            db = SessionLocal()
            try:
                from routes.collector import run_collect_and_analyze
                from services.clawprofile_runtime import auto_promote_patterns, export_active_clawprofile_snapshot
                result = run_collect_and_analyze(db)
                promoted = auto_promote_patterns(db)
                snapshot = export_active_clawprofile_snapshot(db)
                logger.info(f'Scheduled collection completed: {result.get("mining_count", 0)} patterns mined')
                if promoted:
                    logger.info(f'Auto-promoted {len(promoted)} patterns into active ClawProfile')
                if snapshot:
                    logger.info(f'Exported ClawProfile snapshot to {snapshot.get("snapshot_path")}')
            finally:
                db.close()
        except Exception as e:
            logger.warning(f'Scheduled collection failed: {e}')


def start_scheduler():
    global _task
    if _task and not _task.done():
        return
    _config.update(get_schedule_settings())
    loop = asyncio.get_event_loop()
    _task = loop.create_task(_scheduler_loop())
    logger.info(f'Scheduler started: interval={_config["interval_hours"]}h, enabled={_config["enabled"]}')


def _restart_scheduler():
    global _task
    if _task and not _task.done():
        _task.cancel()
        _task = None
    if _config['enabled']:
        try:
            start_scheduler()
        except RuntimeError:
            pass

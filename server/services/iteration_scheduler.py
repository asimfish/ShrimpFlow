import asyncio
import logging

from services.design_iteration import run_iteration_loop

logger = logging.getLogger(__name__)

_task = None


def start_iteration_scheduler():
    global _task
    if _task and not _task.done():
        return
    loop = asyncio.get_event_loop()
    _task = loop.create_task(run_iteration_loop())
    logger.info("Iteration scheduler started: interval=1h")

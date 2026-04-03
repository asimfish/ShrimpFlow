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
                from services.memory_lifecycle import apply_decay
                from services.consolidation_service import run_consolidation
                from services.relation_discovery import run_relation_discovery
                result = run_collect_and_analyze(db)
                promoted = auto_promote_patterns(db)
                snapshot = export_active_clawprofile_snapshot(db)
                # Phase 1: 每次采集周期后执行记忆衰减
                decay_result = apply_decay(db)
                logger.info(f'Scheduled collection completed: {result.get("mining_count", 0)} patterns mined')
                if promoted:
                    logger.info(f'Auto-promoted {len(promoted)} patterns into active ClawProfile')
                if snapshot:
                    logger.info(f'Exported ClawProfile snapshot to {snapshot.get("snapshot_path")}')
                if decay_result.get('decayed'):
                    logger.info(f'Memory decay: {decay_result["decayed"]} patterns updated, {decay_result["lifecycle_changes"]} lifecycle changes')
                # Phase 2: 合并周期
                consolidation_result = run_consolidation(db)
                if consolidation_result.get('prune', {}).get('pruned') or consolidation_result.get('merge', {}).get('merged') or consolidation_result.get('mature', {}).get('matured'):
                    logger.info(f'Consolidation: {consolidation_result}')
                # Phase 3: 关系发现
                relation_result = run_relation_discovery(db)
                if relation_result.get('total'):
                    logger.info(f'Relation discovery: {relation_result}')

                # Phase 4: Claw 自进化 — CoT 推理挖掘 + Workflow 重建 + 品味更新
                try:
                    from services.claw_generator import run_claw_generation
                    from services.cot_miner import compute_taste_dimensions
                    claw_result = run_claw_generation(db)
                    taste = compute_taste_dimensions(db, 336)
                    claw_total = claw_result.get('total_generated', 0)
                    if claw_total:
                        logger.info(f'🧬 Claw evolution: {claw_total} new candidates '
                                    f'(CoT={len(claw_result.get("cot_skills",[]))}, '
                                    f'Workflow={len(claw_result.get("workflow_patterns",[]))})')
                    logger.info(f'🎯 Taste snapshot: rigor={taste.get("rigor",0)} '
                                f'elegance={taste.get("elegance",0)} '
                                f'novelty={taste.get("novelty",0)} '
                                f'simplicity={taste.get("simplicity",0)} '
                                f'reproducibility={taste.get("reproducibility",0)}')
                except Exception as e:
                    logger.warning(f'Claw evolution failed: {e}')
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

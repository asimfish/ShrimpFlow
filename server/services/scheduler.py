import asyncio
import json
import logging
import time
from collections.abc import Callable
from typing import Any

from db import SessionLocal
from services.app_settings import get_schedule_settings, update_schedule_settings
from services.taste_model import auto_confirm_patterns, get_active_taste_profile

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


def _load_cycle_taste_context(db) -> dict[str, Any]:
    """
    Load taste profile for this scheduler cycle. On failure, returns empty context
    so the rest of the pipeline falls back to legacy behavior.
    """
    try:
        profile = get_active_taste_profile(db)
    except Exception as e:
        logger.debug('Taste profile unavailable for scheduler cycle: %s', e)
        return {
            'prioritized_categories': [],
            'min_promote_confidence': 88,
            'profile': None,
        }

    cats: dict[str, int] = {}
    raw = getattr(profile, 'preferred_categories', None) or ''
    if isinstance(raw, str) and raw.strip():
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                cats = {str(k): int(v) for k, v in loaded.items() if isinstance(v, (int, float))}
        except (json.JSONDecodeError, TypeError, ValueError):
            cats = {}

    prioritized = [
        name for name, _w in sorted(cats.items(), key=lambda item: (-item[1], item[0]))
    ][:8]

    min_promote = 88
    th = getattr(profile, 'preferred_confidence_threshold', None)
    if th is not None:
        try:
            t_int = int(th)
            if 1 <= t_int <= 100:
                min_promote = t_int
        except (TypeError, ValueError):
            pass

    return {
        'prioritized_categories': prioritized,
        'min_promote_confidence': min_promote,
        'profile': profile,
    }


def _auto_promote_patterns_with_min_confidence(db, min_confidence: int) -> list[dict]:
    """Same behavior as clawprofile_runtime.auto_promote_patterns but with a configurable confidence floor."""
    from models.pattern import BehaviorPattern
    from services.clawprofile_runtime import _active_profile

    profile = _active_profile(db)
    if not profile:
        return []

    promoted = []
    rows = db.query(BehaviorPattern).filter(
        BehaviorPattern.profile_id == profile.id,
        BehaviorPattern.source == 'auto',
        BehaviorPattern.status == 'learning',
        BehaviorPattern.confidence >= min_confidence,
        BehaviorPattern.evidence_count >= 6,
    ).all()

    now = time.strftime('%Y-%m-%d', time.localtime())
    for row in rows:
        row.status = 'confirmed'
        evolution = json.loads(row.evolution) if row.evolution else []
        evolution.append({
            'date': now,
            'confidence': row.confidence,
            'event_description': '系统夜间自动晋级为 confirmed',
        })
        row.evolution = json.dumps(evolution, ensure_ascii=False)
        promoted.append({
            'id': row.id,
            'name': row.name,
            'confidence': row.confidence,
            'evidence_count': row.evidence_count,
        })

    if promoted:
        db.commit()
    return promoted


def _install_taste_mining_patch(prioritized_categories: list[str]) -> Callable[[], None]:
    """
    Soft hint: after semantic refinement, slightly raise confidence for patterns in
    taste-favored categories (does not drop or hard-filter other categories).
    Returns a no-arg restore callback.
    """
    if not prioritized_categories:
        return lambda: None

    import services.pattern_mining as pm

    preferred = set(prioritized_categories)
    original = pm.semantic_refine_patterns

    def wrapped(patterns):
        out = original(patterns)
        if not isinstance(out, list):
            return out
        for item in out:
            if not isinstance(item, dict):
                continue
            cat = item.get('category')
            if cat in preferred:
                base = int(item.get('confidence') or 0)
                item['confidence'] = min(99, base + 4)
        return out

    pm.semantic_refine_patterns = wrapped

    def restore():
        pm.semantic_refine_patterns = original

    return restore


async def _scheduler_loop():
    while True:
        interval = _config['interval_hours'] * 3600
        await asyncio.sleep(interval)
        if not _config['enabled']:
            continue
        try:
            db = SessionLocal()
            try:
                taste_ctx = _load_cycle_taste_context(db)
                prioritized = taste_ctx['prioritized_categories']
                min_promote = taste_ctx['min_promote_confidence']

                if prioritized:
                    logger.info('Taste-driven: prioritizing %s mining', prioritized)

                if min_promote != 88:
                    logger.info(
                        'Taste-driven: auto-promote minimum confidence set to %s (was default 88)',
                        min_promote,
                    )

                restore_mining = _install_taste_mining_patch(
                    prioritized if prioritized else [],
                )
                try:
                    from routes.collector import run_collect_and_analyze
                    from services.clawprofile_runtime import export_active_clawprofile_snapshot
                    from services.memory_lifecycle import apply_decay
                    from services.consolidation_service import run_consolidation
                    from services.relation_discovery import run_relation_discovery
                    result = run_collect_and_analyze(db)
                finally:
                    restore_mining()

                promoted = _auto_promote_patterns_with_min_confidence(db, min_promote)
                taste_confirm = auto_confirm_patterns(db)
                snapshot = export_active_clawprofile_snapshot(db)
                # Phase 1: 每次采集周期后执行记忆衰减
                decay_result = apply_decay(db)
                logger.info(f'Scheduled collection completed: {result.get("mining_count", 0)} patterns mined')
                if promoted:
                    logger.info(f'Auto-promoted {len(promoted)} patterns into active ClawProfile (min_confidence={min_promote})')
                tc_conf = int(taste_confirm.get('confirmed') or 0)
                if tc_conf:
                    logger.info(
                        'Taste-driven: taste auto-confirm confirmed %s pattern(s) '
                        '(deferred=%s, collect_more=%s)',
                        tc_conf,
                        taste_confirm.get('deferred'),
                        taste_confirm.get('collect_more'),
                    )
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
                    from models.pattern import BehaviorPattern

                    claw_result = run_claw_generation(db)
                    pref_set = set(prioritized) if prioritized else set()
                    boosted = 0
                    if pref_set:
                        for key in ('cot_skills', 'workflow_patterns'):
                            for item in claw_result.get(key, []) or []:
                                pid = item.get('id')
                                if not pid:
                                    continue
                                row = db.query(BehaviorPattern).filter(BehaviorPattern.id == pid).first()
                                if row and (row.category or '') in pref_set:
                                    row.confidence = min(99, int(row.confidence or 0) + 3)
                                    boosted += 1
                        if boosted:
                            db.commit()
                            logger.info(
                                'Taste-driven: soft boost on %s Claw candidate(s) in categories %s',
                                boosted,
                                sorted(pref_set),
                            )
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

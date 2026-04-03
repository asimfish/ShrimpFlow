import json
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from db import get_db
from models.event import DevEvent
from models.pattern import BehaviorPattern
from models.skill import Skill
from models.openclaw import OpenClawSession
from models.digest import DailySummary
from schemas.stats import StatsOverview

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsOverview)
def get_stats(db: Session = Depends(get_db)):
    real_events = db.query(DevEvent).filter(~DevEvent.tags.contains('"seed"'))
    total_events = real_events.with_entities(func.count(DevEvent.id)).scalar() or 0
    total_skills = db.query(func.count(Skill.id)).scalar() or 0
    total_projects = real_events.with_entities(func.count(distinct(DevEvent.project))).scalar() or 0
    total_openclaw_sessions = db.query(func.count(OpenClawSession.id)).scalar() or 0
    total_claude_sessions = db.query(func.count(OpenClawSession.id)).filter(
        OpenClawSession.tags.contains('"claude_code"')
    ).scalar() or 0
    total_codex_sessions = db.query(func.count(OpenClawSession.id)).filter(
        OpenClawSession.tags.contains('"codex"')
    ).scalar() or 0
    total_git_commits = db.query(func.count(DevEvent.id)).filter(
        DevEvent.source == 'git',
        ~DevEvent.tags.contains('"seed"'),
    ).scalar() or 0
    total_days = db.query(func.count(DailySummary.id)).scalar() or 0

    project_row = (
        db.query(DevEvent.project, func.count(DevEvent.id).label('cnt'))
        .filter(~DevEvent.tags.contains('"seed"'))
        .group_by(DevEvent.project)
        .order_by(func.count(DevEvent.id).desc())
        .first()
    )
    most_active_project = project_row[0] if project_row else ''

    dates = [
        r[0] for r in
        db.query(DailySummary.date)
        .filter(DailySummary.event_count > 0)
        .order_by(DailySummary.date.desc())
        .all()
    ]
    streak = 0
    if dates:
        prev = datetime.strptime(dates[0], '%Y-%m-%d')
        streak = 1
        for d in dates[1:]:
            cur = datetime.strptime(d, '%Y-%m-%d')
            if (prev - cur).days == 1:
                streak += 1
                prev = cur
            else:
                break

    return {
        'total_events': total_events, 'total_days': total_days,
        'total_projects': total_projects, 'total_skills': total_skills,
        'total_openclaw_sessions': total_openclaw_sessions,
        'total_claude_sessions': total_claude_sessions,
        'total_codex_sessions': total_codex_sessions,
        'total_git_commits': total_git_commits,
        'most_active_project': most_active_project, 'streak_days': streak,
    }


@router.get("/memory/health")
def get_memory_health_api(db: Session = Depends(get_db)):
    from services.memory_lifecycle import get_memory_health
    return get_memory_health(db)


@router.post("/memory/decay")
def trigger_decay_api(db: Session = Depends(get_db)):
    from services.memory_lifecycle import apply_decay
    return apply_decay(db)


@router.post("/memory/consolidate")
def trigger_consolidation_api(db: Session = Depends(get_db)):
    from services.consolidation_service import run_consolidation
    return run_consolidation(db)


@router.post("/memory/full-cycle")
def full_memory_cycle_api(db: Session = Depends(get_db)):
    """完整记忆巩固周期: 采集 health_before -> decay -> consolidate -> discover -> health_after -> diff"""
    from services.memory_lifecycle import get_memory_health, apply_decay
    from services.consolidation_service import run_consolidation
    from services.relation_discovery import run_relation_discovery
    from services.evidence_ledger import compress_all_evidence
    import time as _time

    started_at = _time.time()
    health_before = get_memory_health(db)
    decay_result = apply_decay(db)
    consolidation_result = run_consolidation(db)
    relation_result = run_relation_discovery(db)
    compression_result = compress_all_evidence(db)
    health_after = get_memory_health(db)
    elapsed = round(_time.time() - started_at, 2)

    # 计算 diff
    def _diff(before, after):
        if before == after:
            return '-'
        delta = after - before if isinstance(after, (int, float)) else None
        if delta is not None:
            sign = '+' if delta > 0 else ''
            return f'{sign}{round(delta, 2)}'
        return f'{before} -> {after}'

    health_diff = {
        'grade': {'before': health_before['grade'], 'after': health_after['grade'], 'change': _diff(health_before['grade'], health_after['grade'])},
        'score': {'before': health_before['score'], 'after': health_after['score'], 'change': _diff(health_before['score'], health_after['score'])},
        'avg_heat': {'before': health_before['avg_heat'], 'after': health_after['avg_heat'], 'change': _diff(health_before['avg_heat'], health_after['avg_heat'])},
        'total': {'before': health_before['total'], 'after': health_after['total'], 'change': _diff(health_before['total'], health_after['total'])},
        'confirmed': {'before': health_before['confirmed'], 'after': health_after['confirmed'], 'change': _diff(health_before['confirmed'], health_after['confirmed'])},
    }

    # 生命周期 diff
    lifecycle_diff = {}
    all_states = set(list(health_before.get('by_lifecycle', {}).keys()) + list(health_after.get('by_lifecycle', {}).keys()))
    for state in sorted(all_states):
        b = health_before.get('by_lifecycle', {}).get(state, 0)
        a = health_after.get('by_lifecycle', {}).get(state, 0)
        lifecycle_diff[state] = {'before': b, 'after': a, 'change': _diff(b, a)}

    # 瓶颈分析
    bottlenecks = []
    if health_after['avg_heat'] < 20:
        bottlenecks.append({'metric': 'avg_heat', 'value': health_after['avg_heat'], 'desc': '平均热度过低，大部分模式处于冷却状态，建议多查看和使用已确认的模式'})
    confirmed_ratio = health_after['confirmed'] / max(health_after['total'], 1)
    if confirmed_ratio < 0.3:
        bottlenecks.append({'metric': 'confirmation_ratio', 'value': f'{round(confirmed_ratio * 100)}%', 'desc': f'确认率仅 {round(confirmed_ratio * 100)}%，{health_after["total"] - health_after["confirmed"]} 个模式仍在学习中'})
    archived_count = health_after.get('by_lifecycle', {}).get('archived', 0)
    if archived_count > health_after['total'] * 0.2:
        bottlenecks.append({'metric': 'archived_ratio', 'value': archived_count, 'desc': f'{archived_count} 个已归档模式占比过高，建议清理或复习激活'})
    if not health_after.get('issues'):
        bottlenecks.append({'metric': 'clean', 'value': 'OK', 'desc': '记忆系统运行健康，无明显瓶颈'})

    return {
        'elapsed_seconds': elapsed,
        'health_before': health_before,
        'health_after': health_after,
        'health_diff': health_diff,
        'lifecycle_diff': lifecycle_diff,
        'decay': decay_result,
        'consolidation': consolidation_result,
        'relations': relation_result,
        'compression': compression_result,
        'bottlenecks': bottlenecks,
        'issues': health_after.get('issues', []),
    }


@router.get("/stats/flywheel-trend")
def get_flywheel_trend(db: Session = Depends(get_db)):
    """按天聚合飞轮指标：累计 pattern 数、累计确认数、平均 confidence，用于折线图"""
    patterns = db.query(BehaviorPattern).all()
    if not patterns:
        return {'points': []}

    daily: dict[str, dict] = defaultdict(lambda: {'created': 0, 'confirmed': 0, 'conf_sum': 0, 'conf_count': 0})

    for p in patterns:
        if not p.created_at:
            continue
        day = datetime.fromtimestamp(p.created_at).strftime('%Y-%m-%d')
        daily[day]['created'] += 1
        daily[day]['conf_sum'] += p.confidence
        daily[day]['conf_count'] += 1

        evo = []
        try:
            evo = json.loads(p.evolution) if p.evolution else []
        except (json.JSONDecodeError, TypeError):
            pass
        for entry in evo:
            event_desc = entry.get('event_description', '')
            if '确认' in event_desc or 'confirm' in event_desc.lower():
                evo_date = entry.get('date', '')
                if evo_date and len(evo_date) >= 5:
                    if len(evo_date) <= 5:
                        evo_date = f'2025-{evo_date}'
                    daily[evo_date]['confirmed'] += 1
                break

        if p.status == 'confirmed' and day not in [e.get('date', '') for e in evo]:
            daily[day]['confirmed'] += 1

    if not daily:
        return {'points': []}

    sorted_days = sorted(daily.keys())
    cum_total = 0
    cum_confirmed = 0
    cum_conf_sum = 0
    cum_conf_count = 0
    points = []

    for day in sorted_days:
        d = daily[day]
        cum_total += d['created']
        cum_confirmed += d['confirmed']
        cum_conf_sum += d['conf_sum']
        cum_conf_count += d['conf_count']
        avg_conf = round(cum_conf_sum / cum_conf_count) if cum_conf_count > 0 else 0
        points.append({
            'date': day,
            'total': cum_total,
            'confirmed': cum_confirmed,
            'avg_confidence': avg_conf,
        })

    return {'points': points}

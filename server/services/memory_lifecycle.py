"""
记忆生命周期管理 (Phase 1)
灵感来自 NeuralMemory 的热度模型 + 衰减/强化机制。

核心概念:
- heat_score: 热度评分, 综合 access_count + recency + confidence
- lifecycle_state: active -> warm -> cool -> compressed -> archived
- decay: 随时间衰减, 不活跃的模式热度下降
- reinforcement: 每次被访问/使用时热度上升
"""
import json
import logging
import math
import time

from sqlalchemy.orm import Session

from models.pattern import (
    BehaviorPattern,
    LIFECYCLE_ACTIVE,
    LIFECYCLE_WARM,
    LIFECYCLE_COOL,
    LIFECYCLE_COMPRESSED,
    LIFECYCLE_ARCHIVED,
)

logger = logging.getLogger(__name__)

# 衰减参数
DECAY_RATE = 0.02  # 每小时衰减系数 (比 NeuralMemory 的 0.1 温和)
DECAY_FLOOR = 1.0  # 热度下限, 不会衰减到 0

# 强化参数
REINFORCEMENT_BASE = 5.0  # 每次访问的基础强化值
REINFORCEMENT_CAP = 100.0  # 热度上限

# 生命周期阈值 (天)
LIFECYCLE_THRESHOLDS = {
    LIFECYCLE_ACTIVE: 7,
    LIFECYCLE_WARM: 30,
    LIFECYCLE_COOL: 90,
    LIFECYCLE_COMPRESSED: 180,
}

DAY_SECONDS = 86400
HOUR_SECONDS = 3600


def compute_heat_score(pattern: BehaviorPattern, now: int = 0) -> float:
    """计算热度: access_frequency * recency_boost + confidence_factor"""
    if not now:
        now = int(time.time())

    access_count = pattern.access_count or 0
    last_accessed = pattern.last_accessed_at or pattern.created_at or now
    confidence = pattern.confidence or 0

    # recency_boost: 指数衰减, 越近访问越高
    hours_since_access = max(0, (now - last_accessed)) / HOUR_SECONDS
    recency_boost = math.exp(-0.005 * hours_since_access)  # 半衰期 ~138 小时 (~6天)

    # access_factor: 对数缩放, 避免高频访问过度膨胀
    access_factor = math.log2(access_count + 1) * 8

    # confidence_factor: 高置信度的模式天然热度更高
    confidence_factor = confidence * 0.3

    heat = access_factor * recency_boost + confidence_factor
    return max(DECAY_FLOOR, min(REINFORCEMENT_CAP, round(heat, 2)))


def determine_lifecycle_state(pattern: BehaviorPattern, now: int = 0) -> str:
    """根据年龄和热度判断生命周期状态"""
    if not now:
        now = int(time.time())

    created = pattern.created_at or now
    age_days = (now - created) / DAY_SECONDS
    heat = pattern.heat_score or 0
    last_accessed = pattern.last_accessed_at or created
    days_since_access = (now - last_accessed) / DAY_SECONDS

    # confirmed 模式享有保护: 至少 warm
    is_confirmed = pattern.status == 'confirmed'

    # 高热度或新模式 -> active
    if age_days < LIFECYCLE_THRESHOLDS[LIFECYCLE_ACTIVE] or heat > 60:
        return LIFECYCLE_ACTIVE

    # 14 天内访问过且不太老 -> warm
    if days_since_access < 14 and age_days < LIFECYCLE_THRESHOLDS[LIFECYCLE_WARM]:
        return LIFECYCLE_WARM

    # confirmed 模式最低 warm
    if is_confirmed and age_days < LIFECYCLE_THRESHOLDS[LIFECYCLE_COOL]:
        return LIFECYCLE_WARM

    if age_days < LIFECYCLE_THRESHOLDS[LIFECYCLE_COOL]:
        return LIFECYCLE_COOL if not is_confirmed else LIFECYCLE_WARM

    if age_days < LIFECYCLE_THRESHOLDS[LIFECYCLE_COMPRESSED]:
        return LIFECYCLE_COMPRESSED if not is_confirmed else LIFECYCLE_COOL

    return LIFECYCLE_ARCHIVED if not is_confirmed else LIFECYCLE_COMPRESSED


def record_access(db: Session, pattern_id: int) -> dict | None:
    """强化: 模式被访问/查看/使用时调用"""
    pattern = db.query(BehaviorPattern).filter(BehaviorPattern.id == pattern_id).first()
    if not pattern:
        return None

    now = int(time.time())
    old_heat = pattern.heat_score or 0

    pattern.access_count = (pattern.access_count or 0) + 1
    pattern.last_accessed_at = now
    pattern.heat_score = compute_heat_score(pattern, now)
    pattern.lifecycle_state = determine_lifecycle_state(pattern, now)

    db.commit()
    logger.debug(f'Reinforced pattern {pattern_id}: heat {old_heat:.1f} -> {pattern.heat_score:.1f}')
    return {
        'pattern_id': pattern_id,
        'heat_before': old_heat,
        'heat_after': pattern.heat_score,
        'lifecycle_state': pattern.lifecycle_state,
        'access_count': pattern.access_count,
    }


def apply_decay(db: Session) -> dict:
    """衰减: 定时任务调用, 对所有模式执行热度衰减 + 生命周期迁移"""
    now = int(time.time())
    patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.status.in_(['learning', 'confirmed']),
    ).all()

    decayed = 0
    lifecycle_changes = 0

    for p in patterns:
        old_heat = p.heat_score or 50.0
        old_state = p.lifecycle_state or LIFECYCLE_ACTIVE

        # 重算热度 (自然包含时间衰减)
        new_heat = compute_heat_score(p, now)

        # 额外衰减: 长期未访问的模式加速衰减
        last_accessed = p.last_accessed_at or p.created_at or now
        hours_idle = (now - last_accessed) / HOUR_SECONDS
        if hours_idle > 168:  # 超过 7 天未访问
            idle_penalty = min(5.0, (hours_idle - 168) * DECAY_RATE)
            new_heat = max(DECAY_FLOOR, new_heat - idle_penalty)

        new_state = determine_lifecycle_state(p, now)

        if abs(new_heat - old_heat) > 0.5 or new_state != old_state:
            p.heat_score = new_heat
            p.lifecycle_state = new_state
            decayed += 1
            if new_state != old_state:
                lifecycle_changes += 1
                # 记录生命周期变迁到 evolution
                try:
                    evo = json.loads(p.evolution) if p.evolution else []
                except (json.JSONDecodeError, TypeError):
                    evo = []
                evo.append({
                    'date': time.strftime('%m-%d'),
                    'confidence': p.confidence,
                    'event_description': f'lifecycle: {old_state} -> {new_state}',
                })
                p.evolution = json.dumps(evo[-20:], ensure_ascii=False)

    if decayed:
        db.commit()

    logger.info(f'Decay applied: {decayed} patterns updated, {lifecycle_changes} lifecycle changes')
    return {
        'total_patterns': len(patterns),
        'decayed': decayed,
        'lifecycle_changes': lifecycle_changes,
    }


def get_memory_health(db: Session) -> dict:
    """记忆系统健康评分 (灵感来自 NeuralMemory 的 brain health)"""
    now = int(time.time())
    patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.status.in_(['learning', 'confirmed']),
    ).all()

    if not patterns:
        return {'score': 0, 'grade': 'F', 'total': 0, 'by_lifecycle': {}, 'issues': ['没有任何模式']}

    by_lifecycle = {}
    total_heat = 0.0
    stale_count = 0
    orphan_count = 0
    issues = []

    for p in patterns:
        state = p.lifecycle_state or LIFECYCLE_ACTIVE
        by_lifecycle[state] = by_lifecycle.get(state, 0) + 1
        total_heat += (p.heat_score or 0)

        # 检测问题
        last_acc = p.last_accessed_at or p.created_at or now
        if (now - last_acc) > 60 * DAY_SECONDS:
            stale_count += 1
        if (p.evidence_count or 0) == 0:
            orphan_count += 1

    avg_heat = total_heat / len(patterns)

    # 评分维度 (满分 100)
    # 1. 热度分布 (30分): 高平均热度 = 健康
    heat_score = min(30, avg_heat * 0.6)
    # 2. 活跃比例 (25分): active+warm 占比高 = 健康
    active_warm = by_lifecycle.get(LIFECYCLE_ACTIVE, 0) + by_lifecycle.get(LIFECYCLE_WARM, 0)
    active_ratio = active_warm / len(patterns)
    vitality_score = active_ratio * 25
    # 3. 证据覆盖 (20分): 无证据的模式越少越好
    orphan_ratio = orphan_count / len(patterns) if patterns else 1
    evidence_score = (1 - orphan_ratio) * 20
    # 4. 新鲜度 (15分): 陈旧模式越少越好
    stale_ratio = stale_count / len(patterns) if patterns else 1
    freshness_score = (1 - stale_ratio) * 15
    # 5. 确认比例 (10分)
    confirmed = sum(1 for p in patterns if p.status == 'confirmed')
    confirm_ratio = confirmed / len(patterns) if patterns else 0
    confirm_score = confirm_ratio * 10

    total_score = round(heat_score + vitality_score + evidence_score + freshness_score + confirm_score)
    total_score = max(0, min(100, total_score))

    # A-F 等级
    if total_score >= 85:
        grade = 'A'
    elif total_score >= 70:
        grade = 'B'
    elif total_score >= 55:
        grade = 'C'
    elif total_score >= 40:
        grade = 'D'
    else:
        grade = 'F'

    if stale_count > 0:
        issues.append(f'{stale_count} 个模式超过 60 天未访问')
    if orphan_count > 0:
        issues.append(f'{orphan_count} 个模式没有证据支撑')
    archived = by_lifecycle.get(LIFECYCLE_ARCHIVED, 0)
    if archived > len(patterns) * 0.3:
        issues.append(f'{archived} 个模式已归档, 建议清理')

    return {
        'score': total_score,
        'grade': grade,
        'total': len(patterns),
        'confirmed': confirmed,
        'avg_heat': round(avg_heat, 1),
        'by_lifecycle': by_lifecycle,
        'breakdown': {
            'heat': round(heat_score, 1),
            'vitality': round(vitality_score, 1),
            'evidence': round(evidence_score, 1),
            'freshness': round(freshness_score, 1),
            'confirmation': round(confirm_score, 1),
        },
        'issues': issues,
    }

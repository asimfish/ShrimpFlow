"""
模式关系发现服务 (Phase 3)
自动发现模式之间的语义关系: CAUSED_BY, LEADS_TO, FOLLOWS, CONTRADICTS, SIMILAR_TO, REINFORCES。

关系来源:
1. deep_mining 的 error_recovery -> CAUSED_BY
2. 用户确认/拒绝行为链 -> LEADS_TO / CONTRADICTS
3. 同一 episode 中共现的模式 -> REINFORCES
4. 名称/描述相似 -> SIMILAR_TO
5. workflow_habit 中的顺序 -> FOLLOWS
"""
import json
import logging
import time
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from models.pattern import BehaviorPattern, PatternRelation

logger = logging.getLogger(__name__)


def _text_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _get_or_update_relation(
    db: Session,
    source_id: int,
    target_id: int,
    relation_type: str,
    weight: float,
    description: str,
) -> PatternRelation:
    """获取已有关系或创建新关系, 如果已存在则增强权重"""
    existing = db.query(PatternRelation).filter(
        PatternRelation.source_pattern_id == source_id,
        PatternRelation.target_pattern_id == target_id,
        PatternRelation.relation_type == relation_type,
    ).first()

    now = int(time.time())
    if existing:
        # 强化: 权重取平均后微增
        existing.weight = min(1.0, (existing.weight + weight) / 2 + 0.05)
        existing.updated_at = now
        return existing

    rel = PatternRelation(
        source_pattern_id=source_id,
        target_pattern_id=target_id,
        relation_type=relation_type,
        weight=round(weight, 3),
        evidence_description=description,
        created_at=now,
        updated_at=now,
    )
    db.add(rel)
    return rel


def discover_similar_relations(db: Session, threshold: float = 0.65) -> int:
    """发现 SIMILAR_TO 关系: 基于名称+描述相似度"""
    patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.status.in_(['learning', 'confirmed']),
    ).all()

    count = 0
    for i, pa in enumerate(patterns):
        for pb in patterns[i + 1:]:
            if pa.category != pb.category:
                continue
            name_sim = _text_similarity(pa.name or '', pb.name or '')
            desc_sim = _text_similarity(pa.description or '', pb.description or '')
            avg_sim = (name_sim * 0.6 + desc_sim * 0.4)
            if avg_sim >= threshold:
                _get_or_update_relation(
                    db, pa.id, pb.id, 'SIMILAR_TO', avg_sim,
                    f'name_sim={name_sim:.2f}, desc_sim={desc_sim:.2f}',
                )
                count += 1
    if count:
        db.commit()
    return count


def discover_temporal_relations(db: Session) -> int:
    """发现 FOLLOWS 关系: 基于模式在 deep_mining 中的顺序"""
    patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.status.in_(['learning', 'confirmed']),
        BehaviorPattern.category == 'coding',
    ).order_by(BehaviorPattern.created_at.asc()).all()

    if len(patterns) < 2:
        return 0

    count = 0
    for i in range(len(patterns) - 1):
        pa = patterns[i]
        pb = patterns[i + 1]
        if not pa.created_at or not pb.created_at:
            continue
        # 如果两个模式在同一次挖掘中被发现 (间隔 < 60s), 说明有时序关系
        gap = abs((pb.created_at or 0) - (pa.created_at or 0))
        if gap < 60:
            _get_or_update_relation(
                db, pa.id, pb.id, 'FOLLOWS', 0.6,
                f'同批次挖掘, gap={gap}s',
            )
            count += 1
    if count:
        db.commit()
    return count


def discover_confirmation_relations(db: Session) -> int:
    """发现 LEADS_TO / CONTRADICTS 关系: 基于用户确认/拒绝行为链"""
    confirmed = db.query(BehaviorPattern).filter(
        BehaviorPattern.status == 'confirmed',
    ).order_by(BehaviorPattern.created_at.asc()).all()

    rejected = db.query(BehaviorPattern).filter(
        BehaviorPattern.status == 'rejected',
    ).all()

    count = 0
    # LEADS_TO: 连续确认的模式
    for i in range(len(confirmed) - 1):
        pa = confirmed[i]
        pb = confirmed[i + 1]
        # 检查 user_feedback 时间戳是否接近
        fb_a = json.loads(pa.user_feedback) if pa.user_feedback else []
        fb_b = json.loads(pb.user_feedback) if pb.user_feedback else []
        if not fb_a or not fb_b:
            continue
        last_a = fb_a[-1].get('ts', 0)
        last_b = fb_b[-1].get('ts', 0)
        if 0 < abs(last_b - last_a) < 300:  # 5 分钟内连续确认
            _get_or_update_relation(
                db, pa.id, pb.id, 'LEADS_TO', 0.7,
                f'连续确认, gap={abs(last_b - last_a)}s',
            )
            count += 1

    # CONTRADICTS: 同类别中确认和拒绝的模式
    rejected_by_cat: dict[str, list[BehaviorPattern]] = {}
    for r in rejected:
        cat = r.category or ''
        if cat not in rejected_by_cat:
            rejected_by_cat[cat] = []
        rejected_by_cat[cat].append(r)

    for c in confirmed:
        cat_rejected = rejected_by_cat.get(c.category or '', [])
        for r in cat_rejected:
            sim = _text_similarity(c.name or '', r.name or '')
            if sim >= 0.4:
                _get_or_update_relation(
                    db, c.id, r.id, 'CONTRADICTS', sim,
                    f'同类别确认vs拒绝, sim={sim:.2f}',
                )
                count += 1

    if count:
        db.commit()
    return count


def discover_co_occurrence_relations(db: Session) -> int:
    """发现 REINFORCES 关系: 基于同一 episode 中的共现"""
    from models.feature_graph import EvidenceLedger
    # 找出同一 episode 中有多条证据的模式对
    ledger_entries = db.query(EvidenceLedger).filter(
        EvidenceLedger.episode_id.isnot(None),
    ).all()

    # 按 episode 分组
    by_episode: dict[int, list[int]] = {}
    for e in ledger_entries:
        if e.episode_id not in by_episode:
            by_episode[e.episode_id] = []
        if e.pattern_id not in by_episode[e.episode_id]:
            by_episode[e.episode_id].append(e.pattern_id)

    count = 0
    for ep_id, pattern_ids in by_episode.items():
        if len(pattern_ids) < 2:
            continue
        for i, pid_a in enumerate(pattern_ids):
            for pid_b in pattern_ids[i + 1:]:
                _get_or_update_relation(
                    db, pid_a, pid_b, 'REINFORCES', 0.5,
                    f'共现于 episode #{ep_id}',
                )
                count += 1
    if count:
        db.commit()
    return count


def run_relation_discovery(db: Session) -> dict:
    """执行完整关系发现周期"""
    logger.info('Starting relation discovery...')
    similar = discover_similar_relations(db)
    temporal = discover_temporal_relations(db)
    confirmation = discover_confirmation_relations(db)
    co_occurrence = discover_co_occurrence_relations(db)

    total = similar + temporal + confirmation + co_occurrence
    logger.info(f'Relation discovery: {total} relations (similar={similar}, temporal={temporal}, confirmation={confirmation}, co_occurrence={co_occurrence})')
    return {
        'total': total,
        'similar': similar,
        'temporal': temporal,
        'confirmation': confirmation,
        'co_occurrence': co_occurrence,
    }


def get_pattern_relations(db: Session, pattern_id: int) -> list[dict]:
    """获取某个模式的所有关系"""
    rels = db.query(PatternRelation).filter(
        (PatternRelation.source_pattern_id == pattern_id) |
        (PatternRelation.target_pattern_id == pattern_id),
    ).order_by(PatternRelation.weight.desc()).all()

    result = []
    for r in rels:
        other_id = r.target_pattern_id if r.source_pattern_id == pattern_id else r.source_pattern_id
        direction = 'outgoing' if r.source_pattern_id == pattern_id else 'incoming'
        other = db.query(BehaviorPattern).filter(BehaviorPattern.id == other_id).first()
        result.append({
            'id': r.id,
            'other_pattern_id': other_id,
            'other_pattern_name': other.name if other else '(deleted)',
            'relation_type': r.relation_type,
            'weight': r.weight,
            'direction': direction,
            'evidence': r.evidence_description,
        })
    return result

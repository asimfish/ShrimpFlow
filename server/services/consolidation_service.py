"""
记忆合并服务 (Phase 2)
灵感来自 NeuralMemory 的 consolidation engine。

三个核心策略:
- PRUNE: 清理低置信度、长期无访问的无用模式
- MERGE: 合并名称/描述高度相似的重复模式
- MATURE: 高证据+高置信度的 learning 模式自动晋升为 confirmed
"""
import json
import logging
import time
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from models.pattern import BehaviorPattern
from services.evidence_ledger import record_evidence
from services.memory_lifecycle import (
    LIFECYCLE_ARCHIVED,
    LIFECYCLE_COMPRESSED,
    DECAY_FLOOR,
    record_access,
)

logger = logging.getLogger(__name__)

# PRUNE 参数
PRUNE_CONFIDENCE_THRESHOLD = 10  # 置信度低于此值
PRUNE_MIN_INACTIVE_DAYS = 30  # 且超过 N 天未访问
PRUNE_MAX_REJECT = 2  # 被拒绝次数 >= 此值也清理

# MERGE 参数
MERGE_NAME_SIMILARITY = 0.70  # 名称相似度阈值
MERGE_DESC_SIMILARITY = 0.65  # 描述相似度阈值

# MATURE 参数
MATURE_MIN_EVIDENCE = 5  # 最低证据数
MATURE_MIN_CONFIDENCE = 75  # 最低置信度

DAY_SECONDS = 86400

def _text_similarity(a: str, b: str) -> float:
    """简单文本相似度 (SequenceMatcher)"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def strategy_prune(db: Session) -> dict:
    """PRUNE: 清理无用模式"""
    now = int(time.time())
    candidates = db.query(BehaviorPattern).filter(
        BehaviorPattern.status.in_(['learning', 'rejected']),
    ).all()

    pruned_ids = []
    for p in candidates:
        last_acc = p.last_accessed_at or p.created_at or now
        days_idle = (now - last_acc) / DAY_SECONDS
        confidence = p.confidence or 0
        reject_count = p.reject_count or 0

        should_prune = False
        reason = ''

        # 低置信度 + 长期无访问
        if confidence < PRUNE_CONFIDENCE_THRESHOLD and days_idle > PRUNE_MIN_INACTIVE_DAYS:
            should_prune = True
            reason = f'confidence={confidence}, idle={int(days_idle)}d'

        # 多次被拒绝
        if reject_count >= PRUNE_MAX_REJECT and p.status == 'rejected':
            should_prune = True
            reason = f'rejected {reject_count} times'

        # archived 且低置信度
        if (p.lifecycle_state or '') in (LIFECYCLE_ARCHIVED, LIFECYCLE_COMPRESSED) and confidence < 20:
            should_prune = True
            reason = f'archived with confidence={confidence}'

        if should_prune:
            pruned_ids.append(p.id)
            p.status = 'pruned'
            # 记录到 evolution
            try:
                evo = json.loads(p.evolution) if p.evolution else []
            except (json.JSONDecodeError, TypeError):
                evo = []
            evo.append({
                'date': time.strftime('%m-%d'),
                'confidence': confidence,
                'event_description': f'pruned: {reason}',
            })
            p.evolution = json.dumps(evo[-20:], ensure_ascii=False)

    if pruned_ids:
        db.commit()
    logger.info(f'PRUNE: {len(pruned_ids)} patterns pruned')
    return {'pruned': len(pruned_ids), 'pruned_ids': pruned_ids}


def strategy_merge(db: Session) -> dict:
    """MERGE: 合并重复模式"""
    patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.status.in_(['learning', 'confirmed']),
    ).order_by(BehaviorPattern.confidence.desc()).all()

    merged_count = 0
    merged_pairs = []
    seen_ids = set()

    for i, pa in enumerate(patterns):
        if pa.id in seen_ids:
            continue
        for pb in patterns[i + 1:]:
            if pb.id in seen_ids:
                continue
            if pa.category != pb.category:
                continue

            name_sim = _text_similarity(pa.name or '', pb.name or '')
            desc_sim = _text_similarity(pa.description or '', pb.description or '')

            if name_sim >= MERGE_NAME_SIMILARITY and desc_sim >= MERGE_DESC_SIMILARITY:
                # 保留置信度更高的, 合并证据到胜者
                winner, loser = (pa, pb) if (pa.confidence or 0) >= (pb.confidence or 0) else (pb, pa)

                # 合并证据数
                winner.evidence_count = (winner.evidence_count or 0) + (loser.evidence_count or 0)
                winner.access_count = (winner.access_count or 0) + (loser.access_count or 0)

                # 合并 learned_from_data
                try:
                    w_data = json.loads(winner.learned_from_data) if winner.learned_from_data else []
                except (json.JSONDecodeError, TypeError):
                    w_data = []
                try:
                    l_data = json.loads(loser.learned_from_data) if loser.learned_from_data else []
                except (json.JSONDecodeError, TypeError):
                    l_data = []
                w_data.extend(l_data)
                winner.learned_from_data = json.dumps(w_data[-10:], ensure_ascii=False)

                # 标记 loser
                loser.status = 'merged'
                try:
                    evo = json.loads(loser.evolution) if loser.evolution else []
                except (json.JSONDecodeError, TypeError):
                    evo = []
                evo.append({
                    'date': time.strftime('%m-%d'),
                    'confidence': loser.confidence,
                    'event_description': f'merged into #{winner.id} (sim={name_sim:.2f})',
                })
                loser.evolution = json.dumps(evo[-20:], ensure_ascii=False)

                # 记录合并证据
                record_evidence(
                    db, winner.id, 'support',
                    f'合并重复模式 #{loser.id} ({loser.name})',
                    source='consolidation_merge',
                )

                seen_ids.add(loser.id)
                merged_count += 1
                merged_pairs.append({'winner': winner.id, 'loser': loser.id, 'similarity': round(name_sim, 2)})
                break  # 每个 pa 最多合并一个

    if merged_count:
        db.commit()
    logger.info(f'MERGE: {merged_count} patterns merged')
    return {'merged': merged_count, 'pairs': merged_pairs}


def strategy_mature(db: Session) -> dict:
    """MATURE: 高质量 learning 模式自动晋升为 confirmed"""
    candidates = db.query(BehaviorPattern).filter(
        BehaviorPattern.status == 'learning',
        BehaviorPattern.confidence >= MATURE_MIN_CONFIDENCE,
        BehaviorPattern.evidence_count >= MATURE_MIN_EVIDENCE,
    ).all()

    matured_ids = []
    for p in candidates:
        # 额外检查: 不能有过多拒绝
        if (p.reject_count or 0) >= 2:
            continue
        # 热度也要足够
        if (p.heat_score or 0) < 20:
            continue

        p.status = 'confirmed'
        from services.pattern_mining import _confidence_to_level
        p.confidence_level = _confidence_to_level(p.confidence)
        matured_ids.append(p.id)

        try:
            evo = json.loads(p.evolution) if p.evolution else []
        except (json.JSONDecodeError, TypeError):
            evo = []
        evo.append({
            'date': time.strftime('%m-%d'),
            'confidence': p.confidence,
            'event_description': f'auto-matured: evidence={p.evidence_count}, heat={p.heat_score:.1f}',
        })
        p.evolution = json.dumps(evo[-20:], ensure_ascii=False)

        # 记录晋升证据
        record_evidence(
            db, p.id, 'utility',
            f'自动晋升: {p.evidence_count}条证据, 置信度{p.confidence}',
            source='consolidation_mature',
        )

    if matured_ids:
        db.commit()
    logger.info(f'MATURE: {len(matured_ids)} patterns auto-confirmed')
    return {'matured': len(matured_ids), 'matured_ids': matured_ids}


def run_consolidation(db: Session) -> dict:
    """执行完整合并周期: PRUNE -> MERGE -> MATURE"""
    logger.info('Starting consolidation cycle...')
    prune_result = strategy_prune(db)
    merge_result = strategy_merge(db)
    mature_result = strategy_mature(db)
    result = {
        'prune': prune_result,
        'merge': merge_result,
        'mature': mature_result,
        'timestamp': int(time.time()),
    }
    logger.info(f'Consolidation complete: pruned={prune_result["pruned"]}, merged={merge_result["merged"]}, matured={mature_result["matured"]}')
    return result


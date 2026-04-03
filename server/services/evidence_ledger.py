import json
import logging
import time

from sqlalchemy.orm import Session

from models.feature_graph import EvidenceLedger
from models.pattern import BehaviorPattern

logger = logging.getLogger(__name__)

# 证据类型对置信度的影响权重
EVIDENCE_WEIGHTS = {
    'support': 0.12,     # 正面支持: 观察到符合模式的行为
    'conflict': -0.15,   # 冲突: 观察到违反模式的行为
    'negative': -0.18,   # 负反馈: 用户显式否定该模式
    'novelty': 0.08,     # 新颖性: 在新场景中观察到模式
    'utility': 0.10,     # 实用性: 模式被实际使用/确认有效
}


def _bayesian_update(prior: float, evidence_strength: float) -> float:
    # 贝叶斯更新: prior 是 0~1 的置信度, evidence_strength 是 -1~1 的证据强度
    likelihood = 0.5 + evidence_strength * 0.4
    likelihood = max(0.01, min(0.99, likelihood))
    posterior = (likelihood * prior) / (likelihood * prior + (1 - likelihood) * (1 - prior))
    return max(0.01, min(0.99, posterior))


def record_evidence(
    db: Session,
    pattern_id: int,
    evidence_type: str,
    description: str,
    source: str,
    episode_id: int = None,
) -> dict:
    # 记录一条证据并更新模式置信度
    pattern = db.query(BehaviorPattern).filter(BehaviorPattern.id == pattern_id).first()
    if not pattern:
        return {'error': 'pattern_not_found'}

    weight = EVIDENCE_WEIGHTS.get(evidence_type, 0)
    if weight == 0:
        return {'error': 'invalid_evidence_type'}

    confidence_before = pattern.confidence
    prior = confidence_before / 100.0
    posterior = _bayesian_update(prior, weight / abs(weight) * min(1.0, abs(weight) * 3))
    confidence_after = max(1, min(99, int(posterior * 100)))

    # 写入账本
    entry = EvidenceLedger(
        pattern_id=pattern_id,
        episode_id=episode_id,
        evidence_type=evidence_type,
        description=description,
        confidence_before=confidence_before,
        confidence_after=confidence_after,
        delta=confidence_after - confidence_before,
        source=source,
        created_at=int(time.time()),
    )
    db.add(entry)

    # 更新模式置信度
    pattern.confidence = confidence_after
    from services.pattern_mining import _confidence_to_level
    pattern.confidence_level = _confidence_to_level(confidence_after)

    # 追加 evolution
    try:
        evo = json.loads(pattern.evolution) if pattern.evolution else []
    except (json.JSONDecodeError, TypeError):
        evo = []
    evo.append({
        'date': time.strftime('%m-%d'),
        'confidence': confidence_after,
        'event_description': f'{evidence_type}: {description[:60]}',
    })
    pattern.evolution = json.dumps(evo[-20:], ensure_ascii=False)

    db.commit()

    logger.info(f'Evidence recorded: pattern={pattern_id}, type={evidence_type}, {confidence_before}->{confidence_after}')
    return {
        'pattern_id': pattern_id,
        'evidence_type': evidence_type,
        'confidence_before': confidence_before,
        'confidence_after': confidence_after,
        'delta': confidence_after - confidence_before,
    }


def record_mining_evidence(db: Session, pattern_id: int, episode_id: int, evidence_type: str, description: str) -> dict:
    # 挖掘过程中记录证据的快捷方法
    return record_evidence(db, pattern_id, evidence_type, description, source='mining', episode_id=episode_id)


def get_ledger_for_pattern(db: Session, pattern_id: int, limit: int = 50) -> list[dict]:
    rows = db.query(EvidenceLedger).filter(
        EvidenceLedger.pattern_id == pattern_id,
    ).order_by(EvidenceLedger.created_at.desc()).limit(limit).all()
    return [
        {
            'id': r.id,
            'pattern_id': r.pattern_id,
            'episode_id': r.episode_id,
            'evidence_type': r.evidence_type,
            'description': r.description,
            'confidence_before': r.confidence_before,
            'confidence_after': r.confidence_after,
            'delta': r.delta,
            'source': r.source,
            'created_at': r.created_at,
        }
        for r in rows
    ]


def get_ledger_stats(db: Session) -> dict:
    rows = db.query(EvidenceLedger).all()
    if not rows:
        return {'total': 0, 'by_type': {}, 'avg_delta': 0}

    by_type = {}
    total_delta = 0
    for r in rows:
        by_type[r.evidence_type] = by_type.get(r.evidence_type, 0) + 1
        total_delta += (r.delta or 0)

    return {
        'total': len(rows),
        'by_type': by_type,
        'avg_delta': round(total_delta / len(rows), 2) if rows else 0,
    }


def is_meaningful_rule(pattern: BehaviorPattern) -> bool:
    # 有意义性判断: 检查模式是否值得保留/推送
    # 1. 名称不能太短或太泛
    name = pattern.name or ''
    if len(name) < 5:
        return False

    # 2. 必须有实际描述
    desc = pattern.description or ''
    if len(desc) < 10:
        return False

    # 3. 证据数量 >= 2
    if (pattern.evidence_count or 0) < 2:
        return False

    # 4. 类别必须有意义
    if pattern.category not in ('coding', 'review', 'git', 'devops', 'collaboration'):
        return False

    # 5. 不能是纯统计描述 (检查是否有可执行的 trigger/body)
    has_trigger = bool(pattern.trigger and len(str(pattern.trigger)) > 5)
    has_body = bool(pattern.body and len(pattern.body) > 20)
    if not has_trigger and not has_body:
        return False

    # 6. 名称不能是纯数字/符号
    import re
    if not re.search(r'[\u4e00-\u9fff a-zA-Z]{3,}', name):
        return False

    return True


def compress_evidence(db: Session, pattern_id: int, keep_recent: int = 50) -> dict:
    """压缩证据: 超过 keep_recent 条时, 把旧条目合并为摘要"""
    total = db.query(EvidenceLedger).filter(
        EvidenceLedger.pattern_id == pattern_id,
    ).count()

    if total <= keep_recent:
        return {'pattern_id': pattern_id, 'compressed': 0, 'kept': total}

    # 保留最近 keep_recent 条, 删除更老的
    recent_ids = [
        r.id for r in
        db.query(EvidenceLedger.id).filter(
            EvidenceLedger.pattern_id == pattern_id,
        ).order_by(EvidenceLedger.created_at.desc()).limit(keep_recent).all()
    ]

    old_entries = db.query(EvidenceLedger).filter(
        EvidenceLedger.pattern_id == pattern_id,
        ~EvidenceLedger.id.in_(recent_ids),
    ).all()

    if not old_entries:
        return {'pattern_id': pattern_id, 'compressed': 0, 'kept': total}

    # 汇总旧条目为一条 summary
    by_type = {}
    total_delta = 0
    oldest_ts = None
    newest_ts = None
    for e in old_entries:
        by_type[e.evidence_type] = by_type.get(e.evidence_type, 0) + 1
        total_delta += (e.delta or 0)
        ts = e.created_at or 0
        if oldest_ts is None or ts < oldest_ts:
            oldest_ts = ts
        if newest_ts is None or ts > newest_ts:
            newest_ts = ts

    summary_desc = ', '.join(f'{t}:{c}' for t, c in sorted(by_type.items()))
    summary = EvidenceLedger(
        pattern_id=pattern_id,
        episode_id=None,
        evidence_type='summary',
        description=f'压缩 {len(old_entries)} 条证据: {summary_desc}, total_delta={total_delta}',
        confidence_before=old_entries[0].confidence_before if old_entries else 0,
        confidence_after=old_entries[-1].confidence_after if old_entries else 0,
        delta=total_delta,
        source='compression',
        created_at=oldest_ts or int(time.time()),
    )
    db.add(summary)

    # 删除旧条目
    for e in old_entries:
        db.delete(e)

    db.commit()
    logger.info(f'Compressed {len(old_entries)} evidence entries for pattern {pattern_id}')
    return {'pattern_id': pattern_id, 'compressed': len(old_entries), 'kept': keep_recent + 1}


def compress_all_evidence(db: Session, threshold: int = 100, keep_recent: int = 50) -> dict:
    """对所有超过 threshold 条证据的模式执行压缩"""
    from sqlalchemy import func
    heavy_patterns = db.query(
        EvidenceLedger.pattern_id, func.count(EvidenceLedger.id).label('cnt'),
    ).group_by(EvidenceLedger.pattern_id).having(
        func.count(EvidenceLedger.id) > threshold,
    ).all()

    total_compressed = 0
    for row in heavy_patterns:
        result = compress_evidence(db, row[0], keep_recent)
        total_compressed += result.get('compressed', 0)

    return {'patterns_processed': len(heavy_patterns), 'total_compressed': total_compressed}


def filter_meaningful_patterns(db: Session) -> list[int]:
    # 过滤出有意义的模式 ID 列表
    patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.status == 'learning',
        BehaviorPattern.confidence >= 50,
    ).all()

    meaningful_ids = []
    for p in patterns:
        if is_meaningful_rule(p):
            meaningful_ids.append(p.id)
        else:
            # 对无意义的模式记录 conflict 证据
            if p.confidence > 20:
                record_evidence(
                    db, p.id, 'conflict',
                    '有意义性检查未通过: 缺少可执行规范或证据不足',
                    source='meaningful_filter',
                )

    return meaningful_ids

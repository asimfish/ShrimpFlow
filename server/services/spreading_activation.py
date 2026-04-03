"""
扩散激活召回 (Phase 4)
灵感来自 NeuralMemory 的 spreading activation 算法。

从查询匹配的种子模式出发, 沿 PatternRelation 边做 BFS 扩散,
每一跳激活衰减, 最终返回按激活强度排序的关联模式网络。

核心参数:
- max_hops: 最大扩散跳数 (默认 2)
- decay_factor: 每跳激活衰减系数 (默认 0.5)
- min_activation: 最低激活阈值 (默认 0.1)
"""
import logging
from collections import defaultdict

from sqlalchemy.orm import Session

from models.pattern import BehaviorPattern, PatternRelation
from services.memory_lifecycle import record_access

logger = logging.getLogger(__name__)

MAX_HOPS = 2
DECAY_FACTOR = 0.5
MIN_ACTIVATION = 0.1

# 不同关系类型的传播权重
RELATION_PROPAGATION = {
    'CAUSED_BY': 0.9,
    'LEADS_TO': 0.85,
    'FOLLOWS': 0.7,
    'REINFORCES': 0.8,
    'SIMILAR_TO': 0.6,
    'CONTRADICTS': 0.4,  # 矛盾关系传播弱但仍传播
}


def _build_adjacency(db: Session) -> dict[int, list[tuple[int, str, float]]]:
    """构建邻接表: pattern_id -> [(neighbor_id, relation_type, weight)]"""
    rels = db.query(PatternRelation).all()
    adj: dict[int, list[tuple[int, str, float]]] = defaultdict(list)
    for r in rels:
        prop = RELATION_PROPAGATION.get(r.relation_type, 0.5) * (r.weight or 1.0)
        adj[r.source_pattern_id].append((r.target_pattern_id, r.relation_type, prop))
        adj[r.target_pattern_id].append((r.source_pattern_id, r.relation_type, prop))
    return adj


def _find_seed_patterns(db: Session, query: str, limit: int = 5) -> list[BehaviorPattern]:
    """从查询文本找到种子模式 (简单关键词匹配)"""
    q = query.lower()
    candidates = db.query(BehaviorPattern).filter(
        BehaviorPattern.status.in_(['learning', 'confirmed']),
    ).all()

    scored = []
    for p in candidates:
        score = 0.0
        name = (p.name or '').lower()
        desc = (p.description or '').lower()
        cat = (p.category or '').lower()

        # 精确匹配
        if q in name:
            score += 10.0
        if q in desc:
            score += 5.0
        if q in cat:
            score += 3.0

        # 分词匹配
        words = q.split()
        for w in words:
            if len(w) < 2:
                continue
            if w in name:
                score += 2.0
            if w in desc:
                score += 1.0

        if score > 0:
            scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:limit]]


def spreading_activation(
    db: Session,
    seed_ids: list[int],
    max_hops: int = MAX_HOPS,
    decay_factor: float = DECAY_FACTOR,
    min_activation: float = MIN_ACTIVATION,
) -> list[dict]:
    """
    从种子模式出发做扩散激活。

    返回: [{pattern_id, name, category, confidence, activation, hop, path}]
    """
    adj = _build_adjacency(db)

    # activation_map: pattern_id -> 最高激活强度
    activation_map: dict[int, float] = {}
    hop_map: dict[int, int] = {}
    path_map: dict[int, list[str]] = {}

    # 种子节点激活 = 1.0
    frontier = []
    for sid in seed_ids:
        activation_map[sid] = 1.0
        hop_map[sid] = 0
        path_map[sid] = ['seed']
        frontier.append((sid, 1.0, 0))

    # BFS 扩散
    for hop in range(1, max_hops + 1):
        next_frontier = []
        for pid, parent_activation, _ in frontier:
            for neighbor_id, rel_type, prop_weight in adj.get(pid, []):
                child_activation = parent_activation * decay_factor * prop_weight
                if child_activation < min_activation:
                    continue
                if neighbor_id in activation_map and activation_map[neighbor_id] >= child_activation:
                    continue
                activation_map[neighbor_id] = child_activation
                hop_map[neighbor_id] = hop
                path_map[neighbor_id] = path_map.get(pid, []) + [f'{rel_type}->{neighbor_id}']
                next_frontier.append((neighbor_id, child_activation, hop))
        frontier = next_frontier

    # 移除种子本身
    for sid in seed_ids:
        activation_map.pop(sid, None)

    if not activation_map:
        return []

    # 批量查询模式信息
    pattern_ids = list(activation_map.keys())
    patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.id.in_(pattern_ids),
    ).all()
    pattern_map = {p.id: p for p in patterns}

    results = []
    for pid, activation in sorted(activation_map.items(), key=lambda x: x[1], reverse=True):
        p = pattern_map.get(pid)
        if not p:
            continue
        results.append({
            'pattern_id': pid,
            'name': p.name,
            'category': p.category,
            'confidence': p.confidence,
            'lifecycle_state': p.lifecycle_state or 'active',
            'heat_score': round(p.heat_score or 0, 1),
            'activation': round(activation, 3),
            'hop': hop_map.get(pid, 0),
            'path': path_map.get(pid, []),
        })

    return results[:20]  # 最多返回 20 个


def recall_patterns(db: Session, query: str, max_hops: int = MAX_HOPS) -> dict:
    """
    扩散激活召回 API 入口。
    1. 从 query 找到种子模式
    2. 从种子出发扩散激活
    3. 对种子执行 record_access 强化
    """
    seeds = _find_seed_patterns(db, query)
    if not seeds:
        return {'query': query, 'seeds': [], 'activated': [], 'total': 0}

    seed_ids = [s.id for s in seeds]
    # 强化种子模式
    for sid in seed_ids:
        record_access(db, sid)

    activated = spreading_activation(db, seed_ids, max_hops=max_hops)

    return {
        'query': query,
        'seeds': [
            {
                'pattern_id': s.id,
                'name': s.name,
                'category': s.category,
                'confidence': s.confidence,
            }
            for s in seeds
        ],
        'activated': activated,
        'total': len(activated),
    }

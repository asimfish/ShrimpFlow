import json
import logging
import math
import time
from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from models.episode import Episode
from models.feature_graph import EpisodeFeature, FeatureEdge

logger = logging.getLogger(__name__)

# 特征向量的维度定义 (固定顺序，用于余弦相似度)
FEATURE_KEYS = [
    'tool_terminal', 'tool_git', 'tool_claude', 'tool_editor', 'tool_codex', 'tool_openclaw', 'tool_system',
    'intent_coding', 'intent_debugging', 'intent_testing', 'intent_committing', 'intent_deploying',
    'intent_reviewing', 'intent_configuring', 'intent_building', 'intent_learning',
    'error_rate', 'has_tests', 'has_commits', 'duration_norm',
]

# 行为原型定义: 基于特征向量的聚类中心
ARCHETYPE_SIGNATURES = {
    'debug-fix-commit': {'intent_debugging': 0.3, 'intent_committing': 0.2, 'has_commits': 1.0},
    'test-driven-dev': {'intent_testing': 0.3, 'intent_coding': 0.3, 'has_tests': 1.0},
    'ai-assisted-coding': {'tool_claude': 0.3, 'intent_coding': 0.3},
    'deploy-ops': {'intent_deploying': 0.3, 'intent_configuring': 0.2},
    'code-review': {'intent_reviewing': 0.4, 'tool_git': 0.2},
    'learning-exploration': {'intent_learning': 0.3, 'tool_openclaw': 0.2},
    'rapid-iteration': {'has_commits': 1.0, 'intent_coding': 0.3, 'duration_norm': 0.2},
}

SIMILARITY_THRESHOLD = 0.6


def _episode_to_vector(features: dict) -> list[float]:
    # 将 episode features 转为固定维度向量
    tool_dist = features.get('tool_dist', {})
    intent_dist = features.get('intent_dist', {})
    error_rate = features.get('error_rate', 0)
    has_tests = 1.0 if features.get('has_tests') else 0.0
    has_commits = 1.0 if features.get('has_commits') else 0.0
    duration = features.get('duration', 0)
    # 归一化 duration: 0~4h -> 0~1
    duration_norm = min(1.0, duration / 14400) if duration > 0 else 0

    vec = [
        tool_dist.get('terminal', 0), tool_dist.get('git', 0), tool_dist.get('claude', 0),
        tool_dist.get('editor', 0), tool_dist.get('codex', 0), tool_dist.get('openclaw', 0),
        tool_dist.get('system', 0),
        intent_dist.get('coding', 0), intent_dist.get('debugging', 0), intent_dist.get('testing', 0),
        intent_dist.get('committing', 0), intent_dist.get('deploying', 0),
        intent_dist.get('reviewing', 0), intent_dist.get('configuring', 0),
        intent_dist.get('building', 0), intent_dist.get('learning', 0),
        error_rate, has_tests, has_commits, duration_norm,
    ]
    return vec


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return dot / (norm_a * norm_b)


def _classify_archetype(vec: list[float]) -> str:
    # 找最匹配的行为原型
    best_archetype = 'general'
    best_score = 0.0

    for archetype, signature in ARCHETYPE_SIGNATURES.items():
        sig_vec = [signature.get(k, 0) for k in FEATURE_KEYS]
        score = _cosine_similarity(vec, sig_vec)
        if score > best_score:
            best_score = score
            best_archetype = archetype

    return best_archetype if best_score > 0.15 else 'general'


def build_feature_graph(db: Session, lookback_hours: int = 168) -> dict:
    # 获取最近的 episodes
    cutoff = int(time.time()) - lookback_hours * 3600
    episodes = db.query(Episode).filter(
        Episode.start_ts > cutoff,
    ).order_by(Episode.start_ts.asc()).all()

    if len(episodes) < 3:
        logger.info(f'Not enough episodes for feature graph: {len(episodes)}')
        return {'nodes': 0, 'edges': 0}

    # 已有的 feature 节点
    existing_episode_ids = {
        row[0] for row in db.query(EpisodeFeature.episode_id).all()
    }

    now = int(time.time())
    new_features = []

    for ep in episodes:
        if ep.id in existing_episode_ids:
            continue

        features = json.loads(ep.features) if ep.features else {}
        vec = _episode_to_vector(features)
        archetype = _classify_archetype(vec)

        node = EpisodeFeature(
            episode_id=ep.id,
            project=ep.project,
            task_category=ep.task_category,
            archetype=archetype,
            feature_vector=json.dumps(features, ensure_ascii=False),
            norm_vector=json.dumps(vec),
            created_at=now,
        )
        db.add(node)
        new_features.append(node)

    if new_features:
        db.flush()

    # 构建边: 计算新节点与所有节点的相似度
    all_features = db.query(EpisodeFeature).all()
    feature_vecs = {}
    for f in all_features:
        vec = json.loads(f.norm_vector) if f.norm_vector else []
        if vec:
            feature_vecs[f.id] = vec

    new_ids = {f.id for f in new_features}
    edge_count = 0

    for new_f in new_features:
        if new_f.id not in feature_vecs:
            continue
        vec_a = feature_vecs[new_f.id]

        for other_id, vec_b in feature_vecs.items():
            if other_id == new_f.id:
                continue
            sim = _cosine_similarity(vec_a, vec_b)
            if sim < SIMILARITY_THRESHOLD:
                continue

            # 确定边类型
            other_f = next((f for f in all_features if f.id == other_id), None)
            if not other_f:
                continue

            if new_f.archetype == other_f.archetype and new_f.archetype != 'general':
                edge_type = 'same_archetype'
            elif sim > 0.8:
                edge_type = 'similar_workflow'
            else:
                edge_type = 'related'

            edge = FeatureEdge(
                source_id=new_f.id,
                target_id=other_id,
                similarity=round(sim, 4),
                edge_type=edge_type,
                created_at=now,
            )
            db.add(edge)
            edge_count += 1

    if new_features or edge_count:
        db.commit()

    # 统计行为原型分布
    archetype_dist = Counter(f.archetype for f in all_features)

    logger.info(f'Feature graph: {len(new_features)} new nodes, {edge_count} new edges, archetypes={dict(archetype_dist)}')
    return {
        'nodes': len(new_features),
        'edges': edge_count,
        'total_nodes': len(all_features),
        'archetype_distribution': dict(archetype_dist),
    }


def get_archetype_summary(db: Session) -> list[dict]:
    # 获取行为原型摘要
    all_features = db.query(EpisodeFeature).all()
    archetype_groups = defaultdict(list)
    for f in all_features:
        archetype_groups[f.archetype].append(f)

    summaries = []
    for archetype, features in archetype_groups.items():
        projects = Counter(f.project for f in features if f.project)
        categories = Counter(f.task_category for f in features if f.task_category)
        summaries.append({
            'archetype': archetype,
            'count': len(features),
            'top_projects': [p for p, _ in projects.most_common(3)],
            'top_categories': [c for c, _ in categories.most_common(3)],
        })

    return sorted(summaries, key=lambda x: x['count'], reverse=True)

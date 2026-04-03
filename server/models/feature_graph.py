from sqlalchemy import Column, Integer, String, Float

from db import Base


# 特征图谱: Episode 的特征向量节点
class EpisodeFeature(Base):
    __tablename__ = "episode_features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    episode_id = Column(Integer, nullable=False, index=True)
    project = Column(String)
    task_category = Column(String)
    # 行为原型聚类标签 (由聚类算法分配)
    archetype = Column(String)  # e.g. "debug-fix-commit", "test-driven-dev"
    # 特征向量 (JSON): tool_dist, intent_dist, error_rate, duration 等
    feature_vector = Column(String)
    # 归一化特征用于相似度计算
    norm_vector = Column(String)  # JSON float[]
    created_at = Column(Integer)


# 特征边: 两个 EpisodeFeature 之间的相似度关系
class FeatureEdge(Base):
    __tablename__ = "feature_edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, nullable=False, index=True)
    target_id = Column(Integer, nullable=False, index=True)
    similarity = Column(Float, nullable=False)  # 0~1 余弦相似度
    edge_type = Column(String)  # same_archetype / similar_workflow / temporal_adjacent
    created_at = Column(Integer)


# Evidence Ledger: 模式置信度变化的审计账本
class EvidenceLedger(Base):
    __tablename__ = "evidence_ledger"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern_id = Column(Integer, nullable=False, index=True)
    episode_id = Column(Integer)  # 关联的 episode
    evidence_type = Column(String, nullable=False)  # support / conflict / novelty / utility
    description = Column(String)
    confidence_before = Column(Integer)
    confidence_after = Column(Integer)
    delta = Column(Integer)  # confidence_after - confidence_before
    source = Column(String)  # mining / user_confirm / user_reject / ai_refine / session_mining
    created_at = Column(Integer)

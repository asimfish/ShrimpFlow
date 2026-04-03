from sqlalchemy import Column, Float, Integer, String

from db import Base


# 记忆生命周期状态 (灵感来自 NeuralMemory 的热度模型)
LIFECYCLE_ACTIVE = 'active'       # <7天 或高热度
LIFECYCLE_WARM = 'warm'           # 7-30天, 14天内访问过
LIFECYCLE_COOL = 'cool'           # 30-90天
LIFECYCLE_COMPRESSED = 'compressed'  # 90-180天
LIFECYCLE_ARCHIVED = 'archived'   # 180+天

LIFECYCLE_ORDER = [LIFECYCLE_ACTIVE, LIFECYCLE_WARM, LIFECYCLE_COOL, LIFECYCLE_COMPRESSED, LIFECYCLE_ARCHIVED]


class BehaviorPattern(Base):
    __tablename__ = "behavior_patterns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String)
    confidence = Column(Integer, default=0)
    evidence_count = Column(Integer, default=0)
    learned_from = Column(String)
    rule = Column(String)
    created_at = Column(Integer)
    status = Column(String, default="learning")
    evolution = Column(String)  # JSON PatternSnapshot[]
    rules = Column(String)  # JSON PatternRule[]
    executions = Column(String)  # JSON PatternExecution[]
    applicable_scenarios = Column(String)  # JSON string[]
    profile_id = Column(Integer, index=True)
    # ClawProfile v1 新增字段
    slug = Column(String)  # kebab-case 标识符
    trigger = Column(String)  # JSON: string | {when, globs, event, context}
    body = Column(String)  # prompt 正文 (Markdown)
    source = Column(String, default='auto')  # auto|manual|imported|forked
    confidence_level = Column(String)  # low|medium|high|very_high
    learned_from_data = Column(String)  # JSON: [{context, insight, confidence}]
    skill_alignment_score = Column(Integer, default=0)  # 与已知 skill 的对齐分(0-100)
    user_feedback = Column(String)  # JSON: [{action, ts, reason}]
    reject_count = Column(Integer, default=0)  # 用户拒绝次数
    # Phase 1: 记忆衰减与强化 (NeuralMemory 热度模型)
    heat_score = Column(Float, default=50.0)  # 热度评分 0~100
    last_accessed_at = Column(Integer, default=0)  # 上次被访问/使用的时间戳
    access_count = Column(Integer, default=0)  # 累计访问/使用次数
    lifecycle_state = Column(String, default='active')  # active/warm/cool/compressed/archived


# Phase 3: 语义关系图 (灵感来自 NeuralMemory 的 24 种关系类型)
RELATION_TYPES = [
    'CAUSED_BY',     # A 由 B 引起 (error_recovery 天然有)
    'LEADS_TO',      # A 导致 B (用户确认 A 后确认 B)
    'FOLLOWS',       # A 之后通常出现 B (workflow 顺序)
    'CONTRADICTS',   # A 与 B 冲突 (用户确认 A 但拒绝 B)
    'SIMILAR_TO',    # A 与 B 相似 (名称/描述)
    'REINFORCES',    # A 强化 B (同一 episode 中共现)
]


class PatternRelation(Base):
    __tablename__ = "pattern_relations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_pattern_id = Column(Integer, nullable=False, index=True)
    target_pattern_id = Column(Integer, nullable=False, index=True)
    relation_type = Column(String, nullable=False)  # CAUSED_BY / LEADS_TO / ...
    weight = Column(Float, default=1.0)  # 关系强度 0~1
    evidence_description = Column(String)  # 发现该关系的依据
    created_at = Column(Integer)
    updated_at = Column(Integer)

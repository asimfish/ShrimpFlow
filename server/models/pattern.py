from sqlalchemy import Column, Integer, String

from db import Base


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

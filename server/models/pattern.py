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

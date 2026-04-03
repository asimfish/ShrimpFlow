from sqlalchemy import Column, Integer, String, Float

from db import Base


class MetaDecisionLog(Base):
    __tablename__ = "meta_decision_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    decision_type = Column(String, nullable=False)  # pattern_confirm | pattern_reject | task_approve | task_skip | auto_confirm
    target_id = Column(Integer, nullable=True)
    target_name = Column(String, nullable=True)
    user_action = Column(String, nullable=False)  # confirm | reject | approve | skip | override
    user_reason = Column(String, nullable=True)
    system_recommendation = Column(String, nullable=True)  # JSON
    context_snapshot = Column(String, nullable=True)  # JSON
    taste_profile_snapshot = Column(String, nullable=True)  # JSON
    created_at = Column(Integer, nullable=False)


class MetaPolicy(Base):
    __tablename__ = "meta_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule = Column(String, nullable=False)
    conditions = Column(String, nullable=True)  # JSON
    predicted_action = Column(String, nullable=False)  # confirm | reject | approve | skip
    confidence = Column(Float, default=0.5)
    hit_count = Column(Integer, default=0)
    miss_count = Column(Integer, default=0)
    supporting_decisions = Column(String, nullable=True)  # JSON int[]
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=True)


class MetaShadowLog(Base):
    __tablename__ = "meta_shadow_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern_id = Column(Integer, nullable=True)
    predicted_action = Column(String, nullable=False)
    predicted_confidence = Column(Float, default=0.5)
    predicted_reason = Column(String, nullable=True)
    actual_action = Column(String, nullable=True)
    matched = Column(Integer, nullable=True)  # 1 = match, 0 = mismatch, NULL = pending
    created_at = Column(Integer, nullable=False)
    resolved_at = Column(Integer, nullable=True)

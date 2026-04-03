from sqlalchemy import Column, Integer, String

from db import Base


class AgentTasteProfile(Base):
    __tablename__ = "agent_taste_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(Integer)
    updated_at = Column(Integer)
    preferred_categories = Column(String)  # JSON: {category: weight}
    preferred_confidence_threshold = Column(Integer, default=70)
    preferred_sources = Column(String)  # JSON: [source]
    decision_history = Column(String)  # JSON: [{pattern_id, decision, reason, ts}]
    taste_summary = Column(String)

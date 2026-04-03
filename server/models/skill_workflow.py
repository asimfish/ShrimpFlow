from sqlalchemy import Column, Float, Integer, String

from db import Base


class SkillWorkflow(Base):
    __tablename__ = "skill_workflows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    skill_sequence = Column(String)  # JSON string[] in order
    frequency = Column(Integer, default=1)
    success_rate = Column(Float, default=0.0)
    source = Column(String, default="mined")  # mined | manual | imported
    matched_pattern_ids = Column(String)  # JSON int[] BehaviorPattern ids
    created_at = Column(Integer)
    updated_at = Column(Integer)

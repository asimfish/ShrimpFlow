from sqlalchemy import Column, Float, Integer, String

from db import Base


class SkillWorkflow(Base):
    __tablename__ = "skill_workflows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    skill_sequence = Column(String)  # JSON string[] in order
    frequency = Column(Integer, default=1)
    success_rate = Column(Float, default=0.0)
    source = Column(String, default="mined")  # mined | manual | imported | ai_summarized
    matched_pattern_ids = Column(String)  # JSON int[] BehaviorPattern ids
    created_at = Column(Integer)
    updated_at = Column(Integer)
    description = Column(String, nullable=True)  # AI-generated one-line summary
    trigger = Column(String, nullable=True)  # when this workflow is typically triggered
    steps = Column(String, nullable=True)  # JSON structured steps [{action, tool, checkpoint}]
    status = Column(String, default="draft")  # draft | confirmed | archived
    context_tags = Column(String, nullable=True)  # JSON string[] usage scenario tags
    confirmed_by = Column(String, nullable=True)  # user | auto

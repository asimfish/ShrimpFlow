from sqlalchemy import Column, Integer, String

from db import Base


class TeamWorkflow(Base):
    __tablename__ = "team_workflows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String)
    profile_id = Column(Integer, index=True)
    patterns = Column(String)  # JSON int[] (兼容旧数据)
    target_team = Column(String)
    status = Column(String, default="draft")
    created_at = Column(Integer)
    # ClawProfile v1 新增
    steps = Column(String)  # JSON: [{pattern, when, gate}, {inline, when}, {parallel}]

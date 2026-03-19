from sqlalchemy import Column, Integer, String

from db import Base


class TeamWorkflow(Base):
    __tablename__ = "team_workflows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String)
    patterns = Column(String)  # JSON int[]
    target_team = Column(String)
    status = Column(String, default="draft")
    created_at = Column(Integer)

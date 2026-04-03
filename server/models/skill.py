from sqlalchemy import Column, Integer, String

from db import Base


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=False)
    level = Column(Integer, default=0)
    total_uses = Column(Integer, default=0)
    cot_uses = Column(Integer, default=0)
    manual_uses = Column(Integer, default=0)
    auto_uses = Column(Integer, default=0)
    combo_patterns = Column(String)
    workflow_roles = Column(String)
    last_used = Column(Integer)
    first_seen = Column(Integer)

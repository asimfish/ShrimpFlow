from sqlalchemy import Column, Integer, String

from db import Base


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=False)
    level = Column(Integer, default=0)
    total_uses = Column(Integer, default=0)
    last_used = Column(Integer)
    first_seen = Column(Integer)

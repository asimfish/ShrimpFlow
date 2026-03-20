from sqlalchemy import Column, Integer, String

from db import Base


class ClawProfile(Base):
    __tablename__ = "claw_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schema = Column(String, nullable=False, default="clawprofile/v1")
    name = Column(String, nullable=False)
    display = Column(String, nullable=False)
    description = Column(String)
    author = Column(String)
    tags = Column(String)  # JSON string[]
    license = Column(String)
    forked_from = Column(String)
    trust = Column(String, default="local")
    injection = Column(String)  # JSON
    is_active = Column(Integer, default=0)
    created_at = Column(Integer)
    updated_at = Column(Integer)

from sqlalchemy import Column, Integer, String

from db import Base


class DevEvent(Base):
    __tablename__ = "dev_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(Integer, nullable=False, index=True)
    source = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)
    directory = Column(String)
    project = Column(String, index=True)
    branch = Column(String)
    exit_code = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)
    semantic = Column(String)
    tags = Column(String)  # JSON
    openclaw_session_id = Column(Integer, nullable=True)

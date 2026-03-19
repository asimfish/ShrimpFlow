from sqlalchemy import Column, Integer, String

from db import Base


class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, unique=True, nullable=False)
    event_count = Column(Integer, default=0)
    top_projects = Column(String)  # JSON {name, count}[]
    top_commands = Column(String)  # JSON {cmd, count}[]
    ai_summary = Column(String)
    openclaw_sessions = Column(Integer, default=0)

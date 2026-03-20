from sqlalchemy import Column, Integer, String

from db import Base


class OpenClawSession(Base):
    __tablename__ = "openclaw_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    messages = Column(String)  # JSON OpenClawMessage[]
    project = Column(String)
    tags = Column(String)  # JSON string[]
    profile_id = Column(Integer, index=True, nullable=True)
    injected_pattern_slugs = Column(String)  # JSON string[]
    analysis_summary = Column(String)
    analysis_status = Column(String)
    created_at = Column(Integer)
    summary = Column(String)


class OpenClawDocument(Base):
    __tablename__ = "openclaw_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False)
    content = Column(String)
    tags = Column(String)  # JSON string[]
    profile_id = Column(Integer, index=True, nullable=True)
    created_at = Column(Integer)
    source_session_id = Column(Integer, nullable=True)

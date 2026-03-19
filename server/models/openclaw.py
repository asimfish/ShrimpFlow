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
    created_at = Column(Integer)
    summary = Column(String)


class OpenClawDocument(Base):
    __tablename__ = "openclaw_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False)
    content = Column(String)
    tags = Column(String)  # JSON string[]
    created_at = Column(Integer)
    source_session_id = Column(Integer, nullable=True)

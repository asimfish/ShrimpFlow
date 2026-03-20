from sqlalchemy import Column, Integer, String

from db import Base


class OpenClawInvocationLog(Base):
    __tablename__ = "openclaw_invocation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, nullable=False, index=True)
    profile_id = Column(Integer, nullable=True, index=True)
    provider = Column(String)
    model = Column(String)
    selector_type = Column(String)  # heuristic | claude_selector
    selected_pattern_slugs = Column(String)  # JSON string[]
    prompt_excerpt = Column(String)
    response_summary = Column(String)
    status = Column(String)
    created_at = Column(Integer)

from sqlalchemy import Column, Integer, String

from db import Base


class SkillImplicitEvent(Base):
    __tablename__ = "skill_implicit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_action = Column(String, nullable=False)  # click | view | impression | search
    skill_name = Column(String, nullable=False, index=True)
    context = Column(String, nullable=True)  # JSON: {project, branch, recent_skills, page}
    created_at = Column(Integer, nullable=False)

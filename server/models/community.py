from sqlalchemy import Column, Integer, String

from db import Base


class SharedProfile(Base):
    __tablename__ = "shared_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False)
    avatar = Column(String)
    title = Column(String)
    bio = Column(String)
    followers = Column(Integer, default=0)
    patterns_count = Column(Integer, default=0)


class SharedPatternPack(Base):
    __tablename__ = "shared_pattern_packs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    author_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    category = Column(String)
    patterns = Column(String)  # JSON BehaviorPattern[]
    downloads = Column(Integer, default=0)
    stars = Column(Integer, default=0)
    tags = Column(String)  # JSON string[]
    created_at = Column(Integer)

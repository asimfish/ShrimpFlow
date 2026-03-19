from pydantic import BaseModel

from schemas.pattern import BehaviorPatternResponse


class SharedProfileResponse(BaseModel):
    id: int
    username: str
    avatar: str
    title: str
    bio: str
    followers: int
    patterns_count: int


class SharedPatternPackResponse(BaseModel):
    id: int
    author: SharedProfileResponse
    name: str
    description: str
    category: str
    patterns: list[BehaviorPatternResponse]
    downloads: int
    stars: int
    tags: list[str]
    created_at: int

from pydantic import BaseModel


class SkillResponse(BaseModel):
    id: int
    name: str
    category: str
    level: int
    total_uses: int
    last_used: int
    first_seen: int

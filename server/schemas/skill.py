from pydantic import BaseModel


class SkillResponse(BaseModel):
    id: int
    name: str
    category: str
    level: int
    total_uses: int
    cot_uses: int
    manual_uses: int
    auto_uses: int
    combo_patterns: list[str]
    workflow_roles: list[str]
    last_used: int
    first_seen: int

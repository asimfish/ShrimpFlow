from pydantic import BaseModel


class ClawProfileResponse(BaseModel):
    id: int
    schema: str
    name: str
    display: str
    description: str | None = None
    author: str | None = None
    tags: list[str]
    license: str | None = None
    forked_from: str | None = None
    trust: str | None = None
    injection: dict | None = None
    is_active: bool
    created_at: int | None = None
    updated_at: int | None = None
    pattern_count: int = 0
    workflow_count: int = 0

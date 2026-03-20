from pydantic import BaseModel


class TeamWorkflowResponse(BaseModel):
    id: int
    profile_id: int | None = None
    name: str
    description: str
    patterns: list[int]
    target_team: str
    status: str
    created_at: int
    steps: list[dict] | None = None

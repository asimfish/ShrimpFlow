from pydantic import BaseModel


class TeamWorkflowResponse(BaseModel):
    id: int
    name: str
    description: str
    patterns: list[int]
    target_team: str
    status: str
    created_at: int

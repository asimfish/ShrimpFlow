from pydantic import BaseModel


class DevEventResponse(BaseModel):
    id: int
    timestamp: int
    source: str
    action: str
    directory: str
    project: str
    branch: str
    exit_code: int
    duration_ms: int
    semantic: str
    tags: list[str]
    openclaw_session_id: int | None = None

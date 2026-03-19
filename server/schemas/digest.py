from pydantic import BaseModel


class ProjectCount(BaseModel):
    name: str
    count: int


class CommandCount(BaseModel):
    cmd: str
    count: int


class DailySummaryResponse(BaseModel):
    date: str
    event_count: int
    top_projects: list[ProjectCount]
    top_commands: list[CommandCount]
    ai_summary: str
    openclaw_sessions: int

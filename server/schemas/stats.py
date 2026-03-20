from pydantic import BaseModel


class StatsOverview(BaseModel):
    total_events: int
    total_days: int
    total_projects: int
    total_skills: int
    total_openclaw_sessions: int
    total_claude_sessions: int
    total_codex_sessions: int = 0
    total_git_commits: int
    most_active_project: str
    streak_days: int

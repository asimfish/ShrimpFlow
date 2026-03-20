from pydantic import BaseModel


class OpenClawInvocationLogResponse(BaseModel):
    id: int
    session_id: int
    profile_id: int | None = None
    provider: str | None = None
    model: str | None = None
    selector_type: str | None = None
    selected_pattern_slugs: list[str] = []
    prompt_excerpt: str | None = None
    response_summary: str | None = None
    status: str | None = None
    created_at: int | None = None

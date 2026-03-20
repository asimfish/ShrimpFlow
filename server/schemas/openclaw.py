from pydantic import BaseModel


class OpenClawMessageResponse(BaseModel):
    role: str
    content: str
    timestamp: int


class OpenClawSessionResponse(BaseModel):
    id: int
    title: str
    category: str
    messages: list[OpenClawMessageResponse]
    project: str
    tags: list[str]
    profile_id: int | None = None
    injected_pattern_slugs: list[str] = []
    analysis_summary: str | None = None
    analysis_status: str | None = None
    created_at: int
    summary: str


class OpenClawDocumentResponse(BaseModel):
    id: int
    title: str
    type: str
    content: str
    tags: list[str]
    profile_id: int | None = None
    created_at: int
    source_session_id: int

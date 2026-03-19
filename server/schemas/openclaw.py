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
    created_at: int
    summary: str


class OpenClawDocumentResponse(BaseModel):
    id: int
    title: str
    type: str
    content: str
    tags: list[str]
    created_at: int
    source_session_id: int

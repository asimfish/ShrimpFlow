from pydantic import BaseModel


class PatternSnapshotResponse(BaseModel):
    date: str
    confidence: int
    event_description: str


class PatternRuleResponse(BaseModel):
    id: int
    name: str
    description: str
    trigger: str
    action: str
    example: str


class PatternExecutionResponse(BaseModel):
    id: int
    pattern_id: int
    timestamp: int
    trigger_event: str
    action_taken: str
    result: str


class BehaviorPatternResponse(BaseModel):
    id: int
    profile_id: int | None = None
    name: str
    category: str
    description: str
    confidence: int
    evidence_count: int
    learned_from: str
    rule: str
    created_at: int
    status: str
    evolution: list[PatternSnapshotResponse]
    rules: list[PatternRuleResponse]
    executions: list[PatternExecutionResponse]
    applicable_scenarios: list[str]
    # ClawProfile v1
    slug: str | None = None
    trigger: dict | str | None = None
    body: str | None = None
    source: str | None = None
    confidence_level: str | None = None
    learned_from_data: list[dict] | None = None

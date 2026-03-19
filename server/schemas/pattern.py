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

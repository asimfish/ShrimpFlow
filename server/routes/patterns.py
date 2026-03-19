import json
import time
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from models.pattern import BehaviorPattern
from models.workflow import TeamWorkflow

router = APIRouter(tags=["patterns"])


def _row_to_dict(row: BehaviorPattern) -> dict:
    return {
        'id': row.id, 'name': row.name, 'category': row.category,
        'description': row.description, 'confidence': row.confidence,
        'evidence_count': row.evidence_count, 'learned_from': row.learned_from,
        'rule': row.rule, 'created_at': row.created_at, 'status': row.status,
        'evolution': json.loads(row.evolution) if row.evolution else [],
        'rules': json.loads(row.rules) if row.rules else [],
        'executions': json.loads(row.executions) if row.executions else [],
        'applicable_scenarios': json.loads(row.applicable_scenarios) if row.applicable_scenarios else [],
    }


def _workflow_to_dict(row: TeamWorkflow) -> dict:
    return {
        'id': row.id, 'name': row.name, 'description': row.description,
        'patterns': json.loads(row.patterns) if row.patterns else [],
        'target_team': row.target_team, 'status': row.status,
        'created_at': row.created_at,
    }


@router.get("/patterns")
def get_patterns(
    category: str = Query(None),
    status: str = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(BehaviorPattern)
    if category:
        q = q.filter(BehaviorPattern.category == category)
    if status:
        q = q.filter(BehaviorPattern.status == status)
    rows = q.order_by(BehaviorPattern.confidence.desc()).all()
    return [_row_to_dict(r) for r in rows]


@router.get("/patterns/export")
def export_patterns(ids: str = Query(...), db: Session = Depends(get_db)):
    id_list = [int(x) for x in ids.split(',') if x.strip()]
    rows = db.query(BehaviorPattern).filter(BehaviorPattern.id.in_(id_list)).all()
    return {'patterns': [_row_to_dict(r) for r in rows], 'exported_at': int(time.time())}


class PatternImportRequest(BaseModel):
    patterns: list[dict]


@router.post("/patterns/import")
def import_patterns(req: PatternImportRequest, db: Session = Depends(get_db)):
    imported = 0
    for p in req.patterns:
        pattern = BehaviorPattern(
            name=p.get('name', ''), category=p.get('category', 'coding'),
            description=p.get('description', ''), confidence=p.get('confidence', 50),
            evidence_count=p.get('evidence_count', 0),
            learned_from=p.get('learned_from', 'imported'),
            rule=p.get('rule', ''), created_at=int(time.time()),
            status=p.get('status', 'confirmed'),
            evolution=json.dumps(p.get('evolution', [])),
            rules=json.dumps(p.get('rules', [])),
            executions=json.dumps(p.get('executions', [])),
            applicable_scenarios=json.dumps(p.get('applicable_scenarios', [])),
        )
        db.add(pattern)
        imported += 1
    db.commit()
    return {'imported': imported}


class PatternCreateRequest(BaseModel):
    name: str
    category: str
    description: str
    confidence: int = 50
    evidence_count: int = 0
    learned_from: str = ''
    rule: str = ''
    status: str = 'learning'
    evolution: list[dict] = []
    rules: list[dict] = []
    executions: list[dict] = []
    applicable_scenarios: list[str] = []


class PatternUpdateRequest(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    confidence: int | None = None
    evidence_count: int | None = None
    learned_from: str | None = None
    rule: str | None = None
    status: str | None = None
    evolution: list[dict] | None = None
    rules: list[dict] | None = None
    executions: list[dict] | None = None
    applicable_scenarios: list[str] | None = None


@router.post("/patterns")
def create_pattern(req: PatternCreateRequest, db: Session = Depends(get_db)):
    pattern = BehaviorPattern(
        name=req.name, category=req.category, description=req.description,
        confidence=req.confidence, evidence_count=req.evidence_count,
        learned_from=req.learned_from, rule=req.rule,
        created_at=int(time.time()), status=req.status,
        evolution=json.dumps(req.evolution), rules=json.dumps(req.rules),
        executions=json.dumps(req.executions),
        applicable_scenarios=json.dumps(req.applicable_scenarios),
    )
    db.add(pattern)
    db.commit()
    db.refresh(pattern)
    return _row_to_dict(pattern)


@router.get("/patterns/{pattern_id}")
def get_pattern(pattern_id: int, db: Session = Depends(get_db)):
    row = db.query(BehaviorPattern).filter(BehaviorPattern.id == pattern_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return _row_to_dict(row)


@router.put("/patterns/{pattern_id}")
def update_pattern(pattern_id: int, req: PatternUpdateRequest, db: Session = Depends(get_db)):
    row = db.query(BehaviorPattern).filter(BehaviorPattern.id == pattern_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pattern not found")
    if req.name is not None:
        row.name = req.name
    if req.category is not None:
        row.category = req.category
    if req.description is not None:
        row.description = req.description
    if req.confidence is not None:
        row.confidence = req.confidence
    if req.evidence_count is not None:
        row.evidence_count = req.evidence_count
    if req.learned_from is not None:
        row.learned_from = req.learned_from
    if req.rule is not None:
        row.rule = req.rule
    if req.status is not None:
        row.status = req.status
    if req.evolution is not None:
        row.evolution = json.dumps(req.evolution)
    if req.rules is not None:
        row.rules = json.dumps(req.rules)
    if req.executions is not None:
        row.executions = json.dumps(req.executions)
    if req.applicable_scenarios is not None:
        row.applicable_scenarios = json.dumps(req.applicable_scenarios)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


@router.delete("/patterns/{pattern_id}")
def delete_pattern(pattern_id: int, db: Session = Depends(get_db)):
    row = db.query(BehaviorPattern).filter(BehaviorPattern.id == pattern_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pattern not found")
    db.delete(row)
    db.commit()
    return {'status': 'ok'}


@router.get("/workflows")
def get_workflows(db: Session = Depends(get_db)):
    rows = db.query(TeamWorkflow).all()
    return [_workflow_to_dict(r) for r in rows]


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    row = db.query(TeamWorkflow).filter(TeamWorkflow.id == workflow_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return _workflow_to_dict(row)


class WorkflowCreateRequest(BaseModel):
    name: str
    description: str
    patterns: list[int]
    target_team: str


class WorkflowUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    patterns: list[int] | None = None
    target_team: str | None = None
    status: str | None = None


@router.post("/workflows")
def create_workflow(req: WorkflowCreateRequest, db: Session = Depends(get_db)):
    wf = TeamWorkflow(
        name=req.name, description=req.description,
        patterns=json.dumps(req.patterns), target_team=req.target_team,
        status='draft', created_at=int(time.time()),
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return _workflow_to_dict(wf)


@router.put("/workflows/{workflow_id}")
def update_workflow(workflow_id: int, req: WorkflowUpdateRequest, db: Session = Depends(get_db)):
    row = db.query(TeamWorkflow).filter(TeamWorkflow.id == workflow_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if req.name is not None:
        row.name = req.name
    if req.description is not None:
        row.description = req.description
    if req.patterns is not None:
        row.patterns = json.dumps(req.patterns)
    if req.target_team is not None:
        row.target_team = req.target_team
    if req.status is not None:
        row.status = req.status
    db.commit()
    db.refresh(row)
    return _workflow_to_dict(row)


@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    row = db.query(TeamWorkflow).filter(TeamWorkflow.id == workflow_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.delete(row)
    db.commit()
    return {'status': 'ok'}


from services.pattern_mining import run_mining


@router.post("/patterns/mine")
def mine_patterns(db: Session = Depends(get_db)):
    results = run_mining(db)
    return {'patterns': results, 'count': len(results)}

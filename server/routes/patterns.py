import json
import time
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from models.pattern import BehaviorPattern
from models.profile import ClawProfile
from models.workflow import TeamWorkflow

router = APIRouter(tags=["patterns"])


def _row_to_dict(row: BehaviorPattern) -> dict:
    return {
        'id': row.id, 'profile_id': row.profile_id, 'name': row.name, 'category': row.category,
        'description': row.description, 'confidence': row.confidence,
        'evidence_count': row.evidence_count, 'learned_from': row.learned_from,
        'rule': row.rule, 'created_at': row.created_at, 'status': row.status,
        'evolution': json.loads(row.evolution) if row.evolution else [],
        'rules': json.loads(row.rules) if row.rules else [],
        'executions': json.loads(row.executions) if row.executions else [],
        'applicable_scenarios': json.loads(row.applicable_scenarios) if row.applicable_scenarios else [],
        'slug': row.slug,
        'trigger': json.loads(row.trigger) if row.trigger and row.trigger.startswith('{') else row.trigger,
        'body': row.body,
        'source': row.source,
        'confidence_level': row.confidence_level,
        'learned_from_data': json.loads(row.learned_from_data) if row.learned_from_data else [],
    }


def _workflow_to_dict(row: TeamWorkflow) -> dict:
    return {
        'id': row.id, 'profile_id': row.profile_id, 'name': row.name, 'description': row.description,
        'patterns': json.loads(row.patterns) if row.patterns else [],
        'target_team': row.target_team, 'status': row.status,
        'created_at': row.created_at,
        'steps': json.loads(row.steps) if row.steps else [],
    }


@router.get("/patterns")
def get_patterns(
    category: str = Query(None),
    status: str = Query(None),
    profile_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(BehaviorPattern)
    if profile_id is None:
        active = db.query(ClawProfile).filter(ClawProfile.is_active == 1).first()
        if active:
            q = q.filter(BehaviorPattern.profile_id == active.id)
    else:
        q = q.filter(BehaviorPattern.profile_id == profile_id)
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
    profile_row = None
    if rows and rows[0].profile_id:
        profile_row = db.query(ClawProfile).filter(ClawProfile.id == rows[0].profile_id).first()
    patterns_out = []
    for r in rows:
        evolution = json.loads(r.evolution) if r.evolution else []
        trigger_val = json.loads(r.trigger) if r.trigger and r.trigger.startswith('{') else r.trigger
        patterns_out.append({
            'slug': r.slug or r.name.lower().replace(' ', '-')[:50],
            'frontmatter': {
                'name': r.name, 'confidence': r.confidence_level or 'medium',
                'confidence_score': r.confidence, 'category': r.category,
                'trigger': trigger_val, 'evidence': r.evidence_count,
                'source': r.source or 'auto',
                'learned_from': json.loads(r.learned_from_data) if r.learned_from_data else [],
            },
            'body': r.body or r.description or '',
            'evolution': [{'date': e.get('date', ''), 'score': e.get('confidence', 0), 'note': e.get('event_description', '')} for e in evolution],
        })
    # 导出关联的 workflows
    wf_rows = db.query(TeamWorkflow).all()
    workflows_out = []
    for wf in wf_rows:
        wf_patterns = json.loads(wf.patterns) if wf.patterns else []
        if any(pid in id_list for pid in wf_patterns):
            workflows_out.append({
                'slug': wf.name.lower().replace(' ', '-')[:50],
                'frontmatter': {
                    'name': wf.name,
                    'steps': json.loads(wf.steps) if wf.steps else [],
                },
                'body': wf.description or '',
            })
    return {
        'schema': 'clawprofile/v1',
        'profile': {
            'name': profile_row.name if profile_row else 'local-devtwin-profile',
            'display': profile_row.display if profile_row else '本地行为模式库',
            'description': profile_row.description if profile_row else f'从 DevTwin 中导出的 {len(rows)} 个行为模式',
            'author': profile_row.author if profile_row else 'liyufeng',
            'tags': json.loads(profile_row.tags) if profile_row and profile_row.tags else list(set(r.category for r in rows)),
            'license': profile_row.license if profile_row else 'public',
            'trust': profile_row.trust if profile_row else 'local',
            'injection': json.loads(profile_row.injection) if profile_row and profile_row.injection else {'mode': 'proactive', 'budget': 2000},
        },
        'patterns': patterns_out,
        'workflows': workflows_out,
        'exported_at': int(time.time()),
    }


class PatternImportRequest(BaseModel):
    profile: dict | None = None
    patterns: list[dict] = []
    workflows: list[dict] = []


def _normalize_import_pattern(raw: dict, profile_meta: dict | None) -> dict:
    if 'frontmatter' in raw:
        fm = raw.get('frontmatter', {}) or {}
        confidence = fm.get('confidence_score')
        if confidence is None:
            level = fm.get('confidence', 'medium')
            confidence = {'low': 25, 'medium': 55, 'high': 80, 'very_high': 95}.get(level, 55)
        return {
            'name': fm.get('name') or raw.get('slug') or 'Imported Pattern',
            'category': fm.get('category', 'coding'),
            'description': raw.get('body', '')[:240] or fm.get('name', ''),
            'confidence': confidence,
            'evidence_count': fm.get('evidence', 0),
            'learned_from': (profile_meta or {}).get('display') or (profile_meta or {}).get('name') or 'imported_clawprofile',
            'rule': fm.get('name', raw.get('slug', '')),
            'status': 'confirmed',
            'evolution': [
                {
                    'date': item.get('date', ''),
                    'confidence': item.get('score', item.get('confidence', confidence)),
                    'event_description': item.get('note', item.get('event_description', '导入 ClawProfile')),
                }
                for item in raw.get('evolution', [])
            ],
            'rules': raw.get('rules', []),
            'executions': raw.get('executions', []),
            'applicable_scenarios': raw.get('applicable_scenarios', []),
            'slug': raw.get('slug'),
            'trigger': fm.get('trigger'),
            'body': raw.get('body'),
            'source': fm.get('source', 'imported'),
            'confidence_level': fm.get('confidence'),
            'learned_from_data': fm.get('learned_from', []),
        }

    return {
        'name': raw.get('name', ''),
        'category': raw.get('category', 'coding'),
        'description': raw.get('description', ''),
        'confidence': raw.get('confidence', 50),
        'evidence_count': raw.get('evidence_count', 0),
        'learned_from': raw.get('learned_from') or (profile_meta or {}).get('display') or 'imported',
        'rule': raw.get('rule', ''),
        'status': raw.get('status', 'confirmed'),
        'evolution': raw.get('evolution', []),
        'rules': raw.get('rules', []),
        'executions': raw.get('executions', []),
        'applicable_scenarios': raw.get('applicable_scenarios', []),
        'slug': raw.get('slug'),
        'trigger': raw.get('trigger'),
        'body': raw.get('body'),
        'source': raw.get('source', 'imported'),
        'confidence_level': raw.get('confidence_level'),
        'learned_from_data': raw.get('learned_from_data', []),
    }


@router.post("/patterns/import")
def import_patterns(req: PatternImportRequest, db: Session = Depends(get_db)):
    active_profile = db.query(ClawProfile).filter(ClawProfile.is_active == 1).first()
    imported = 0
    imported_workflows = 0
    slug_to_id: dict[str, int] = {}
    for raw_pattern in req.patterns:
        p = _normalize_import_pattern(raw_pattern, req.profile)
        slug = p.get('slug') or p['name'].lower().replace(' ', '-')[:64]
        existing = db.query(BehaviorPattern).filter(BehaviorPattern.slug == slug).first()
        if existing:
            existing.name = p['name']
            existing.category = p['category']
            existing.description = p['description']
            existing.confidence = p['confidence']
            existing.evidence_count = p['evidence_count']
            existing.learned_from = p['learned_from']
            existing.rule = p['rule']
            existing.status = p['status']
            existing.evolution = json.dumps(p['evolution'], ensure_ascii=False)
            existing.rules = json.dumps(p['rules'], ensure_ascii=False)
            existing.executions = json.dumps(p['executions'], ensure_ascii=False)
            existing.applicable_scenarios = json.dumps(p['applicable_scenarios'], ensure_ascii=False)
            existing.profile_id = active_profile.id if active_profile else existing.profile_id
            existing.trigger = json.dumps(p['trigger'], ensure_ascii=False) if isinstance(p['trigger'], dict) else p['trigger']
            existing.body = p['body']
            existing.source = p['source'] or 'imported'
            existing.confidence_level = p['confidence_level']
            existing.learned_from_data = json.dumps(p['learned_from_data'], ensure_ascii=False)
            slug_to_id[slug] = existing.id
            continue

        pattern = BehaviorPattern(
            name=p['name'], category=p['category'],
            description=p['description'], confidence=p['confidence'],
            evidence_count=p['evidence_count'],
            learned_from=p['learned_from'],
            rule=p['rule'], created_at=int(time.time()),
            status=p['status'],
            evolution=json.dumps(p['evolution'], ensure_ascii=False),
            rules=json.dumps(p['rules'], ensure_ascii=False),
            executions=json.dumps(p['executions'], ensure_ascii=False),
            applicable_scenarios=json.dumps(p['applicable_scenarios'], ensure_ascii=False),
            profile_id=active_profile.id if active_profile else None,
            slug=slug,
            trigger=json.dumps(p['trigger'], ensure_ascii=False) if isinstance(p['trigger'], dict) else p['trigger'],
            body=p['body'],
            source=p['source'] or 'imported',
            confidence_level=p['confidence_level'],
            learned_from_data=json.dumps(p['learned_from_data'], ensure_ascii=False),
        )
        db.add(pattern)
        db.flush()
        slug_to_id[slug] = pattern.id
        imported += 1

    for raw_workflow in req.workflows:
        fm = raw_workflow.get('frontmatter', {}) or {}
        wf_name = fm.get('name') or raw_workflow.get('slug') or 'Imported Workflow'
        wf_steps = fm.get('steps', [])
        workflow_pattern_ids = []
        for step in wf_steps:
            if 'pattern' in step and step['pattern'] in slug_to_id:
                workflow_pattern_ids.append(slug_to_id[step['pattern']])

        existing = db.query(TeamWorkflow).filter(TeamWorkflow.name == wf_name).first()
        if existing:
            existing.description = raw_workflow.get('body', existing.description)
            existing.profile_id = active_profile.id if active_profile else existing.profile_id
            existing.patterns = json.dumps(workflow_pattern_ids, ensure_ascii=False)
            existing.steps = json.dumps(wf_steps, ensure_ascii=False)
            imported_workflows += 1
            continue

        db.add(TeamWorkflow(
            name=wf_name,
            description=raw_workflow.get('body', ''),
            profile_id=active_profile.id if active_profile else None,
            patterns=json.dumps(workflow_pattern_ids, ensure_ascii=False),
            target_team='Imported',
            status='draft',
            created_at=int(time.time()),
            steps=json.dumps(wf_steps, ensure_ascii=False),
        ))
        imported_workflows += 1
    db.commit()
    return {'imported': imported, 'workflows': imported_workflows}


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
    # ClawProfile v1
    slug: str | None = None
    trigger: dict | str | None = None
    body: str | None = None
    source: str = 'manual'
    confidence_level: str | None = None
    learned_from_data: list[dict] = []


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
    # ClawProfile v1
    slug: str | None = None
    trigger: dict | str | None = None
    body: str | None = None
    source: str | None = None
    confidence_level: str | None = None
    learned_from_data: list[dict] | None = None


@router.post("/patterns")
def create_pattern(req: PatternCreateRequest, db: Session = Depends(get_db)):
    active_profile = db.query(ClawProfile).filter(ClawProfile.is_active == 1).first()
    pattern = BehaviorPattern(
        name=req.name, category=req.category, description=req.description,
        confidence=req.confidence, evidence_count=req.evidence_count,
        learned_from=req.learned_from, rule=req.rule,
        created_at=int(time.time()), status=req.status,
        evolution=json.dumps(req.evolution), rules=json.dumps(req.rules),
        executions=json.dumps(req.executions),
        applicable_scenarios=json.dumps(req.applicable_scenarios),
        profile_id=active_profile.id if active_profile else None,
        slug=req.slug, body=req.body, source=req.source,
        confidence_level=req.confidence_level,
        trigger=json.dumps(req.trigger) if isinstance(req.trigger, dict) else req.trigger,
        learned_from_data=json.dumps(req.learned_from_data),
    )
    db.add(pattern)
    db.commit()
    db.refresh(pattern)
    return _row_to_dict(pattern)


@router.get("/patterns/pending")
def get_pending_patterns(db: Session = Depends(get_db)):
    rows = db.query(BehaviorPattern).filter(
        BehaviorPattern.confidence >= 70,
        BehaviorPattern.status == 'learning',
    ).all()
    return [_row_to_dict(r) for r in rows]


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
    if req.slug is not None:
        row.slug = req.slug
    if req.trigger is not None:
        row.trigger = json.dumps(req.trigger) if isinstance(req.trigger, dict) else req.trigger
    if req.body is not None:
        row.body = req.body
    if req.source is not None:
        row.source = req.source
    if req.confidence_level is not None:
        row.confidence_level = req.confidence_level
    if req.learned_from_data is not None:
        row.learned_from_data = json.dumps(req.learned_from_data)
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
    active = db.query(ClawProfile).filter(ClawProfile.is_active == 1).first()
    q = db.query(TeamWorkflow)
    if active:
        q = q.filter(TeamWorkflow.profile_id == active.id)
    rows = q.all()
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
    steps: list[dict] = []


class WorkflowUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    patterns: list[int] | None = None
    target_team: str | None = None
    status: str | None = None
    steps: list[dict] | None = None


@router.post("/workflows")
def create_workflow(req: WorkflowCreateRequest, db: Session = Depends(get_db)):
    active_profile = db.query(ClawProfile).filter(ClawProfile.is_active == 1).first()
    wf = TeamWorkflow(
        name=req.name, description=req.description,
        profile_id=active_profile.id if active_profile else None,
        patterns=json.dumps(req.patterns), target_team=req.target_team,
        status='draft', created_at=int(time.time()),
        steps=json.dumps(req.steps),
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
    if req.steps is not None:
        row.steps = json.dumps(req.steps)
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
from services.pattern_confirm import confirm_pattern, reject_pattern


@router.post("/patterns/mine")
def mine_patterns(db: Session = Depends(get_db)):
    results = run_mining(db)
    return {'patterns': results, 'count': len(results)}


@router.post("/patterns/{pattern_id}/confirm")
def confirm_pattern_api(pattern_id: int, db: Session = Depends(get_db)):
    return confirm_pattern(db, pattern_id)


@router.post("/patterns/{pattern_id}/reject")
def reject_pattern_api(pattern_id: int, db: Session = Depends(get_db)):
    return reject_pattern(db, pattern_id)

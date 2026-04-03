import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db import get_db
from models.skill import Skill
from models.skill_workflow import SkillWorkflow
from schemas.skill import SkillResponse
from services.skill_planner import generate_learning_plan
from services.skill_recommender import (
    bulk_skill_improvement_report,
    recommend_skills,
    suggest_skill_improvements,
)
from services.skill_discovery import get_discovery_report, import_skills_as_patterns
from services.skill_tracker import mine_skill_workflows, get_skill_cot_stats, track_skill_invocation

router = APIRouter(tags=["skills"])


@router.get("/skills", response_model=list[SkillResponse])
def get_skills(db: Session = Depends(get_db)):
    rows = db.query(Skill).order_by(Skill.level.desc()).all()
    def _jlist(raw):
        if not raw:
            return []
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError, ValueError):
            return []
    return [
        {
            'id': r.id, 'name': r.name, 'category': r.category, 'level': r.level,
            'total_uses': r.total_uses or 0,
            'cot_uses': r.cot_uses or 0,
            'manual_uses': r.manual_uses or 0,
            'auto_uses': r.auto_uses or 0,
            'combo_patterns': _jlist(r.combo_patterns),
            'workflow_roles': _jlist(r.workflow_roles),
            'last_used': r.last_used or 0,
            'first_seen': r.first_seen or 0,
        }
        for r in rows
    ]


@router.get("/skills/recommendations")
def get_skill_recommendations(limit: int = 8, db: Session = Depends(get_db)):
    return recommend_skills(db, limit=max(1, min(limit, 24)))


@router.get("/skills/improvement-report")
def get_skill_improvement_report(db: Session = Depends(get_db)):
    return bulk_skill_improvement_report(db)


@router.get("/skills/discovery")
def get_skill_discovery(db: Session = Depends(get_db)):
    return get_discovery_report(db)


@router.post("/skills/import-from-library")
def post_import_skills_from_library(db: Session = Depends(get_db)):
    count = import_skills_as_patterns(db)
    return {"imported": count}


@router.get("/skills/{skill_id}/improvement")
def get_skill_improvement(skill_id: int, db: Session = Depends(get_db)):
    try:
        return suggest_skill_improvements(db, skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


class LearningPlanRequest(BaseModel):
    goal: str


@router.post("/skills/learning-plan")
def get_learning_plan(req: LearningPlanRequest, db: Session = Depends(get_db)):
    return generate_learning_plan(db, req.goal.strip())


class RecommendationFeedbackRequest(BaseModel):
    skill_name: str
    action: str = Field(..., pattern=r"^(useful|dismiss)$")


@router.post("/skills/recommendations/feedback")
def skill_recommendation_feedback(req: RecommendationFeedbackRequest, db: Session = Depends(get_db)):
    from models.behavior_pattern import BehaviorPattern
    from services.taste_model import record_pattern_decision

    pattern = db.query(BehaviorPattern).filter(BehaviorPattern.name == req.skill_name).first()
    if not pattern:
        pattern = BehaviorPattern(name=req.skill_name, category="skill_rec", source="recommendation", confidence=50)
        db.add(pattern)
        db.flush()
    decision = "confirm" if req.action == "useful" else "reject"
    reason = f"User marked recommendation '{req.skill_name}' as {req.action}"
    record_pattern_decision(db, pattern, decision, reason)
    return {"status": "ok"}


class TrackSkillRequest(BaseModel):
    name: str
    invocation_type: str
    combo_skills: list[str] = Field(default_factory=list)
    session_id: int | None = None
    trigger_source: str | None = None
    outcome: str | None = None


@router.get("/skills/workflows")
def get_skill_workflows(db: Session = Depends(get_db)):
    return mine_skill_workflows(db)


def _safe_json_list(raw: str | None) -> list:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


@router.get("/skills/workflows/mined")
def get_mined_skill_workflows(db: Session = Depends(get_db)):
    rows = (
        db.query(SkillWorkflow)
        .order_by(SkillWorkflow.frequency.desc(), SkillWorkflow.id.asc())
        .all()
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "sequence": _safe_json_list(r.skill_sequence),
            "frequency": r.frequency or 0,
            "success_rate": float(r.success_rate or 0.0),
            "source": r.source or "mined",
            "matched_pattern_ids": _safe_json_list(r.matched_pattern_ids),
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "description": r.description,
            "trigger": r.trigger,
            "steps": _safe_json_list(r.steps) if r.steps else [],
            "status": r.status or "draft",
            "context_tags": _safe_json_list(r.context_tags) if r.context_tags else [],
            "confirmed_by": r.confirmed_by,
        }
        for r in rows
    ]


@router.get("/skills/cot-stats")
def get_skill_stats(db: Session = Depends(get_db)):
    return get_skill_cot_stats(db)


@router.post("/skills/track")
def track_skill(req: TrackSkillRequest, db: Session = Depends(get_db)):
    return track_skill_invocation(
        db,
        req.name.strip(),
        req.invocation_type.strip(),
        [item.strip() for item in req.combo_skills if item and item.strip()],
        session_id=req.session_id,
        trigger_source=req.trigger_source,
        outcome=req.outcome,
    )


class WorkflowStatusRequest(BaseModel):
    status: str = Field(..., pattern=r"^(draft|confirmed|archived)$")


@router.put("/skills/workflows/{workflow_id}/status")
def update_workflow_status(workflow_id: int, req: WorkflowStatusRequest, db: Session = Depends(get_db)):
    row = db.query(SkillWorkflow).filter(SkillWorkflow.id == workflow_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")
    import time
    row.status = req.status
    row.updated_at = int(time.time())
    if req.status == "confirmed":
        row.confirmed_by = "user"
    db.add(row)
    db.commit()
    return {"id": row.id, "status": row.status}

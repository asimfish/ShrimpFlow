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
from services.skill_discovery import get_discovery_report
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
        except Exception:
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


class TrackSkillRequest(BaseModel):
    name: str
    invocation_type: str
    combo_skills: list[str] = Field(default_factory=list)


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
    )

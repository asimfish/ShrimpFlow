from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from models.skill import Skill
from schemas.skill import SkillResponse
from services.skill_planner import generate_learning_plan

router = APIRouter(tags=["skills"])


@router.get("/skills", response_model=list[SkillResponse])
def get_skills(db: Session = Depends(get_db)):
    rows = db.query(Skill).order_by(Skill.level.desc()).all()
    return [{'id': r.id, 'name': r.name, 'category': r.category, 'level': r.level,
             'total_uses': r.total_uses, 'last_used': r.last_used, 'first_seen': r.first_seen} for r in rows]


class LearningPlanRequest(BaseModel):
    goal: str


@router.post("/skills/learning-plan")
def get_learning_plan(req: LearningPlanRequest, db: Session = Depends(get_db)):
    return generate_learning_plan(db, req.goal.strip())

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from models.skill import Skill
from schemas.skill import SkillResponse

router = APIRouter(tags=["skills"])


@router.get("/skills", response_model=list[SkillResponse])
def get_skills(db: Session = Depends(get_db)):
    rows = db.query(Skill).order_by(Skill.level.desc()).all()
    return [{'id': r.id, 'name': r.name, 'category': r.category, 'level': r.level,
             'total_uses': r.total_uses, 'last_used': r.last_used, 'first_seen': r.first_seen} for r in rows]

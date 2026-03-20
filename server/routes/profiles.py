import json
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from models.pattern import BehaviorPattern
from models.profile import ClawProfile
from models.workflow import TeamWorkflow

router = APIRouter(tags=["profiles"])


def _profile_to_dict(row: ClawProfile, db: Session) -> dict:
    pattern_count = db.query(BehaviorPattern).filter(BehaviorPattern.profile_id == row.id).count()
    workflow_count = db.query(TeamWorkflow).filter(TeamWorkflow.profile_id == row.id).count()
    return {
        "id": row.id,
        "schema": row.schema,
        "name": row.name,
        "display": row.display,
        "description": row.description,
        "author": row.author,
        "tags": json.loads(row.tags) if row.tags else [],
        "license": row.license,
        "forked_from": row.forked_from,
        "trust": row.trust,
        "injection": json.loads(row.injection) if row.injection else None,
        "is_active": bool(row.is_active),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "pattern_count": pattern_count,
        "workflow_count": workflow_count,
    }


class ProfileCreateRequest(BaseModel):
    name: str
    display: str
    description: str | None = None
    author: str | None = None
    tags: list[str] = []
    license: str | None = "public"
    forked_from: str | None = None
    trust: str = "local"
    injection: dict | None = None


class ProfileUpdateRequest(BaseModel):
    display: str | None = None
    description: str | None = None
    author: str | None = None
    tags: list[str] | None = None
    license: str | None = None
    forked_from: str | None = None
    trust: str | None = None
    injection: dict | None = None


@router.get("/profiles")
def list_profiles(db: Session = Depends(get_db)):
    rows = db.query(ClawProfile).order_by(ClawProfile.is_active.desc(), ClawProfile.updated_at.desc()).all()
    return [_profile_to_dict(row, db) for row in rows]


@router.get("/profiles/active")
def get_active_profile(db: Session = Depends(get_db)):
    row = db.query(ClawProfile).filter(ClawProfile.is_active == 1).first()
    if not row:
        raise HTTPException(status_code=404, detail="Active profile not found")
    return _profile_to_dict(row, db)


@router.post("/profiles")
def create_profile(req: ProfileCreateRequest, db: Session = Depends(get_db)):
    now = int(time.time())
    profile = ClawProfile(
        schema="clawprofile/v1",
        name=req.name,
        display=req.display,
        description=req.description,
        author=req.author,
        tags=json.dumps(req.tags, ensure_ascii=False),
        license=req.license,
        forked_from=req.forked_from,
        trust=req.trust,
        injection=json.dumps(req.injection, ensure_ascii=False) if req.injection else None,
        is_active=0,
        created_at=now,
        updated_at=now,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _profile_to_dict(profile, db)


@router.put("/profiles/{profile_id}")
def update_profile(profile_id: int, req: ProfileUpdateRequest, db: Session = Depends(get_db)):
    row = db.query(ClawProfile).filter(ClawProfile.id == profile_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    if req.display is not None:
        row.display = req.display
    if req.description is not None:
        row.description = req.description
    if req.author is not None:
        row.author = req.author
    if req.tags is not None:
        row.tags = json.dumps(req.tags, ensure_ascii=False)
    if req.license is not None:
        row.license = req.license
    if req.forked_from is not None:
        row.forked_from = req.forked_from
    if req.trust is not None:
        row.trust = req.trust
    if req.injection is not None:
        row.injection = json.dumps(req.injection, ensure_ascii=False)
    row.updated_at = int(time.time())
    db.commit()
    db.refresh(row)
    return _profile_to_dict(row, db)


@router.post("/profiles/{profile_id}/activate")
def activate_profile(profile_id: int, db: Session = Depends(get_db)):
    row = db.query(ClawProfile).filter(ClawProfile.id == profile_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    db.query(ClawProfile).update({"is_active": 0})
    row.is_active = 1
    row.updated_at = int(time.time())
    db.commit()
    db.refresh(row)
    return _profile_to_dict(row, db)

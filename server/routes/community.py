import json
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from models.community import SharedProfile, SharedPatternPack, SharedClawProfile

router = APIRouter(tags=["community"])


def _profile_to_dict(row: SharedProfile) -> dict:
    return {
        'id': row.id, 'username': row.username, 'avatar': row.avatar,
        'title': row.title, 'bio': row.bio, 'followers': row.followers,
        'patterns_count': row.patterns_count,
    }


def _normalize_workflow(raw: dict, fallback_id: int) -> dict:
    frontmatter = raw.get('frontmatter', {}) if isinstance(raw, dict) else {}
    steps = frontmatter.get('steps') if isinstance(frontmatter, dict) else raw.get('steps', [])
    name = ''
    if isinstance(frontmatter, dict):
        name = str(frontmatter.get('name', '')).strip()
    if not name and isinstance(raw, dict):
        name = str(raw.get('name') or raw.get('slug') or f'workflow-{fallback_id}').strip()
    description = ''
    if isinstance(raw, dict):
        description = str(raw.get('body') or raw.get('description') or '').strip()
    return {
        'id': raw.get('id', fallback_id) if isinstance(raw, dict) else fallback_id,
        'slug': raw.get('slug') if isinstance(raw, dict) else None,
        'name': name or f'workflow-{fallback_id}',
        'description': description,
        'steps': steps if isinstance(steps, list) else [],
    }


def _pack_to_dict(row: SharedPatternPack, db: Session) -> dict:
    author = db.query(SharedProfile).filter(SharedProfile.id == row.author_id).first()
    author_dict = _profile_to_dict(author) if author else {
        'id': 0, 'username': 'Unknown', 'avatar': '', 'title': '', 'bio': '', 'followers': 0, 'patterns_count': 0
    }
    return {
        'id': row.id,
        'author': author_dict,
        'name': row.name,
        'description': row.description,
        'category': row.category,
        'patterns': json.loads(row.patterns) if row.patterns else [],
        'downloads': row.downloads,
        'stars': row.stars,
        'tags': json.loads(row.tags) if row.tags else [],
        'created_at': row.created_at,
    }


def _shared_claw_profile_to_dict(row: SharedClawProfile, db: Session) -> dict:
    author = db.query(SharedProfile).filter(SharedProfile.id == row.author_id).first()
    author_dict = _profile_to_dict(author) if author else {
        'id': 0, 'username': 'Unknown', 'avatar': '', 'title': '', 'bio': '', 'followers': 0, 'patterns_count': 0
    }
    workflows = json.loads(row.workflows) if row.workflows else []
    return {
        'id': row.id,
        'author': author_dict,
        'name': row.name,
        'display': row.display or row.name,
        'description': row.description,
        'profile': json.loads(row.profile) if row.profile else {},
        'patterns': json.loads(row.patterns) if row.patterns else [],
        'workflows': [_normalize_workflow(workflow, index + 1) for index, workflow in enumerate(workflows)],
        'downloads': row.downloads,
        'stars': row.stars,
        'tags': json.loads(row.tags) if row.tags else [],
        'created_at': row.created_at,
    }


@router.get("/community/profiles")
def get_profiles(db: Session = Depends(get_db)):
    rows = db.query(SharedProfile).all()
    return [_profile_to_dict(r) for r in rows]


@router.get("/community/profiles/{profile_id}")
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    row = db.query(SharedProfile).filter(SharedProfile.id == profile_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _profile_to_dict(row)


@router.get("/community/packs")
def get_packs(
    category: str = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(SharedPatternPack)
    if category:
        q = q.filter(SharedPatternPack.category == category)
    rows = q.order_by(SharedPatternPack.stars.desc()).all()
    return [_pack_to_dict(r, db) for r in rows]


@router.get("/community/packs/{pack_id}")
def get_pack(pack_id: int, db: Session = Depends(get_db)):
    row = db.query(SharedPatternPack).filter(SharedPatternPack.id == pack_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pack not found")
    return _pack_to_dict(row, db)


import time
from pydantic import BaseModel

class PackCreateRequest(BaseModel):
    name: str
    description: str
    category: str
    patterns: list[dict]
    tags: list[str]


class SharedClawProfileCreateRequest(BaseModel):
    name: str
    display: str
    description: str
    profile: dict
    patterns: list[dict]
    workflows: list[dict]
    tags: list[str]

@router.post("/community/packs")
def create_pack(req: PackCreateRequest, db: Session = Depends(get_db)):
    # 默认 author_id=1
    pack = SharedPatternPack(
        author_id=1, name=req.name, description=req.description,
        category=req.category, patterns=json.dumps(req.patterns),
        downloads=0, stars=0, tags=json.dumps(req.tags),
        created_at=int(time.time()),
    )
    db.add(pack)
    db.commit()
    db.refresh(pack)
    return _pack_to_dict(pack, db)

@router.post("/community/packs/{pack_id}/star")
def star_pack(pack_id: int, db: Session = Depends(get_db)):
    row = db.query(SharedPatternPack).filter(SharedPatternPack.id == pack_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pack not found")
    row.stars = row.stars + 1
    db.commit()
    return {'stars': row.stars}

@router.post("/community/packs/{pack_id}/download")
def download_pack(pack_id: int, db: Session = Depends(get_db)):
    row = db.query(SharedPatternPack).filter(SharedPatternPack.id == pack_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pack not found")
    row.downloads = row.downloads + 1
    db.commit()
    return _pack_to_dict(row, db)


@router.get("/community/claw-profiles")
def get_shared_claw_profiles(db: Session = Depends(get_db)):
    rows = db.query(SharedClawProfile).order_by(SharedClawProfile.stars.desc()).all()
    return [_shared_claw_profile_to_dict(row, db) for row in rows]


@router.get("/community/claw-profiles/{profile_id}")
def get_shared_claw_profile(profile_id: int, db: Session = Depends(get_db)):
    row = db.query(SharedClawProfile).filter(SharedClawProfile.id == profile_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Shared ClawProfile not found")
    return _shared_claw_profile_to_dict(row, db)


@router.post("/community/claw-profiles")
def create_shared_claw_profile(req: SharedClawProfileCreateRequest, db: Session = Depends(get_db)):
    row = SharedClawProfile(
        author_id=1,
        name=req.name,
        display=req.display,
        description=req.description,
        profile=json.dumps(req.profile, ensure_ascii=False),
        patterns=json.dumps(req.patterns, ensure_ascii=False),
        workflows=json.dumps(req.workflows, ensure_ascii=False),
        downloads=0,
        stars=0,
        tags=json.dumps(req.tags, ensure_ascii=False),
        created_at=int(time.time()),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _shared_claw_profile_to_dict(row, db)


@router.post("/community/claw-profiles/{profile_id}/star")
def star_shared_claw_profile(profile_id: int, db: Session = Depends(get_db)):
    row = db.query(SharedClawProfile).filter(SharedClawProfile.id == profile_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Shared ClawProfile not found")
    row.stars = row.stars + 1
    db.commit()
    return {'stars': row.stars}


@router.post("/community/claw-profiles/{profile_id}/download")
def download_shared_claw_profile(profile_id: int, db: Session = Depends(get_db)):
    row = db.query(SharedClawProfile).filter(SharedClawProfile.id == profile_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Shared ClawProfile not found")
    row.downloads = row.downloads + 1
    db.commit()
    return _shared_claw_profile_to_dict(row, db)

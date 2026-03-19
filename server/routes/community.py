import json
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from models.community import SharedProfile, SharedPatternPack

router = APIRouter(tags=["community"])


def _profile_to_dict(row: SharedProfile) -> dict:
    return {
        'id': row.id, 'username': row.username, 'avatar': row.avatar,
        'title': row.title, 'bio': row.bio, 'followers': row.followers,
        'patterns_count': row.patterns_count,
    }


def _pack_to_dict(row: SharedPatternPack, db: Session) -> dict:
    author = db.query(SharedProfile).filter(SharedProfile.id == row.author_id).first()
    author_dict = _profile_to_dict(author) if author else {
        'id': 0, 'username': 'Unknown', 'avatar': '', 'title': '', 'bio': '', 'followers': 0, 'patterns_count': 0
    }
    return {
        'id': row.id, 'author': author_dict, 'name': row.name,
        'description': row.description, 'category': row.category,
        'patterns': json.loads(row.patterns) if row.patterns else [],
        'downloads': row.downloads, 'stars': row.stars,
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

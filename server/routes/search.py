import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db import get_db
from models.event import DevEvent
from models.pattern import BehaviorPattern
from models.openclaw import OpenClawSession
from models.community import SharedPatternPack
from services.content_labels import detect_origin, summarize_session_title

router = APIRouter(tags=["search"])


@router.get("/search")
def global_search(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    results = {'events': [], 'patterns': [], 'sessions': [], 'packs': []}

    # 搜索事件
    events = db.query(DevEvent).filter(DevEvent.action.contains(q)).limit(10).all()
    results['events'] = [
        {
            'id': e.id,
            'action': e.action,
            'source': detect_origin(json.loads(e.tags) if e.tags else [], fallback='vscode' if e.source == 'vscode_cursor' else e.source),
            'project': e.project,
        }
        for e in events
    ]

    # 搜索模式
    patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.name.contains(q) | BehaviorPattern.description.contains(q)
    ).limit(10).all()
    results['patterns'] = [{'id': p.id, 'name': p.name, 'category': p.category} for p in patterns]

    # 搜索会话
    sessions = db.query(OpenClawSession).filter(
        OpenClawSession.title.contains(q) | OpenClawSession.summary.contains(q)
    ).limit(10).all()
    results['sessions'] = [
        {
            'id': s.id,
            'title': summarize_session_title(json.loads(s.messages) if s.messages else [], s.title, s.category),
            'category': s.category,
            'origin': detect_origin(json.loads(s.tags) if s.tags else [], fallback='openclaw'),
        }
        for s in sessions
    ]

    # 搜索社区包
    packs = db.query(SharedPatternPack).filter(
        SharedPatternPack.name.contains(q) | SharedPatternPack.description.contains(q)
    ).limit(10).all()
    results['packs'] = [{'id': p.id, 'name': p.name, 'category': p.category} for p in packs]

    return results

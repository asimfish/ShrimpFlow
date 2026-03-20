import json
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from models.openclaw import OpenClawSession, OpenClawDocument
from services.openclaw_runtime import analyze_session_with_active_profile

router = APIRouter(tags=["openclaw"])


def _session_to_dict(row: OpenClawSession) -> dict:
    return {
        'id': row.id, 'title': row.title, 'category': row.category,
        'messages': json.loads(row.messages) if row.messages else [],
        'project': row.project, 'tags': json.loads(row.tags) if row.tags else [],
        'profile_id': row.profile_id,
        'injected_pattern_slugs': json.loads(row.injected_pattern_slugs) if row.injected_pattern_slugs else [],
        'analysis_summary': row.analysis_summary,
        'analysis_status': row.analysis_status,
        'created_at': row.created_at, 'summary': row.summary,
    }


def _doc_to_dict(row: OpenClawDocument) -> dict:
    return {
        'id': row.id, 'title': row.title, 'type': row.type,
        'content': row.content, 'tags': json.loads(row.tags) if row.tags else [],
        'profile_id': row.profile_id,
        'created_at': row.created_at, 'source_session_id': row.source_session_id,
    }


@router.get("/openclaw/sessions")
def get_sessions(
    category: str = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(OpenClawSession).order_by(OpenClawSession.created_at.desc())
    if category:
        q = q.filter(OpenClawSession.category == category)
    return [_session_to_dict(r) for r in q.all()]


@router.get("/openclaw/sessions/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)):
    row = db.query(OpenClawSession).filter(OpenClawSession.id == session_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_to_dict(row)


@router.get("/openclaw/documents")
def get_documents(db: Session = Depends(get_db)):
    rows = db.query(OpenClawDocument).filter(
        OpenClawDocument.type != 'claude_session_index',
    ).order_by(OpenClawDocument.created_at.desc()).all()
    return [_doc_to_dict(r) for r in rows]


@router.get("/openclaw/documents/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db)):
    row = db.query(OpenClawDocument).filter(OpenClawDocument.id == doc_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_to_dict(row)


@router.post("/openclaw/sessions/{session_id}/analyze")
def analyze_session(session_id: int, db: Session = Depends(get_db)):
    try:
        return analyze_session_with_active_profile(db, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

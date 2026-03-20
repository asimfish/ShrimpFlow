import json
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from models.openclaw import OpenClawSession, OpenClawDocument
from services.content_labels import (
    build_index_label,
    derive_project_label,
    detect_origin,
    origin_label,
    summarize_document_preview,
    summarize_document_title,
    summarize_session_summary,
    summarize_session_title,
)
from services.openclaw_runtime import analyze_session_with_active_profile, list_session_invocations

router = APIRouter(tags=["openclaw"])


def _session_to_dict(row: OpenClawSession) -> dict:
    messages = json.loads(row.messages) if row.messages else []
    tags = json.loads(row.tags) if row.tags else []
    origin = detect_origin(tags, fallback="openclaw")
    project = derive_project_label(row.project or "", messages)
    return {
        'id': row.id, 'title': row.title, 'category': row.category,
        'messages': messages,
        'project': project, 'tags': tags,
        'profile_id': row.profile_id,
        'injected_pattern_slugs': json.loads(row.injected_pattern_slugs) if row.injected_pattern_slugs else [],
        'analysis_summary': row.analysis_summary,
        'analysis_status': row.analysis_status,
        'created_at': row.created_at, 'summary': row.summary,
        'origin': origin,
        'origin_label': origin_label(origin),
        'index_label': build_index_label('S', row.id),
        'display_title': summarize_session_title(messages, row.title, row.category),
        'display_summary': summarize_session_summary(messages, row.summary or '', project, origin, row.category),
    }


def _doc_to_dict(row: OpenClawDocument) -> dict:
    tags = json.loads(row.tags) if row.tags else []
    origin = detect_origin(tags, fallback="openclaw")
    return {
        'id': row.id, 'title': row.title, 'type': row.type,
        'content': row.content, 'tags': tags,
        'profile_id': row.profile_id,
        'created_at': row.created_at, 'source_session_id': row.source_session_id,
        'origin': origin,
        'origin_label': origin_label(origin),
        'index_label': build_index_label('K', row.id),
        'display_title': summarize_document_title(row.title, row.type, row.content or ''),
        'preview_excerpt': summarize_document_preview(row.content or '', row.title),
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
        ~OpenClawDocument.type.in_(('claude_session_index', 'codex_session_index')),
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


@router.get("/openclaw/sessions/{session_id}/invocations")
def get_session_invocations(session_id: int, db: Session = Depends(get_db)):
    return list_session_invocations(db, session_id)

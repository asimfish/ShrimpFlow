import json
import time
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from models.event import DevEvent

router = APIRouter(tags=["collector"])


class CollectEventRequest(BaseModel):
    source: str
    action: str
    directory: str = ''
    project: str = ''
    branch: str = ''
    exit_code: int = 0
    duration_ms: int = 0
    semantic: str = ''
    tags: list[str] = []
    openclaw_session_id: int | None = None


@router.post("/collect/event")
def collect_event(req: CollectEventRequest, db: Session = Depends(get_db)):
    event = DevEvent(
        timestamp=int(time.time()),
        source=req.source,
        action=req.action,
        directory=req.directory,
        project=req.project,
        branch=req.branch,
        exit_code=req.exit_code,
        duration_ms=req.duration_ms,
        semantic=req.semantic,
        tags=json.dumps(req.tags),
        openclaw_session_id=req.openclaw_session_id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {'id': event.id, 'status': 'ok'}


@router.post("/collect/terminal")
def collect_terminal(req: CollectEventRequest, db: Session = Depends(get_db)):
    req.source = 'terminal'
    return collect_event(req, db)


@router.post("/collect/git")
def collect_git(req: CollectEventRequest, db: Session = Depends(get_db)):
    req.source = 'git'
    return collect_event(req, db)


@router.post("/collect/openclaw")
def collect_openclaw(req: CollectEventRequest, db: Session = Depends(get_db)):
    req.source = 'openclaw'
    return collect_event(req, db)


from services.real_data_collector import (
    collect_shell_history, collect_claude_code,
    collect_clawd_docs, collect_git_history, collect_all,
)


@router.post("/collect/shell-history")
def api_collect_shell(db: Session = Depends(get_db)):
    from services.real_data_collector import collect_shell_history
    result = collect_shell_history(db)
    return result.to_dict()


@router.post("/collect/claude-code")
def api_collect_claude(db: Session = Depends(get_db)):
    from services.real_data_collector import collect_claude_code
    result = collect_claude_code(db)
    return result.to_dict()


@router.post("/collect/clawd")
def api_collect_clawd(db: Session = Depends(get_db)):
    from services.real_data_collector import collect_clawd_docs
    result = collect_clawd_docs(db)
    return result.to_dict()


@router.post("/collect/git-history")
def api_collect_git(db: Session = Depends(get_db)):
    from services.real_data_collector import collect_git_history
    result = collect_git_history(db)
    return result.to_dict()


@router.post("/collect/all")
def api_collect_all(db: Session = Depends(get_db)):
    from services.real_data_collector import collect_all
    results = collect_all(db)
    return {'results': results}

import json
import time
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from models.event import DevEvent
from routes.events import notify_new_event

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
    notify_new_event({
        'id': event.id,
        'timestamp': event.timestamp,
        'source': event.source,
        'action': event.action,
        'project': event.project,
        'branch': event.branch,
        'directory': event.directory,
        'exit_code': event.exit_code,
        'duration_ms': event.duration_ms,
        'semantic': event.semantic,
        'tags': req.tags,
        'openclaw_session_id': event.openclaw_session_id,
    })
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


@router.post("/collect/all-and-analyze")
def api_collect_all_and_analyze(db: Session = Depends(get_db)):
    from services.real_data_collector import collect_all
    from services.pattern_mining import run_mining
    from services.ai_summary import generate_pattern_description, generate_daily_summary
    from models.pattern import BehaviorPattern
    from models.event import DevEvent
    from models.digest import DailySummary
    from datetime import datetime, timezone
    from sqlalchemy import func, distinct
    import json as _json

    results = collect_all(db)
    mined = run_mining(db)

    # 对新挖掘的模式尝试 AI 增强描述
    for p_dict in mined:
        row = db.query(BehaviorPattern).filter(BehaviorPattern.name == p_dict['name']).first()
        if row and row.learned_from == 'auto_mining':
            examples = _json.loads(row.applicable_scenarios) if row.applicable_scenarios else []
            desc = generate_pattern_description(row.name, examples)
            if desc and desc != row.description:
                row.description = desc
    db.commit()

    # 为所有有真实事件的日期重新生成摘要，避免 seed 摘要长期污染
    event_dates = db.query(
        func.strftime('%Y-%m-%d', DevEvent.timestamp, 'unixepoch').label('d')
    ).filter(
        ~DevEvent.tags.contains('"seed"'),
    ).distinct().all()
    generated_count = 0
    for (date_str,) in event_dates:
        if not date_str:
            continue
        generate_daily_summary(db, date_str)
        generated_count += 1

    # 也更新今日摘要
    today_str = datetime.now().strftime('%Y-%m-%d')
    generate_daily_summary(db, today_str)

    return {'results': results, 'mining_count': len(mined), 'digest_updated': True, 'digests_generated': generated_count}

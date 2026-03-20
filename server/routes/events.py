import json
import time
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db import get_db
from models.event import DevEvent
from schemas.event import DevEventResponse

router = APIRouter(tags=["events"])


def _normalized_source(row: DevEvent, tags: list[str]) -> str:
    if row.source != 'vscode_cursor':
        return row.source
    tag_set = {tag.lower() for tag in tags}
    if 'cursor' in tag_set:
        return 'cursor'
    if 'vscode' in tag_set or 'code' in tag_set:
        return 'vscode'
    return 'vscode'


def _row_to_dict(row: DevEvent) -> dict:
    tags = json.loads(row.tags) if row.tags else []
    return {
        'id': row.id, 'timestamp': row.timestamp, 'source': _normalized_source(row, tags),
        'action': row.action, 'directory': row.directory, 'project': row.project,
        'branch': row.branch, 'exit_code': row.exit_code, 'duration_ms': row.duration_ms,
        'semantic': row.semantic, 'tags': tags,
        'openclaw_session_id': row.openclaw_session_id,
    }


@router.get("/events", response_model=list[DevEventResponse])
def get_events(
    source: str = Query(None),
    project: str = Query(None),
    search: str = Query(None),
    time_range: str = Query(None),
    limit: int = Query(5000),
    include_seed: bool = Query(False),
    db: Session = Depends(get_db),
):
    q = db.query(DevEvent).order_by(DevEvent.timestamp.desc())
    if not include_seed:
        q = q.filter(~DevEvent.tags.contains('"seed"'))
    if source:
        q = q.filter(DevEvent.source == source)
    if project:
        q = q.filter(DevEvent.project == project)
    if search:
        q = q.filter(DevEvent.action.contains(search))
    if time_range:
        now = int(time.time())
        DAY = 86400
        cutoff_map = {'today': now - DAY, 'week': now - 7 * DAY, 'month': now - 30 * DAY}
        cutoff = cutoff_map.get(time_range)
        if cutoff:
            q = q.filter(DevEvent.timestamp >= cutoff)
    rows = q.limit(limit).all()
    return [_row_to_dict(r) for r in rows]


import asyncio
from fastapi.responses import StreamingResponse

# 简单的事件队列（内存中）
_event_subscribers: list = []


def notify_new_event(event_data: dict):
    for q in list(_event_subscribers):
        try:
            q.put_nowait(event_data)
        except Exception:
            pass


async def _event_generator():
    q = asyncio.Queue()
    _event_subscribers.append(q)
    try:
        while True:
            try:
                data = await asyncio.wait_for(q.get(), timeout=30)
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        if q in _event_subscribers:
            _event_subscribers.remove(q)


@router.get("/events/stream")
async def stream_events():
    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/events/{event_id}", response_model=DevEventResponse)
def get_event(event_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    row = db.query(DevEvent).filter(DevEvent.id == event_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")
    return _row_to_dict(row)

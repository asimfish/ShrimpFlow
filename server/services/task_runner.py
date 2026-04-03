import json
import time
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from db import SessionLocal


def get_fresh_session() -> Session:
    """Create an independent DB session for background tasks."""
    return SessionLocal()


def _now_ts() -> int:
    return int(time.time())


def create_task(db: Session, task_type: str) -> str:
    task_id = str(uuid.uuid4())
    now = _now_ts()
    db.execute(
        text(
            "INSERT INTO background_tasks (id, task_type, status, progress, stage, created_at, updated_at) "
            "VALUES (:id, :task_type, 'pending', 0, '等待开始', :now, :now)"
        ),
        {"id": task_id, "task_type": task_type, "now": now},
    )
    db.commit()
    return task_id


def update_task(
    db: Session,
    task_id: str,
    status: str,
    progress: int,
    stage: str,
    result=None,
    error: str | None = None,
) -> None:
    now = _now_ts()
    db.execute(
        text(
            "UPDATE background_tasks "
            "SET status=:status, progress=:progress, stage=:stage, "
            "result=:result, error=:error, updated_at=:now "
            "WHERE id=:id"
        ),
        {
            "status": status,
            "progress": progress,
            "stage": stage,
            "result": json.dumps(result, ensure_ascii=False) if result is not None else None,
            "error": error,
            "now": now,
            "id": task_id,
        },
    )
    db.commit()


def get_task(db: Session, task_id: str) -> dict | None:
    row = db.execute(
        text("SELECT id, task_type, status, progress, stage, result, error, created_at, updated_at "
             "FROM background_tasks WHERE id=:id"),
        {"id": task_id},
    ).fetchone()
    if not row:
        return None
    return _row_to_dict(row)


def list_tasks(db: Session, task_type: str | None = None, limit: int = 20) -> list:
    if task_type:
        rows = db.execute(
            text(
                "SELECT id, task_type, status, progress, stage, result, error, created_at, updated_at "
                "FROM background_tasks WHERE task_type=:task_type "
                "ORDER BY created_at DESC LIMIT :limit"
            ),
            {"task_type": task_type, "limit": limit},
        ).fetchall()
    else:
        rows = db.execute(
            text(
                "SELECT id, task_type, status, progress, stage, result, error, created_at, updated_at "
                "FROM background_tasks ORDER BY created_at DESC LIMIT :limit"
            ),
            {"limit": limit},
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row) -> dict:
    result_raw = row[5]
    result = None
    if result_raw:
        try:
            result = json.loads(result_raw)
        except Exception:
            result = result_raw
    return {
        "id": row[0],
        "task_type": row[1],
        "status": row[2],
        "progress": row[3],
        "stage": row[4],
        "result": result,
        "error": row[6],
        "created_at": row[7],
        "updated_at": row[8],
    }

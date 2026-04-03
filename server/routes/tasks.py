from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from services.task_runner import get_task, list_tasks

router = APIRouter(tags=["tasks"])


@router.get("/tasks/{task_id}")
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/tasks")
def get_tasks(task_type: str | None = None, limit: int = 20, db: Session = Depends(get_db)):
    return list_tasks(db, task_type=task_type, limit=min(limit, 50))

import logging
import threading
import time

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import SessionLocal, get_db
from models.pattern import BehaviorPattern
from services.task_runner import create_task, get_fresh_session, get_task, update_task
from services.taste_model import (
    auto_confirm_patterns,
    get_or_create_taste_profile,
    get_pending_pattern_recommendations,
    get_taste_dashboard_stats,
    learn_from_history,
    log_autonomous_action,
    record_pattern_decision,
    serialize_taste_profile,
    suggest_autonomous_tasks,
)

logger = logging.getLogger(__name__)

# 批准后可后台执行的任务类型（其余仅记录偏好并记日志，不执行）
_APPROVED_TASK_EXEC_WHITELIST = frozenset({"mine_patterns", "collect", "taste_auto_confirm"})

router = APIRouter(tags=["agent-taste"])

# 后台 AI 学习的最短间隔（秒），避免频繁触发
_RELEARN_INTERVAL = 3600
_relearn_lock = threading.Lock()
_last_relearn_at = 0


def _background_relearn():
    """在独立线程中执行 AI 学习，使用独立 DB session。"""
    global _last_relearn_at
    with _relearn_lock:
        # 双重检查，防止并发重复触发
        if time.time() - _last_relearn_at < _RELEARN_INTERVAL:
            return
        _last_relearn_at = time.time()
    db = SessionLocal()
    try:
        learn_from_history(db)
    except Exception:
        pass
    finally:
        db.close()


def _should_relearn(profile) -> bool:
    """判断是否需要触发 AI 学习。"""
    if time.time() - _last_relearn_at < _RELEARN_INTERVAL:
        return False
    # profile 从未学习过，或距上次更新超过间隔
    updated_at = profile.updated_at or 0
    return time.time() - updated_at >= _RELEARN_INTERVAL


@router.get("/agent-taste")
def get_agent_taste_profile(db: Session = Depends(get_db)):
    # 立即返回缓存数据
    profile = get_or_create_taste_profile(db)
    payload = serialize_taste_profile(profile)
    payload.update(get_taste_dashboard_stats(db))
    payload["top_pending"] = [
        {
            "id": item["pattern"].id,
            "name": item["pattern"].name,
            "category": item["pattern"].category,
            "confidence": item["pattern"].confidence,
            "source": item["pattern"].source,
            "taste_action": item["action"],
            "priority_score": item["priority_score"],
            "taste_reasons": item["reasons"],
        }
        for item in get_pending_pattern_recommendations(db)[:10]
    ]
    # 后台异步触发 AI 学习（不阻塞响应）
    if _should_relearn(profile):
        threading.Thread(target=_background_relearn, daemon=True).start()
    return payload


@router.get("/agent-taste/autonomous-suggestions")
def get_autonomous_suggestions(db: Session = Depends(get_db)):
    """Taste-driven autonomous task ideas (suggestions only; never executes)."""
    return {"suggestions": suggest_autonomous_tasks(db)}


@router.post("/agent-taste/auto-confirm")
def run_auto_confirm(db: Session = Depends(get_db)):
    return auto_confirm_patterns(db)


class ApproveTaskRequest(BaseModel):
    task: str


def _run_mine_patterns_background(task_id: str) -> None:
    db = get_fresh_session()
    try:
        update_task(db, task_id, "running", 10, "正在挖掘模式…")
        from services.pattern_mining import run_mining

        mined = run_mining(db)
        result = {"mining_count": len(mined)}
        update_task(db, task_id, "done", 100, "完成", result=result)
        log_autonomous_action(db, "mine_patterns", f"mining_count={len(mined)}")
    except Exception as e:
        update_task(db, task_id, "error", 0, "出错", error=str(e))
        try:
            log_autonomous_action(db, "mine_patterns", f"error: {e}")
        except Exception:
            pass
    finally:
        db.close()


def _run_taste_auto_confirm_background(task_id: str) -> None:
    db = get_fresh_session()
    try:
        update_task(db, task_id, "running", 30, "品味自动确认…")
        out = auto_confirm_patterns(db)
        update_task(db, task_id, "done", 100, "完成", result=out)
        log_autonomous_action(
            db,
            "taste_auto_confirm",
            f"confirmed={out.get('confirmed')}, deferred={out.get('deferred')}, collect_more={out.get('collect_more')}",
        )
    except Exception as e:
        update_task(db, task_id, "error", 0, "出错", error=str(e))
        try:
            log_autonomous_action(db, "taste_auto_confirm", f"error: {e}")
        except Exception:
            pass
    finally:
        db.close()


def _run_collect_approved_background(task_id: str) -> None:
    from routes.collector import _run_collect_background

    _run_collect_background(task_id)
    db = get_fresh_session()
    try:
        row = get_task(db, task_id)
        if row:
            if row.get("status") == "done":
                r = row.get("result") or {}
                summary = (
                    f"mining_count={r.get('mining_count')}, deep_mining_count={r.get('deep_mining_count')}, "
                    f"patterns_pushed={r.get('patterns_pushed')}"
                )
            else:
                summary = f"status={row.get('status')} error={row.get('error')}"
            log_autonomous_action(db, "collect", summary)
    except Exception as e:
        logger.warning("collect approved log failed: %s", e)
    finally:
        db.close()


@router.post("/agent-taste/approve-task")
def approve_autonomous_task(
    req: ApproveTaskRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    pattern = db.query(BehaviorPattern).filter(BehaviorPattern.name == req.task).first()
    if not pattern:
        pattern = BehaviorPattern(name=req.task, category="autonomous", source="suggestion", confidence=60)
        db.add(pattern)
        db.flush()
    record_pattern_decision(db, pattern, "confirm", f"User approved autonomous task: {req.task}")

    task_id = None
    if req.task in _APPROVED_TASK_EXEC_WHITELIST:
        task_id = create_task(db, req.task)
        if req.task == "mine_patterns":
            background_tasks.add_task(_run_mine_patterns_background, task_id)
        elif req.task == "collect":
            background_tasks.add_task(_run_collect_approved_background, task_id)
        elif req.task == "taste_auto_confirm":
            background_tasks.add_task(_run_taste_auto_confirm_background, task_id)
    else:
        logger.info("approve-task: no execution for non-whitelisted task %s", req.task)
        try:
            log_autonomous_action(
                db,
                req.task,
                "skipped: not whitelisted for autonomous execution",
            )
        except Exception:
            pass

    return {"status": "approved", "task": req.task, "task_id": task_id}


@router.post("/agent-taste/relearn")
def relearn_agent_taste_profile(db: Session = Depends(get_db)):
    profile = learn_from_history(db)
    global _last_relearn_at
    _last_relearn_at = time.time()
    payload = serialize_taste_profile(profile)
    payload["top_pending"] = [
        {
            "id": item["pattern"].id,
            "name": item["pattern"].name,
            "category": item["pattern"].category,
            "confidence": item["pattern"].confidence,
            "source": item["pattern"].source,
            "taste_action": item["action"],
            "priority_score": item["priority_score"],
        }
        for item in get_pending_pattern_recommendations(db)[:10]
    ]
    return payload

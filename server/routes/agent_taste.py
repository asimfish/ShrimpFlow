import threading
import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import SessionLocal, get_db
from services.taste_model import (
    auto_confirm_patterns,
    get_or_create_taste_profile,
    get_pending_pattern_recommendations,
    learn_from_history,
    serialize_taste_profile,
    suggest_autonomous_tasks,
)

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

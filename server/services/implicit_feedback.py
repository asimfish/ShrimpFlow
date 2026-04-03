import json
import time
from collections import defaultdict

from sqlalchemy.orm import Session

from models.skill_implicit_event import SkillImplicitEvent


VALID_ACTIONS = {"click", "view", "impression", "search"}


def record_implicit_event(db: Session, skill_name: str, user_action: str, context: dict | None = None) -> dict:
    action = (user_action or "").strip().lower()
    if action not in VALID_ACTIONS:
        action = "view"

    name = (skill_name or "").strip()
    if not name:
        return {"error": "skill_name is required"}

    now = int(time.time())
    event = SkillImplicitEvent(
        user_action=action,
        skill_name=name,
        context=json.dumps(context, ensure_ascii=False) if context else None,
        created_at=now,
    )
    db.add(event)
    db.commit()
    return {"status": "ok", "action": action, "skill_name": name}


def get_implicit_signal(db: Session, skill_name: str) -> dict:
    """Get aggregated implicit feedback signal for a single skill."""
    rows = db.query(SkillImplicitEvent).filter(SkillImplicitEvent.skill_name == skill_name).all()
    counts: dict[str, int] = defaultdict(int)
    latest_ts = 0
    for row in rows:
        counts[row.user_action] += 1
        if row.created_at and row.created_at > latest_ts:
            latest_ts = row.created_at
    return {
        "skill_name": skill_name,
        "click": counts.get("click", 0),
        "view": counts.get("view", 0),
        "impression": counts.get("impression", 0),
        "search": counts.get("search", 0),
        "total": sum(counts.values()),
        "last_interaction": latest_ts,
    }


def get_aggregated_signals(db: Session) -> dict[str, dict]:
    """Get implicit feedback signals for all skills."""
    rows = db.query(SkillImplicitEvent).all()
    signals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    latest: dict[str, int] = defaultdict(int)
    for row in rows:
        signals[row.skill_name][row.user_action] += 1
        if row.created_at and row.created_at > latest[row.skill_name]:
            latest[row.skill_name] = row.created_at

    result = {}
    for name, counts in signals.items():
        result[name] = {
            "click": counts.get("click", 0),
            "view": counts.get("view", 0),
            "impression": counts.get("impression", 0),
            "search": counts.get("search", 0),
            "total": sum(counts.values()),
            "last_interaction": latest[name],
        }
    return result


def get_negative_signal(db: Session, min_impressions: int = 5) -> list[str]:
    """Find skills that have been shown (impression) but never clicked — implicit disinterest."""
    signals = get_aggregated_signals(db)
    negatives = []
    for name, data in signals.items():
        if data["impression"] >= min_impressions and data["click"] == 0:
            negatives.append(name)
    return negatives

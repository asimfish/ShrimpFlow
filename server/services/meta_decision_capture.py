import json
import time

from sqlalchemy.orm import Session

from models.meta_decision import MetaDecisionLog


def capture_decision_context(
    db: Session,
    decision_type: str,
    target_id: int | None,
    target_name: str,
    user_action: str,
    user_reason: str = "",
    system_recommendation: dict | None = None,
    extra_context: dict | None = None,
) -> MetaDecisionLog:
    """Capture a user decision with full context for Meta-Agent learning."""
    from models.pattern import BehaviorPattern
    from models.agent_taste import AgentTasteProfile

    taste_snapshot = None
    try:
        taste = db.query(AgentTasteProfile).order_by(AgentTasteProfile.id.desc()).first()
        if taste:
            taste_snapshot = json.dumps({
                "preferred_categories": taste.preferred_categories,
                "threshold": taste.preferred_confidence_threshold,
                "preferred_sources": taste.preferred_sources,
            }, ensure_ascii=False)
    except Exception:
        pass

    pending_count = db.query(BehaviorPattern).filter(
        BehaviorPattern.status.in_(["learning", "pending"])
    ).count()

    context = {
        "pending_patterns": pending_count,
        "timestamp": int(time.time()),
        **(extra_context or {}),
    }

    log = MetaDecisionLog(
        decision_type=decision_type,
        target_id=target_id,
        target_name=target_name,
        user_action=user_action,
        user_reason=user_reason,
        system_recommendation=json.dumps(system_recommendation, ensure_ascii=False) if system_recommendation else None,
        context_snapshot=json.dumps(context, ensure_ascii=False),
        taste_profile_snapshot=taste_snapshot,
        created_at=int(time.time()),
    )
    db.add(log)
    db.commit()
    return log


def get_decision_history(db: Session, limit: int = 50) -> list[dict]:
    """Get recent decision logs for Meta-Agent analysis."""
    rows = (
        db.query(MetaDecisionLog)
        .order_by(MetaDecisionLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "decision_type": r.decision_type,
            "target_id": r.target_id,
            "target_name": r.target_name,
            "user_action": r.user_action,
            "user_reason": r.user_reason,
            "system_recommendation": json.loads(r.system_recommendation) if r.system_recommendation else None,
            "context_snapshot": json.loads(r.context_snapshot) if r.context_snapshot else None,
            "taste_profile_snapshot": json.loads(r.taste_profile_snapshot) if r.taste_profile_snapshot else None,
            "created_at": r.created_at,
        }
        for r in rows
    ]


def get_meta_agent_maturity(db: Session) -> dict:
    """Compute Meta-Agent maturity score and level."""
    total = db.query(MetaDecisionLog).count()
    from models.meta_decision import MetaPolicy, MetaShadowLog
    policy_count = db.query(MetaPolicy).count()
    shadow_total = db.query(MetaShadowLog).filter(MetaShadowLog.matched.isnot(None)).count()
    shadow_match = db.query(MetaShadowLog).filter(MetaShadowLog.matched == 1).count()

    alignment_rate = round(shadow_match / shadow_total, 3) if shadow_total else 0

    score = 0
    if total >= 10:
        score += 20
    if policy_count >= 3:
        score += 20
    score += int(alignment_rate * 40)
    if alignment_rate >= 0.9 and shadow_total >= 20:
        score += 20

    levels = [
        (90, "Master"),
        (70, "Expert"),
        (45, "Competent"),
        (20, "Learning"),
        (0, "Infant"),
    ]
    level = "Infant"
    for threshold, name in levels:
        if score >= threshold:
            level = name
            break

    return {
        "score": min(100, score),
        "level": level,
        "total_decisions": total,
        "total_policies": policy_count,
        "alignment_rate": alignment_rate,
        "shadow_predictions": shadow_total,
    }

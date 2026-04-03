from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from services.meta_decision_capture import get_decision_history, get_meta_agent_maturity

router = APIRouter(tags=["meta-agent"])


@router.get("/meta-agent/decisions")
def list_decisions(limit: int = 50, db: Session = Depends(get_db)):
    return get_decision_history(db, limit=min(limit, 200))


class AnnotateDecisionRequest(BaseModel):
    reason: str


@router.post("/meta-agent/decisions/{decision_id}/annotate")
def annotate_decision(decision_id: int, req: AnnotateDecisionRequest, db: Session = Depends(get_db)):
    from models.meta_decision import MetaDecisionLog
    log = db.query(MetaDecisionLog).filter(MetaDecisionLog.id == decision_id).first()
    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Decision not found")
    log.user_reason = req.reason
    db.add(log)
    db.commit()
    return {"id": log.id, "user_reason": log.user_reason}


@router.get("/meta-agent/maturity")
def get_maturity(db: Session = Depends(get_db)):
    return get_meta_agent_maturity(db)


@router.get("/meta-agent/policies")
def list_policies(db: Session = Depends(get_db)):
    import json
    from models.meta_decision import MetaPolicy
    rows = db.query(MetaPolicy).order_by(MetaPolicy.confidence.desc()).all()
    return [
        {
            "id": r.id,
            "rule": r.rule,
            "conditions": json.loads(r.conditions) if r.conditions else None,
            "predicted_action": r.predicted_action,
            "confidence": r.confidence,
            "hit_count": r.hit_count,
            "miss_count": r.miss_count,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/meta-agent/shadow-stats")
def get_shadow_stats(db: Session = Depends(get_db)):
    from models.meta_decision import MetaShadowLog
    total = db.query(MetaShadowLog).filter(MetaShadowLog.matched.isnot(None)).count()
    matches = db.query(MetaShadowLog).filter(MetaShadowLog.matched == 1).count()
    mismatches = db.query(MetaShadowLog).filter(MetaShadowLog.matched == 0).count()
    pending = db.query(MetaShadowLog).filter(MetaShadowLog.matched.is_(None)).count()
    alignment_rate = round(matches / total, 3) if total else 0

    recent_mismatches = (
        db.query(MetaShadowLog)
        .filter(MetaShadowLog.matched == 0)
        .order_by(MetaShadowLog.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "total_predictions": total,
        "matches": matches,
        "mismatches": mismatches,
        "pending": pending,
        "alignment_rate": alignment_rate,
        "recent_mismatches": [
            {
                "id": r.id,
                "pattern_id": r.pattern_id,
                "predicted_action": r.predicted_action,
                "actual_action": r.actual_action,
                "predicted_reason": r.predicted_reason,
            }
            for r in recent_mismatches
        ],
    }

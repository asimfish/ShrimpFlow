import json
import time
from pathlib import Path

from sqlalchemy.orm import Session

from models.pattern import BehaviorPattern
from models.profile import ClawProfile
from models.workflow import TeamWorkflow

EXPORT_ROOT = Path(__file__).resolve().parents[1] / "automation" / "clawprofile_snapshots"


def _active_profile(db: Session) -> ClawProfile | None:
    return db.query(ClawProfile).filter(ClawProfile.is_active == 1).first()


def _pattern_to_export(row: BehaviorPattern) -> dict:
    trigger = None
    if row.trigger:
        try:
            trigger = json.loads(row.trigger) if row.trigger.startswith("{") else row.trigger
        except json.JSONDecodeError:
            trigger = row.trigger
    return {
        "slug": row.slug or row.name,
        "frontmatter": {
            "name": row.name,
            "confidence": row.confidence_level or "medium",
            "confidence_score": row.confidence,
            "category": row.category,
            "trigger": trigger,
            "evidence": row.evidence_count,
            "source": row.source or "auto",
            "learned_from": json.loads(row.learned_from_data) if row.learned_from_data else [],
        },
        "body": row.body or row.description or "",
        "evolution": json.loads(row.evolution) if row.evolution else [],
    }


def _workflow_to_export(row: TeamWorkflow) -> dict:
    return {
        "slug": row.name.lower().replace(" ", "-"),
        "frontmatter": {
            "name": row.name,
            "steps": json.loads(row.steps) if row.steps else [],
        },
        "body": row.description or "",
    }


def export_active_clawprofile_snapshot(db: Session) -> dict | None:
    profile = _active_profile(db)
    if not profile:
        return None

    patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.profile_id == profile.id,
        BehaviorPattern.status.in_(("confirmed", "exportable")),
    ).order_by(BehaviorPattern.confidence.desc()).all()
    workflows = db.query(TeamWorkflow).filter(
        TeamWorkflow.profile_id == profile.id,
    ).order_by(TeamWorkflow.created_at.desc()).all()

    payload = {
        "schema": profile.schema or "clawprofile/v1",
        "profile": {
            "name": profile.name,
            "display": profile.display,
            "description": profile.description,
            "author": profile.author,
            "tags": json.loads(profile.tags) if profile.tags else [],
            "license": profile.license,
            "trust": profile.trust,
            "injection": json.loads(profile.injection) if profile.injection else None,
        },
        "patterns": [_pattern_to_export(pattern) for pattern in patterns],
        "workflows": [_workflow_to_export(workflow) for workflow in workflows],
        "exported_at": int(time.time()),
    }

    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(payload["exported_at"]))
    latest_path = EXPORT_ROOT / "latest.clawprofile.json"
    stamped_path = EXPORT_ROOT / f"{stamp}.clawprofile.json"
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    latest_path.write_text(content, encoding="utf-8")
    stamped_path.write_text(content, encoding="utf-8")
    return {
        "profile": profile.display,
        "patterns": len(payload["patterns"]),
        "workflows": len(payload["workflows"]),
        "latest_path": str(latest_path),
        "snapshot_path": str(stamped_path),
    }


def auto_promote_patterns(db: Session) -> list[dict]:
    profile = _active_profile(db)
    if not profile:
        return []

    promoted = []
    rows = db.query(BehaviorPattern).filter(
        BehaviorPattern.profile_id == profile.id,
        BehaviorPattern.source == "auto",
        BehaviorPattern.status == "learning",
        BehaviorPattern.confidence >= 88,
        BehaviorPattern.evidence_count >= 6,
    ).all()

    now = time.strftime("%Y-%m-%d", time.localtime())
    for row in rows:
        row.status = "confirmed"
        evolution = json.loads(row.evolution) if row.evolution else []
        evolution.append({
            "date": now,
            "confidence": row.confidence,
            "event_description": "系统夜间自动晋级为 confirmed",
        })
        row.evolution = json.dumps(evolution, ensure_ascii=False)
        promoted.append({
            "id": row.id,
            "name": row.name,
            "confidence": row.confidence,
            "evidence_count": row.evidence_count,
        })

    if promoted:
        db.commit()
    return promoted

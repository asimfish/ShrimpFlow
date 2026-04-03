import json
import time
from collections import Counter

from models.invocation import OpenClawInvocationLog
from models.skill import Skill
from models.skill_workflow import SkillWorkflow


def _now_ts():
    return int(time.time())


def _load_json_list(raw):
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    values = []
    for item in data:
        text = str(item).strip()
        if text:
            values.append(text)
    return values


def _dump_json_list(values):
    deduped = []
    seen = set()
    for item in values or []:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        deduped.append(text)
    return json.dumps(deduped, ensure_ascii=False)


def _normalize_invoke_type(invoke_type):
    value = (invoke_type or "").strip().lower()
    if value in {"cot", "manual", "auto"}:
        return value
    return "auto"


def _normalize_sequence(skill_name, combo_skills):
    sequence = []
    for item in combo_skills or []:
        text = str(item).strip()
        if text and text not in sequence:
            sequence.append(text)
    if skill_name not in sequence:
        sequence = [skill_name] + sequence
    return sequence


def _infer_roles(skill_name, sequence):
    roles = []
    if len(sequence) <= 1:
        return roles

    for index, name in enumerate(sequence):
        if name != skill_name:
            continue
        if index == 0:
            roles.append("initiator")
        elif index == len(sequence) - 1:
            roles.append("finalizer")
        else:
            roles.append("middle")
    return list(dict.fromkeys(roles))


def _ensure_skill(db, skill_name):
    skill = db.query(Skill).filter(Skill.name == skill_name).first()
    if skill:
        return skill

    now = _now_ts()
    skill = Skill(
        name=skill_name,
        category="workflow",
        level=0,
        total_uses=0,
        cot_uses=0,
        manual_uses=0,
        auto_uses=0,
        combo_patterns=_dump_json_list([]),
        workflow_roles=_dump_json_list([]),
        last_used=now,
        first_seen=now,
    )
    db.add(skill)
    db.flush()
    return skill


def _skill_payload(skill):
    total = skill.total_uses or 0
    cot = skill.cot_uses or 0
    manual = skill.manual_uses or 0
    auto = max(total - cot - manual, 0)
    return {
        "id": skill.id,
        "name": skill.name,
        "category": skill.category,
        "level": skill.level,
        "total_uses": total,
        "cot_uses": cot,
        "manual_uses": manual,
        "auto_uses": auto,
        "last_used": skill.last_used,
        "first_seen": skill.first_seen,
        "combo_patterns": _load_json_list(skill.combo_patterns),
        "workflow_roles": _load_json_list(skill.workflow_roles),
    }


def track_skill_invocation(db, skill_name: str, invoke_type: str, combo_skills: list[str] = None):
    name = (skill_name or "").strip()
    if not name:
        raise ValueError("skill_name is required")

    normalized_type = _normalize_invoke_type(invoke_type)
    sequence = _normalize_sequence(name, combo_skills)
    combo_names = [item for item in sequence if item != name]
    workflow_roles = _infer_roles(name, sequence)

    skill = _ensure_skill(db, name)
    now = _now_ts()
    skill.total_uses = (skill.total_uses or 0) + 1
    if normalized_type == "cot":
        skill.cot_uses = (skill.cot_uses or 0) + 1
    elif normalized_type == "manual":
        skill.manual_uses = (skill.manual_uses or 0) + 1
    else:
        skill.auto_uses = (skill.auto_uses or 0) + 1

    skill.last_used = now
    if not skill.first_seen:
        skill.first_seen = now

    merged_combo_names = _load_json_list(skill.combo_patterns) + combo_names
    skill.combo_patterns = _dump_json_list(merged_combo_names)

    merged_roles = _load_json_list(skill.workflow_roles) + workflow_roles
    skill.workflow_roles = _dump_json_list(merged_roles)

    db.add(skill)
    db.commit()
    db.refresh(skill)
    return _skill_payload(skill)


def mine_skill_workflows(db) -> list[dict]:
    rows = db.query(
        OpenClawInvocationLog.selected_pattern_slugs,
        OpenClawInvocationLog.status,
    ).all()

    counts = Counter()
    success_counts = Counter()

    for selected_pattern_slugs, status in rows:
        sequence = _load_json_list(selected_pattern_slugs)
        if len(sequence) < 2:
            continue

        max_size = min(4, len(sequence))
        for size in range(2, max_size + 1):
            for start in range(0, len(sequence) - size + 1):
                window = tuple(sequence[start:start + size])
                counts[window] += 1
                if status == "ok":
                    success_counts[window] += 1

    workflows = []
    for sequence, count in counts.items():
        min_freq = 1 if len(sequence) == 2 else 3
        if count < min_freq:
            continue

        success_rate = round(success_counts[sequence] / count, 3)
        sequence_list = list(sequence)
        workflows.append({
            "name": " -> ".join(sequence_list),
            "sequence": sequence_list,
            "count": count,
            "success_rate": success_rate,
            "description": f"常见 workflow，连续出现 {count} 次，序列为 {' -> '.join(sequence_list)}",
        })

    workflows.sort(key=lambda item: (-item["count"], -len(item["sequence"]), item["name"]))
    _persist_mined_workflows(db, workflows)
    return workflows


def _persist_mined_workflows(db, workflows: list[dict]) -> None:
    """Upsert mined workflows into SkillWorkflow (skill_sequence JSON must match for identity)."""
    if not workflows:
        return
    now = _now_ts()
    for wf in workflows:
        sequence_list = wf.get("sequence") or []
        if not isinstance(sequence_list, list):
            continue
        seq_key = _dump_json_list(sequence_list)
        if not seq_key or seq_key == "[]":
            continue
        count = int(wf.get("count") or 0)
        success_rate = float(wf.get("success_rate") or 0.0)
        name = (wf.get("name") or "").strip() or seq_key
        existing = (
            db.query(SkillWorkflow)
            .filter(SkillWorkflow.skill_sequence == seq_key)
            .first()
        )
        if existing:
            # mine_skill_workflows() recomputes totals from all logs each call; replace avoids
            # inflating frequency when /skills/workflows is hit repeatedly (same as upsert by sequence).
            existing.frequency = count
            existing.success_rate = round(success_rate, 3)
            existing.name = name
            existing.source = existing.source or "mined"
            existing.updated_at = now
            db.add(existing)
        else:
            row = SkillWorkflow(
                name=name,
                skill_sequence=seq_key,
                frequency=count,
                success_rate=round(success_rate, 3),
                source="mined",
                created_at=now,
                updated_at=now,
            )
            db.add(row)
    db.commit()


def get_skill_cot_stats(db) -> dict:
    rows = db.query(Skill).order_by(Skill.total_uses.desc(), Skill.name.asc()).all()

    overall_total = 0
    overall_cot = 0
    overall_manual = 0
    skill_stats = []

    for row in rows:
        total = row.total_uses or 0
        cot = row.cot_uses or 0
        manual = row.manual_uses or 0
        auto = max(total - cot - manual, 0)

        overall_total += total
        overall_cot += cot
        overall_manual += manual

        skill_stats.append({
            "name": row.name,
            "total_uses": total,
            "cot_uses": cot,
            "manual_uses": manual,
            "auto_uses": auto,
            "cot_ratio": round(cot / total, 3) if total else 0,
            "manual_ratio": round(manual / total, 3) if total else 0,
            "auto_ratio": round(auto / total, 3) if total else 0,
            "combo_patterns": _load_json_list(row.combo_patterns),
            "workflow_roles": _load_json_list(row.workflow_roles),
            "last_used": row.last_used,
        })

    overall_auto = max(overall_total - overall_cot - overall_manual, 0)
    return {
        "overall": {
            "skill_count": len(rows),
            "total_uses": overall_total,
            "cot_uses": overall_cot,
            "manual_uses": overall_manual,
            "auto_uses": overall_auto,
            "cot_ratio": round(overall_cot / overall_total, 3) if overall_total else 0,
            "manual_ratio": round(overall_manual / overall_total, 3) if overall_total else 0,
            "auto_ratio": round(overall_auto / overall_total, 3) if overall_total else 0,
        },
        "skills": skill_stats,
    }


def track_skill_usage(event):
    return event


def calculate_skill_level(skill_id):
    return skill_id

import json
import time
from collections import defaultdict
from statistics import median

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.agent_taste import AgentTasteProfile
from models.pattern import BehaviorPattern
from services.ai_provider import chat

DEFAULT_CONFIDENCE_THRESHOLD = 70
DECISION_HISTORY_LIMIT = 200


def _now_ts() -> int:
    return int(time.time())


def _loads_json(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _dumps_json(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _fallback_summary(
    confirmed_count: int,
    rejected_count: int,
    category_weights: dict[str, int],
    threshold: int,
    preferred_sources: list[str],
) -> str:
    top_categories = [name for name, weight in sorted(category_weights.items(), key=lambda item: item[1], reverse=True)[:3] if weight >= 55]
    category_text = "、".join(top_categories) if top_categories else "尚未形成稳定类别偏好"
    source_text = "、".join(preferred_sources[:3]) if preferred_sources else "来源偏好暂不明显"
    return (
        f"当前 taste model 更倾向确认 {category_text} 类模式。"
        f"经验置信度阈值约为 {threshold}。"
        f"已学习到 {confirmed_count} 次确认、{rejected_count} 次拒绝，偏好来源为 {source_text}。"
    )


def get_or_create_taste_profile(db: Session) -> AgentTasteProfile:
    profile = db.query(AgentTasteProfile).order_by(AgentTasteProfile.id.asc()).first()
    if profile:
        return profile

    now = _now_ts()
    profile = AgentTasteProfile(
        created_at=now,
        updated_at=now,
        preferred_categories=_dumps_json({}),
        preferred_confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
        preferred_sources=_dumps_json([]),
        decision_history=_dumps_json([]),
        taste_summary="尚未学习到稳定偏好，先使用默认阈值和人工规则。",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _profile_has_learned_signal(profile: AgentTasteProfile) -> bool:
    return bool(
        _loads_json(profile.preferred_categories, {})
        or _loads_json(profile.preferred_sources, [])
        or _loads_json(profile.decision_history, [])
    )


def get_active_taste_profile(db: Session) -> AgentTasteProfile:
    profile = get_or_create_taste_profile(db)
    if _profile_has_learned_signal(profile):
        return profile

    confirmed_count = db.query(BehaviorPattern).filter(BehaviorPattern.status == "confirmed").count()
    rejected_count = db.query(BehaviorPattern).filter(BehaviorPattern.status == "rejected").count()
    if confirmed_count or rejected_count:
        return learn_from_history(db)
    return profile


def _build_category_weights(
    confirmed_patterns: list[BehaviorPattern],
    rejected_patterns: list[BehaviorPattern],
) -> dict[str, int]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"confirmed": 0, "rejected": 0})
    for row in confirmed_patterns:
        counts[row.category or "unknown"]["confirmed"] += 1
    for row in rejected_patterns:
        counts[row.category or "unknown"]["rejected"] += 1

    weights = {}
    for category, stat in counts.items():
        confirmed = stat["confirmed"]
        rejected = stat["rejected"]
        # 平滑后计算偏好强度，50 表示中性，大于 50 表示更偏好确认。
        ratio = (confirmed + 1) / (confirmed + rejected + 2)
        weights[category] = int(round(ratio * 100))
    return dict(sorted(weights.items(), key=lambda item: (-item[1], item[0])))


def _aggregate_reject_reasons_from_feedback(rejected_patterns: list[BehaviorPattern]) -> str:
    """从已拒绝模式的 user_feedback 中统计 reject 条目的 reason，生成摘要行（负向信号）。"""
    counts: dict[str, int] = defaultdict(int)
    for row in rejected_patterns:
        items = _loads_json(row.user_feedback, [])
        if not isinstance(items, list):
            continue
        for entry in items:
            if not isinstance(entry, dict):
                continue
            if entry.get("action") != "reject":
                continue
            reason = (entry.get("reason") or "").strip()
            if reason:
                counts[reason] += 1
    if not counts:
        return ""
    top = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:8]
    parts = [f"{name}({n}次)" for name, n in top]
    return "常见拒绝原因: " + "、".join(parts)


def _build_preferred_sources(
    confirmed_patterns: list[BehaviorPattern],
    rejected_patterns: list[BehaviorPattern],
) -> list[str]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"confirmed": 0, "rejected": 0})
    for row in confirmed_patterns:
        counts[row.source or "auto"]["confirmed"] += 1
    for row in rejected_patterns:
        counts[row.source or "auto"]["rejected"] += 1

    preferred = []
    for source, stat in sorted(
        counts.items(),
        key=lambda item: (-item[1]["confirmed"], item[1]["rejected"], item[0]),
    ):
        confirmed = stat["confirmed"]
        rejected = stat["rejected"]
        if confirmed == 0:
            continue
        ratio = (confirmed + 1) / (confirmed + rejected + 2)
        if ratio >= 0.55 or confirmed > rejected:
            preferred.append(source)
    return preferred[:5]


def _build_taste_summary(
    confirmed_patterns: list[BehaviorPattern],
    rejected_patterns: list[BehaviorPattern],
    category_weights: dict[str, int],
    threshold: int,
    preferred_sources: list[str],
    reject_reasons_line: str = "",
) -> str:
    confirmed_count = len(confirmed_patterns)
    rejected_count = len(rejected_patterns)
    categories_text = ", ".join(f"{name}:{weight}" for name, weight in list(category_weights.items())[:6]) or "none"
    sources_text = ", ".join(preferred_sources) or "none"
    reject_hint = f"\n用户填写的拒绝原因统计: {reject_reasons_line}" if reject_reasons_line else ""
    prompt = f"""你在为一个自主 agent 生成「品味模型」摘要。请用中文输出 3 句话以内，描述它倾向确认什么模式、会拒绝什么模式，以及推荐阈值。

确认样本数: {confirmed_count}
拒绝样本数: {rejected_count}
类别权重: {categories_text}
偏好来源: {sources_text}
建议确认阈值: {threshold}{reject_hint}

要求:
1. 语气像系统画像，不要写空话。
2. 明确提到高偏好类别或来源。
3. 若存在拒绝原因统计，简要概括用户不喜欢的模式特征（负向偏好）。
4. 如果数据不足，要直接说明。"""
    result = chat([{"role": "user", "content": prompt}], max_tokens=180)
    base = result.strip() if result else _fallback_summary(
        confirmed_count, rejected_count, category_weights, threshold, preferred_sources
    )
    if reject_reasons_line:
        return f"{base}\n{reject_reasons_line}".strip()
    return base


def learn_from_history(db: Session) -> AgentTasteProfile:
    profile = get_or_create_taste_profile(db)

    confirmed_patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.status == "confirmed",
    ).all()
    rejected_patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.status == "rejected",
    ).all()

    category_weights = _build_category_weights(confirmed_patterns, rejected_patterns)
    confirmed_confidences = [row.confidence for row in confirmed_patterns if row.confidence is not None]
    threshold = int(round(median(confirmed_confidences))) if confirmed_confidences else DEFAULT_CONFIDENCE_THRESHOLD
    preferred_sources = _build_preferred_sources(confirmed_patterns, rejected_patterns)
    reject_reasons_line = _aggregate_reject_reasons_from_feedback(rejected_patterns)

    profile.preferred_categories = _dumps_json(category_weights)
    profile.preferred_confidence_threshold = threshold
    profile.preferred_sources = _dumps_json(preferred_sources)
    profile.taste_summary = _build_taste_summary(
        confirmed_patterns,
        rejected_patterns,
        category_weights,
        threshold,
        preferred_sources,
        reject_reasons_line=reject_reasons_line,
    )
    if not profile.created_at:
        profile.created_at = _now_ts()
    profile.updated_at = _now_ts()

    db.commit()
    db.refresh(profile)
    return profile


def record_pattern_decision(
    db: Session,
    pattern: BehaviorPattern,
    decision: str,
    reason: str,
) -> AgentTasteProfile:
    profile = get_or_create_taste_profile(db)
    history = _loads_json(profile.decision_history, [])
    history.append(
        {
            "pattern_id": pattern.id,
            "pattern_name": pattern.name,
            "decision": decision,
            "reason": reason,
            "category": pattern.category,
            "confidence": pattern.confidence,
            "source": pattern.source,
            "ts": _now_ts(),
        }
    )
    profile.decision_history = _dumps_json(history[-DECISION_HISTORY_LIMIT:])
    profile.updated_at = _now_ts()
    db.commit()
    return learn_from_history(db)


def record_task_preference(
    db: Session,
    task_type: str,
    action: str,
    context: str = "",
) -> AgentTasteProfile:
    """Append a workflow/task event to decision_history (Direction 4 task preferences)."""
    profile = get_or_create_taste_profile(db)
    history = _loads_json(profile.decision_history, [])
    if not isinstance(history, list):
        history = []
    entry = {
        "task_type": task_type,
        "action": action,
        "ts": _now_ts(),
    }
    if context:
        entry["context"] = context
    history.append(entry)
    profile.decision_history = _dumps_json(history[-DECISION_HISTORY_LIMIT:])
    profile.updated_at = _now_ts()
    db.commit()
    db.refresh(profile)
    return profile


def _task_trigger_skip_from_profile(profile: AgentTasteProfile) -> tuple[dict[str, int], dict[str, int]]:
    history = _loads_json(profile.decision_history, [])
    triggered: dict[str, int] = defaultdict(int)
    skipped: dict[str, int] = defaultdict(int)
    if not isinstance(history, list):
        return {}, {}
    for entry in history:
        if not isinstance(entry, dict):
            continue
        tt = entry.get("task_type")
        if tt is None:
            continue
        key = str(tt)
        act = str(entry.get("action") or "").lower()
        if act == "triggered":
            triggered[key] += 1
        elif act == "skipped":
            skipped[key] += 1
    return dict(triggered), dict(skipped)


def get_preferred_task_schedule(db: Session) -> dict[str, float]:
    """Map task_type -> preference score in [0,1] from triggered vs skipped counts in decision_history."""
    profile = get_or_create_taste_profile(db)
    triggered, skipped = _task_trigger_skip_from_profile(profile)
    scores: dict[str, float] = {}
    all_types = set(triggered) | set(skipped)
    for tt in all_types:
        t, s = triggered[tt], skipped[tt]
        total = t + s
        if total > 0:
            scores[tt] = round(t / total, 4)
    return scores


# 与 scheduler 周期一致的可编排原子；仅作「建议」文案与排序，不会自动执行。
_AUTONOMOUS_TASK_SPEC: list[dict] = [
    {
        "id": "mine_patterns",
        "reason": "你经常手动触发模式挖掘，系统建议在确认预览策略后可定期自动排队此步骤",
        "category_hint": "mining",
    },
    {
        "id": "collect",
        "reason": "你经常手动运行采集与分析流水线，系统建议将同等流程纳入可编排的定时任务",
        "category_hint": "collection",
    },
    {
        "id": "taste_auto_confirm",
        "reason": "你多次显式参与品味相关任务，系统建议在护栏内自动预筛高置信模式供你过目",
        "category_hint": "taste",
    },
    {
        "id": "memory_decay",
        "reason": "你关注记忆生命周期，系统建议按固定节奏运行衰减与冷却，减少手动清理",
        "category_hint": "memory",
    },
    {
        "id": "consolidation",
        "reason": "你常驱动合并与剪枝类操作，系统建议周期性自动合并候选模式",
        "category_hint": "consolidation",
    },
    {
        "id": "relation_discovery",
        "reason": "你多次触发关系发现，系统建议低频率后台扫描关联，结果仅作建议列表",
        "category_hint": "relations",
    },
    {
        "id": "claw_evolution",
        "reason": "你频繁使用 Claw 进化相关能力，系统建议在窗口期自动挖掘 CoT / 工作流候选",
        "category_hint": "evolution",
    },
]

# 与 routes 中 create_task(task_type=...) 一致的任务，可用 background_tasks 成功次数补充「手动活跃度」。
_BG_BACKED_TASK_TYPES = frozenset({"mine_patterns", "collect"})


def _completed_background_task_counts(db: Session) -> dict[str, int]:
    rows = db.execute(
        text(
            "SELECT task_type, COUNT(*) FROM background_tasks WHERE status = 'done' GROUP BY task_type"
        ),
    ).fetchall()
    out: dict[str, int] = {}
    for row in rows:
        if row[0] is None:
            continue
        out[str(row[0])] = int(row[1])
    return out


def _frequency_label_from_activity(activity: int) -> str:
    if activity >= 20:
        return "每2小时"
    if activity >= 10:
        return "每6小时"
    if activity >= 5:
        return "每12小时"
    if activity >= 2:
        return "每24小时"
    return "每3天（低频次）"


def _top_category_line(weights: dict[str, int]) -> str:
    if not weights:
        return ""
    top = sorted(weights.items(), key=lambda item: (-item[1], item[0]))[:2]
    parts = [f"{name}" for name, w in top if w >= 55]
    if not parts:
        parts = [top[0][0]] if top else []
    return "、".join(parts)


def _suggestion_confidence(
    schedule_score: float,
    category_weights: dict[str, int],
    spec: dict,
) -> float:
    hint = str(spec.get("category_hint") or "")
    boost = 0.0
    if category_weights and hint:
        # 与模式类品味弱关联：高权重任意类别略抬升「可自动化」信心
        top_w = max(category_weights.values(), default=50)
        boost = min(0.12, max(0, (top_w - 50) / 400))
    raw = 0.42 + 0.48 * schedule_score + boost
    return min(0.95, max(0.35, raw))


def suggest_autonomous_tasks(db: Session) -> list[dict]:
    """
    基于品味画像与任务偏好，列出「若开启自主编排可考虑」的步骤建议。
    仅返回建议文案与参数，不执行任何任务；从未被用户触发过的任务类型不会入选。
    """
    profile = get_active_taste_profile(db)
    category_weights = _loads_json(profile.preferred_categories, {})
    if not isinstance(category_weights, dict):
        category_weights = {}

    hist_triggers, hist_skipped = _task_trigger_skip_from_profile(profile)
    schedule_scores = get_preferred_task_schedule(db)
    bg_done = _completed_background_task_counts(db)

    top_cat_line = _top_category_line(
        {str(k): int(v) for k, v in category_weights.items() if isinstance(v, (int, float))},
    )

    candidates: list[dict] = []
    for spec in _AUTONOMOUS_TASK_SPEC:
        tid = spec["id"]
        h_t = hist_triggers.get(tid, 0)
        h_s = hist_skipped.get(tid, 0)
        bg = bg_done.get(tid, 0) if tid in _BG_BACKED_TASK_TYPES else 0

        user_has_signaled = h_t >= 1 or (bg >= 1 if tid in _BG_BACKED_TASK_TYPES else False)
        if not user_has_signaled:
            continue

        activity = h_t + bg
        pref = schedule_scores.get(tid)
        if pref is None:
            total_hs = h_t + h_s
            pref = (h_t / total_hs) if total_hs > 0 else 1.0

        reason = spec["reason"]
        if top_cat_line and tid in ("mine_patterns", "collect", "taste_auto_confirm"):
            reason = f"{reason}；当前画像更关注类别：{top_cat_line}"

        candidates.append(
            {
                "task": tid,
                "reason": reason,
                "confidence": round(_suggestion_confidence(float(pref), category_weights, spec), 2),
                "frequency": _frequency_label_from_activity(activity),
                "_activity": activity,
                "_pref": float(pref),
            },
        )

    candidates.sort(key=lambda item: (-item["_activity"], -item["_pref"]))
    for item in candidates:
        del item["_activity"]
        del item["_pref"]
    return candidates


def evaluate_pattern_with_taste(profile: AgentTasteProfile, pattern: BehaviorPattern) -> dict:
    preferred_categories = _loads_json(profile.preferred_categories, {})
    preferred_sources = set(_loads_json(profile.preferred_sources, []))
    threshold = profile.preferred_confidence_threshold or DEFAULT_CONFIDENCE_THRESHOLD

    category_weight = int(preferred_categories.get(pattern.category, 50))
    source_bonus = 10 if pattern.source in preferred_sources else (-4 if preferred_sources else 0)
    evidence_bonus = min(15, max(0, pattern.evidence_count or 0) * 3)
    threshold_gap = int(pattern.confidence or 0) - threshold
    threshold_bonus = max(-15, min(15, threshold_gap))

    priority_score = int(round(
        (pattern.confidence or 0) * 0.45
        + category_weight * 0.35
        + evidence_bonus
        + source_bonus
        + threshold_bonus
    ))

    reasons = []
    if category_weight >= 60:
        reasons.append(f"偏好类别 {pattern.category} 权重 {category_weight}")
    elif category_weight <= 40:
        reasons.append(f"类别 {pattern.category} 历史确认率偏低")
    if pattern.source in preferred_sources:
        reasons.append(f"来源 {pattern.source} 符合历史偏好")
    elif preferred_sources:
        reasons.append(f"来源 {pattern.source} 不在高偏好来源中")
    if (pattern.confidence or 0) >= threshold:
        reasons.append(f"当前置信度 {pattern.confidence} 高于阈值 {threshold}")
    else:
        reasons.append(f"当前置信度 {pattern.confidence} 低于阈值 {threshold}")
    if pattern.evidence_count:
        reasons.append(f"证据数 {pattern.evidence_count}")

    if (pattern.confidence or 0) >= threshold and priority_score >= 78:
        action = "confirm"
    elif priority_score >= 58:
        action = "collect_more"
    else:
        action = "defer"

    return {
        "action": action,
        "priority_score": priority_score,
        "reasons": reasons,
    }


def get_pending_pattern_recommendations(db: Session) -> list[dict]:
    profile = get_active_taste_profile(db)
    threshold = profile.preferred_confidence_threshold or DEFAULT_CONFIDENCE_THRESHOLD
    min_confidence = max(35, threshold - 20)

    patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.status == "learning",
        BehaviorPattern.confidence >= min_confidence,
    ).all()

    ranked = []
    for pattern in patterns:
        ranked.append(
            {
                "pattern": pattern,
                **evaluate_pattern_with_taste(profile, pattern),
            }
        )

    ranked.sort(
        key=lambda item: (
            item["priority_score"],
            item["pattern"].confidence or 0,
            item["pattern"].evidence_count or 0,
        ),
        reverse=True,
    )
    return ranked


def auto_confirm_patterns(db: Session) -> dict:
    ranked = get_pending_pattern_recommendations(db)
    confirmed_ids = []
    deferred_ids = []
    more_ids = []
    for item in ranked:
        pattern = item["pattern"]
        action = item["action"]
        if action == "confirm":
            pattern.status = "confirmed"
            record_pattern_decision(db, pattern, "confirmed", "taste-agent auto-confirm")
            confirmed_ids.append(pattern.id)
        elif action == "defer":
            deferred_ids.append(pattern.id)
        else:
            more_ids.append(pattern.id)
    db.commit()
    return {
        "confirmed": len(confirmed_ids),
        "deferred": len(deferred_ids),
        "collect_more": len(more_ids),
        "confirmed_ids": confirmed_ids,
    }


def serialize_taste_profile(profile: AgentTasteProfile) -> dict:
    history = _loads_json(profile.decision_history, [])
    return {
        "id": profile.id,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
        "preferred_categories": _loads_json(profile.preferred_categories, {}),
        "preferred_confidence_threshold": profile.preferred_confidence_threshold or DEFAULT_CONFIDENCE_THRESHOLD,
        "preferred_sources": _loads_json(profile.preferred_sources, []),
        "decision_history": history,
        "decision_history_count": len(history),
        "taste_summary": profile.taste_summary,
    }

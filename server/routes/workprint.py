"""
Workprint Export Route
把 DevTwin 已挖掘的 BehaviorPattern + TeamWorkflow 导出为 SKILL.md 格式。
Workprint 是 DevTwin 的输出层，不是独立工具。
"""
import json
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from db import get_db
from models.pattern import BehaviorPattern
from models.workflow import TeamWorkflow

router = APIRouter(tags=["workprint"])

_CONF_ICON = {
    "very_high": "●",
    "high": "●",
    "medium": "◑",
    "low": "○",
}

_LIFECYCLE_NOTE = {
    "active": "",
    "warm": " _(warming)_",
    "cool": " _(cooling)_",
    "compressed": " _(compressed — low recency)_",
    "archived": " _(archived)_",
}


# ---------------------------------------------------------------------------
# GET /api/workprint/export  →  SKILL.md 文本
# ---------------------------------------------------------------------------

@router.get("/workprint/export", response_class=PlainTextResponse)
def export_workprint(
    profile_id: int | None = Query(None),
    name: str = Query("me"),
    display_name: str = Query(""),
    min_confidence: int = Query(30, ge=0, le=100),
    min_evidence: int = Query(1, ge=0),
    lifecycle: str = Query("active,warm"),   # 逗号分隔的状态白名单
    include_body: bool = Query(True),
    db: Session = Depends(get_db),
):
    allowed_lifecycle = set(lifecycle.split(","))
    display = display_name or name

    # 查询 patterns
    q = db.query(BehaviorPattern).filter(
        BehaviorPattern.status != "rejected",
        BehaviorPattern.confidence >= min_confidence,
    )
    if profile_id:
        q = q.filter(BehaviorPattern.profile_id == profile_id)
    all_patterns = q.order_by(BehaviorPattern.heat_score.desc()).all()

    # 过滤生命周期
    patterns = [
        p for p in all_patterns
        if (p.lifecycle_state or "active") in allowed_lifecycle
        and (p.evidence_count or 0) >= min_evidence
    ]

    # 查询 workflows
    wq = db.query(TeamWorkflow)
    if profile_id:
        wq = wq.filter(TeamWorkflow.profile_id == profile_id)
    workflows = wq.order_by(TeamWorkflow.created_at.desc()).limit(10).all()

    # 日期范围
    timestamps = [p.created_at for p in all_patterns if p.created_at]
    if timestamps:
        first = datetime.fromtimestamp(min(timestamps), tz=timezone.utc).strftime("%Y-%m-%d")
        last = datetime.fromtimestamp(max(timestamps), tz=timezone.utc).strftime("%Y-%m-%d")
        date_range = f"{first} — {last}"
    else:
        date_range = "unknown"

    md = _render_skill_md(
        name=name,
        display=display,
        patterns=patterns,
        workflows=workflows,
        total_all=len(all_patterns),
        date_range=date_range,
        include_body=include_body,
    )
    return md


# ---------------------------------------------------------------------------
# GET /api/workprint/preview  →  JSON 摘要（供前端展示用）
# ---------------------------------------------------------------------------

@router.get("/workprint/preview")
def preview_workprint(
    profile_id: int | None = Query(None),
    min_confidence: int = Query(30),
    lifecycle: str = Query("active,warm"),
    db: Session = Depends(get_db),
):
    allowed_lifecycle = set(lifecycle.split(","))

    q = db.query(BehaviorPattern).filter(
        BehaviorPattern.status != "rejected",
        BehaviorPattern.confidence >= min_confidence,
    )
    if profile_id:
        q = q.filter(BehaviorPattern.profile_id == profile_id)
    patterns = q.order_by(BehaviorPattern.heat_score.desc()).all()
    patterns = [p for p in patterns if (p.lifecycle_state or "active") in allowed_lifecycle]

    by_category: dict[str, int] = {}
    by_confidence: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    by_lifecycle: dict[str, int] = {}
    top_heat = []

    for p in patterns:
        cat = p.category or "other"
        by_category[cat] = by_category.get(cat, 0) + 1

        cl = p.confidence_level or "low"
        if cl in ("very_high", "high"):
            by_confidence["high"] += 1
        elif cl == "medium":
            by_confidence["medium"] += 1
        else:
            by_confidence["low"] += 1

        ls = p.lifecycle_state or "active"
        by_lifecycle[ls] = by_lifecycle.get(ls, 0) + 1

        top_heat.append({
            "id": p.id,
            "name": p.name,
            "heat_score": round(p.heat_score or 0, 1),
            "confidence": p.confidence,
            "confidence_level": p.confidence_level,
            "lifecycle_state": p.lifecycle_state,
            "evidence_count": p.evidence_count or 0,
        })

    top_heat.sort(key=lambda x: -x["heat_score"])

    return {
        "total_patterns": len(patterns),
        "by_category": by_category,
        "by_confidence": by_confidence,
        "by_lifecycle": by_lifecycle,
        "top_patterns": top_heat[:10],
        "export_url": "/api/workprint/export",
    }


# ---------------------------------------------------------------------------
# 渲染逻辑
# ---------------------------------------------------------------------------

def _render_skill_md(
    name: str,
    display: str,
    patterns: list[BehaviorPattern],
    workflows: list[TeamWorkflow],
    total_all: int,
    date_range: str,
    include_body: bool,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d")
    sections = [
        _frontmatter(name, display, len(patterns), total_all, date_range, now),
        _header(name, display, len(patterns), date_range),
        _usage(name, display),
        _stats_section(patterns),
        _patterns_section(patterns, include_body),
        _workflows_section(workflows),
        _honest_limits(),
        _footer(),
    ]
    return "\n\n".join(s for s in sections if s and s.strip())


def _frontmatter(name, display, n, total, date_range, now):
    return f"""---
name: workprint/{name}
description: Behavioral skill distilled from {n} active patterns ({total} total mined)
version: 0.1.0
distilled_at: {now}
active_patterns: {n}
total_mined: {total}
date_range: {date_range}
source: DevTwin
---"""


def _header(name, display, n, date_range):
    return f"""# Workprint: {display}

> **{n}** active behavioral patterns distilled from real traces ({date_range})

Generated by [DevTwin](https://github.com/asimfish/devtwin) — every pattern below is backed by empirical behavioral evidence with Bayesian confidence scoring, not inferred from self-reports."""


def _usage(name, display):
    return f"""## Usage

```
/workprint {name} review this PR for me
/workprint {name} how would you approach this architecture decision?
/workprint {name} write a commit message for these changes
```

When activated, Claude responds from the perspective of **{display}'s actual working patterns** — grounded in observed behavior, not role-play assumptions."""


def _stats_section(patterns: list[BehaviorPattern]) -> str:
    if not patterns:
        return ""

    by_cat: dict[str, int] = {}
    for p in patterns:
        cat = p.category or "other"
        by_cat[cat] = by_cat.get(cat, 0) + 1

    avg_conf = int(sum(p.confidence or 0 for p in patterns) / len(patterns))
    avg_heat = round(sum(p.heat_score or 0 for p in patterns) / len(patterns), 1)
    total_evidence = sum(p.evidence_count or 0 for p in patterns)

    cat_parts = ", ".join(f"`{k}` ({v})" for k, v in sorted(by_cat.items(), key=lambda x: -x[1])[:5])

    return f"""## Behavioral DNA

| Metric | Value |
|--------|-------|
| Active patterns | {len(patterns)} |
| Total evidence collected | {total_evidence} |
| Average confidence | {avg_conf}% |
| Average heat score | {avg_heat}/100 |
| Top categories | {cat_parts} |"""


def _patterns_section(patterns: list[BehaviorPattern], include_body: bool) -> str:
    if not patterns:
        return "## Core Behavioral Patterns\n\n_No patterns found matching the filter criteria._"

    lines = [
        "## Core Behavioral Patterns\n",
        "_Legend: ● High confidence | ◑ Medium | ○ Low | Heat = recency × access frequency_\n",
    ]

    for p in patterns[:30]:   # 最多展示 30 条
        lines.append(_render_pattern(p, include_body))

    return "\n".join(lines)


def _render_pattern(p: BehaviorPattern, include_body: bool) -> str:
    cl = p.confidence_level or "low"
    icon = _CONF_ICON.get(cl, "○")
    lifecycle_note = _LIFECYCLE_NOTE.get(p.lifecycle_state or "active", "")

    # 触发条件
    trigger_str = ""
    if p.trigger:
        try:
            t = json.loads(p.trigger) if p.trigger.startswith("{") else p.trigger
            trigger_str = t.get("when", t) if isinstance(t, dict) else str(t)
        except Exception:
            trigger_str = str(p.trigger)

    # 证据摘要（从 learned_from_data）
    evidence_items = []
    if p.learned_from_data:
        try:
            data = json.loads(p.learned_from_data)
            for item in data[:3]:
                if isinstance(item, dict):
                    ctx = item.get("context", "") or item.get("insight", "")
                    if ctx:
                        evidence_items.append(f"- {str(ctx)[:120]}")
        except Exception:
            pass

    lines = [
        f"### {icon} {p.name}{lifecycle_note}",
        f"**Category**: `{p.category}` | "
        f"**Confidence**: {p.confidence}% ({cl}) | "
        f"**Evidence**: {p.evidence_count or 0} | "
        f"**Heat**: {round(p.heat_score or 0, 1)}",
        "",
        p.description or "",
    ]

    if trigger_str:
        lines += ["", f"**Triggers when**: {trigger_str}"]

    if include_body and p.body:
        lines += ["", "**Behavioral rule**:", "", p.body[:500]]

    if evidence_items:
        lines += ["", "**Evidence traces**:"] + evidence_items

    lines.append("\n---")
    return "\n".join(lines)


def _workflows_section(workflows: list[TeamWorkflow]) -> str:
    if not workflows:
        return ""

    lines = ["## Workflow Patterns\n"]
    for w in workflows:
        steps = []
        if w.steps:
            try:
                steps = json.loads(w.steps)
            except Exception:
                pass

        steps_str = " → ".join(f"`{s}`" for s in steps[:6]) if steps else "_see description_"
        lines += [
            f"### {w.name}",
            f"**Sequence**: {steps_str}",
            "",
            w.description or "",
            "",
            "---",
        ]
    return "\n".join(lines)


def _honest_limits() -> str:
    return """## Honest Limits

_What this workprint cannot replicate:_

- Patterns reflect **observed behavior in the analysis window**, not complete working style
- Confidence scores are Bayesian estimates — high-confidence patterns have more evidence, but evidence is never exhaustive
- Private reasoning and in-the-moment intuition are not captured — only actions that left a trace are included
- Behavioral patterns evolve; patterns marked _(cooling)_ or _(compressed)_ may no longer reflect current habits"""


def _footer() -> str:
    return (
        "---\n\n"
        "_Generated by [DevTwin](https://github.com/asimfish/devtwin) Workprint export — "
        "Distill real behavior traces into executable AI skills._"
    )

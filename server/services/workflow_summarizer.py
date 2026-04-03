import json
import logging
import time

from sqlalchemy.orm import Session

from models.invocation import OpenClawInvocationLog
from models.openclaw import OpenClawSession
from models.skill_workflow import SkillWorkflow
from services.ai_provider import chat

logger = logging.getLogger(__name__)


def _load_json(raw):
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


def _gather_workflow_context(db: Session, skill_sequence: list[str], limit: int = 5) -> list[dict]:
    """Find invocation logs whose selected_pattern_slugs contain the skill sequence."""
    if not skill_sequence:
        return []

    logs = (
        db.query(OpenClawInvocationLog)
        .order_by(OpenClawInvocationLog.created_at.desc())
        .limit(200)
        .all()
    )

    matched = []
    seq_set = set(skill_sequence)
    for log in logs:
        slugs = _load_json(log.selected_pattern_slugs)
        if seq_set.issubset(set(slugs)):
            session_summary = None
            if log.session_id:
                session = db.query(OpenClawSession).filter(OpenClawSession.id == log.session_id).first()
                if session:
                    session_summary = getattr(session, "analysis_summary", None) or getattr(session, "title", None)
            matched.append({
                "log_id": log.id,
                "session_id": log.session_id,
                "provider": log.provider,
                "model": log.model,
                "status": log.status,
                "trigger_source": getattr(log, "trigger_source", None),
                "outcome": getattr(log, "outcome", None),
                "session_summary": session_summary,
                "created_at": log.created_at,
            })
            if len(matched) >= limit:
                break
    return matched


def _build_summarize_prompt(workflow_name: str, skill_sequence: list[str], frequency: int,
                            success_rate: float, context: list[dict]) -> str:
    context_block = ""
    if context:
        examples = []
        for ctx in context[:3]:
            summary = ctx.get("session_summary") or "（无摘要）"
            trigger = ctx.get("trigger_source") or "unknown"
            outcome = ctx.get("outcome") or ctx.get("status") or "unknown"
            examples.append(f"- 触发方式: {trigger}, 结果: {outcome}, 会话摘要: {summary}")
        context_block = "\n".join(examples)

    return f"""你是一个 AI 工作流分析专家。根据以下 skill 调用序列和上下文，生成一份结构化的 workflow 描述。

## 输入数据
- 序列名称: {workflow_name}
- Skill 序列: {' → '.join(skill_sequence)}
- 出现频次: {frequency}
- 成功率: {success_rate:.1%}

## 上下文示例
{context_block or '暂无上下文数据'}

## 输出要求
请严格返回以下 JSON，不要添加任何 markdown 标记：
{{
  "description": "一句话描述这个 workflow 的用途（中文，20字以内）",
  "trigger": "何时触发此 workflow（中文，30字以内）",
  "steps": [
    {{"action": "步骤描述", "tool": "相关工具/skill名", "checkpoint": "验证点"}},
    ...
  ],
  "context_tags": ["标签1", "标签2", "标签3"]
}}"""


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def summarize_single_workflow(db: Session, workflow: SkillWorkflow) -> dict | None:
    """AI-summarize a single SkillWorkflow and persist the result."""
    sequence = _load_json(workflow.skill_sequence)
    if not sequence:
        return None

    context = _gather_workflow_context(db, sequence)
    prompt = _build_summarize_prompt(
        workflow.name, sequence, workflow.frequency or 0,
        workflow.success_rate or 0.0, context,
    )

    response = chat([{"role": "user", "content": prompt}], max_tokens=1500)
    if not response:
        logger.warning("AI returned empty response for workflow %s", workflow.id)
        return None

    try:
        parsed = json.loads(_strip_json_fence(response))
    except json.JSONDecodeError:
        logger.warning("Failed to parse AI response for workflow %s: %s", workflow.id, response[:200])
        return None

    now = int(time.time())
    workflow.description = parsed.get("description", workflow.description)
    workflow.trigger = parsed.get("trigger", workflow.trigger)
    steps = parsed.get("steps")
    if isinstance(steps, list):
        workflow.steps = json.dumps(steps, ensure_ascii=False)
    tags = parsed.get("context_tags")
    if isinstance(tags, list):
        workflow.context_tags = json.dumps(tags, ensure_ascii=False)
    workflow.source = "ai_summarized"
    workflow.updated_at = now
    db.add(workflow)
    db.commit()

    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description,
        "trigger": workflow.trigger,
        "steps": _load_json(workflow.steps),
        "context_tags": _load_json(workflow.context_tags),
        "source": workflow.source,
    }


def summarize_all_draft_workflows(db: Session) -> list[dict]:
    """AI-summarize all draft/mined workflows that haven't been summarized yet."""
    rows = (
        db.query(SkillWorkflow)
        .filter(SkillWorkflow.status.in_(["draft", None]))
        .filter(SkillWorkflow.source.in_(["mined", None]))
        .order_by(SkillWorkflow.frequency.desc())
        .limit(20)
        .all()
    )

    results = []
    for wf in rows:
        result = summarize_single_workflow(db, wf)
        if result:
            results.append(result)
    return results

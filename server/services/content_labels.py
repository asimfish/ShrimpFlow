import os
import re
from pathlib import Path

ORIGIN_LABELS = {
    "openclaw": "OpenClaw",
    "claude_code": "Claude Code",
    "codex": "Codex",
    "cursor": "Cursor",
    "vscode": "VS Code",
    "unknown": "未知来源",
}

GENERIC_PROJECT_NAMES = {
    "",
    "liyufeng",
    "planner",
    "workspace",
    "unknown",
    "codex",
}

NOISE_PREFIXES = (
    "# agents.md",
    "<environment_context>",
    "<permissions instructions>",
    "you are codex",
    "## memory",
    "## formatting rules",
    "## final answer instructions",
)

TITLE_RULES = [
    ("AI 语义聚合与会话管理改造", ("语义聚合", "供应商", "模型", "知识库", "会话分类", "页面", "卡顿", "刷新")),
    ("代码审查与实现完善", ("review", "审查", "检查", "代码审查")),
    ("报错定位与修复", ("bug", "fix", "error", "debug", "报错", "调试")),
    ("架构与方案设计", ("design", "architecture", "架构", "方案", "设计")),
    ("论文与实验分析", ("paper", "论文", "experiment", "实验", "benchmark", "ablation")),
    ("构建与部署排查", ("build", "deploy", "部署", "启动", "端口", "发布")),
    ("测试补全与验证", ("test", "pytest", "测试", "验证")),
]

CATEGORY_TITLES = {
    "paper": "论文与实验分析",
    "debug": "报错定位与修复",
    "review": "代码审查与实现完善",
    "experiment": "实验设计与结果整理",
    "architecture": "架构与方案设计",
    "learning": "问题探索与方案推进",
}

DOC_TYPE_TITLES = {
    "daily_task": "任务清单",
    "paper_note": "论文笔记",
    "experiment_log": "实验日志",
    "meeting_note": "会议纪要",
    "daily_summary": "日报总结",
    "ai_tools_daily": "AI 工具日报",
    "ai_tools_weekly": "AI 工具周报",
    "ai_tools_index": "AI 工具索引",
    "github_daily": "GitHub 日报",
    "media_daily": "媒体日报",
    "misc": "工作笔记",
}


def detect_origin(tags: list[str], fallback: str | None = None) -> str:
    tag_set = {tag.lower() for tag in tags}
    if "claude_code" in tag_set or "claude-code" in tag_set:
        return "claude_code"
    if "codex" in tag_set:
        return "codex"
    if "cursor" in tag_set:
        return "cursor"
    if "vscode" in tag_set or "code" in tag_set:
        return "vscode"
    if "openclaw" in tag_set or "clawd" in tag_set:
        return "openclaw"
    return fallback or "unknown"


def origin_label(origin: str) -> str:
    return ORIGIN_LABELS.get(origin, ORIGIN_LABELS["unknown"])


def build_index_label(prefix: str, item_id: int) -> str:
    return f"{prefix}-{item_id:04d}"


def _compact_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"`{1,3}", " ", text)
    text = re.sub(r"#+\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_noise_candidate(text: str) -> bool:
    cleaned = _compact_text(text).lower()
    if len(cleaned) < 8:
        return True
    return any(cleaned.startswith(prefix) for prefix in NOISE_PREFIXES)


def _trim_title(text: str, limit: int = 28) -> str:
    compact = _compact_text(text)
    compact = re.sub(r"^(请你|帮我|麻烦你|继续|再|请|我想|我需要)\s*", "", compact)
    compact = re.sub(r"^(please|help me|can you|could you)\s*", "", compact, flags=re.IGNORECASE)
    compact = compact.split("。")[0].split("！")[0].split("？")[0].split(". ")[0].split(": ")[0]
    compact = compact.strip(" -_:,.;")
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "..."


def _extract_project_from_paths(text: str) -> str | None:
    for raw_path in re.findall(r"/Users/[^\s<>\"]+", text):
        cleaned = raw_path.rstrip(").,")
        parts = Path(cleaned).parts
        if not parts:
            continue
        if ".claude" in parts and "workspaces" in parts:
            try:
                workspace_name = parts[parts.index("workspaces") + 1]
                return re.sub(r"-[0-9a-f]{8,}$", "", workspace_name)
            except (ValueError, IndexError):
                continue
        basename = os.path.basename(cleaned.rstrip("/"))
        if basename and basename.lower() not in {"users", "liyufeng"}:
            return basename
    return None


def derive_project_label(project: str, messages: list[dict] | None = None, cwd: str | None = None) -> str:
    if project and project not in GENERIC_PROJECT_NAMES and not re.fullmatch(r"worker-\d+", project):
        return project

    if cwd:
        parts = Path(cwd).parts
        if ".claude" in parts and "workspaces" in parts:
            try:
                workspace_name = parts[parts.index("workspaces") + 1]
                return re.sub(r"-[0-9a-f]{8,}$", "", workspace_name)
            except (ValueError, IndexError):
                pass
        basename = os.path.basename(cwd.rstrip("/"))
        if basename and basename not in GENERIC_PROJECT_NAMES and not re.fullmatch(r"worker-\d+", basename):
            return basename

    for message in messages or []:
        content = str(message.get("content", ""))
        candidate = _extract_project_from_paths(content)
        if candidate:
            return candidate

    return project or "workspace"


def summarize_session_title(messages: list[dict], fallback_title: str, category: str) -> str:
    candidates = []
    for message in messages:
        if message.get("role") == "user":
            candidates.append(str(message.get("content", "")))
    candidates.append(fallback_title)

    for candidate in candidates:
        if not candidate or _is_noise_candidate(candidate):
            continue
        compact = _compact_text(candidate)
        lowered = compact.lower()
        for title, keywords in TITLE_RULES:
            if any(keyword.lower() in lowered for keyword in keywords):
                return title
        trimmed = _trim_title(compact)
        if trimmed:
            return trimmed

    return CATEGORY_TITLES.get(category, "未命名会话")


def summarize_session_summary(messages: list[dict], fallback_summary: str, project: str, origin: str, category: str) -> str:
    meaningful = next(
        (
            _compact_text(str(message.get("content", "")))
            for message in messages
            if message.get("role") == "user" and not _is_noise_candidate(str(message.get("content", "")))
        ),
        "",
    )
    if meaningful:
        summary = meaningful
    else:
        summary = _compact_text(fallback_summary)

    if len(summary) > 88:
        summary = summary[:88].rstrip() + "..."

    if not summary:
        summary = f"{origin_label(origin)} · {CATEGORY_TITLES.get(category, '会话')}"

    if project:
        return f"{project} · {summary}"
    return summary


def summarize_document_title(title: str, doc_type: str, content: str = "") -> str:
    stem = Path(title).stem
    if doc_type == "daily_summary":
        match = re.search(r"(\d{4}-\d{2}-\d{2})", title)
        return f"日报总结 · {match.group(1)}" if match else DOC_TYPE_TITLES[doc_type]
    if doc_type == "ai_tools_daily":
        match = re.search(r"(\d{4}-\d{2}-\d{2})", title)
        return f"AI 工具日报 · {match.group(1)}" if match else DOC_TYPE_TITLES[doc_type]
    if doc_type == "ai_tools_weekly":
        match = re.search(r"(\d{4}-W\d{2})", title)
        return f"AI 工具周报 · {match.group(1)}" if match else DOC_TYPE_TITLES[doc_type]
    if doc_type == "github_daily":
        match = re.search(r"(\d{4}-\d{2}-\d{2})", title)
        return f"GitHub 日报 · {match.group(1)}" if match else DOC_TYPE_TITLES[doc_type]
    if doc_type == "media_daily":
        match = re.search(r"(\d{4}-\d{2}-\d{2})", title)
        return f"媒体日报 · {match.group(1)}" if match else DOC_TYPE_TITLES[doc_type]

    if stem and re.fullmatch(r"\d{4}-\d{2}-\d{2}", stem):
        return f"{DOC_TYPE_TITLES.get(doc_type, '文档')} · {stem}"

    compact = _compact_text(stem or title)
    compact = compact or _compact_text(content[:48])
    compact = _trim_title(compact, limit=32)
    return compact or DOC_TYPE_TITLES.get(doc_type, "文档")


def summarize_document_preview(content: str, fallback: str = "") -> str:
    preview = _compact_text(content or fallback)
    if len(preview) > 90:
        return preview[:90].rstrip() + "..."
    return preview


def infer_session_category(messages: list[dict], fallback: str = "learning") -> str:
    text = " ".join(str(message.get("content", "")).lower() for message in messages[:8])
    if any(token in text for token in ("bug", "fix", "error", "debug", "报错", "修复")):
        return "debug"
    if any(token in text for token in ("review", "审查", "检查", "评审")):
        return "review"
    if any(token in text for token in ("设计", "design", "架构", "architecture", "方案")):
        return "architecture"
    if any(token in text for token in ("论文", "paper", "related work", "benchmark", "ablation", "实验")):
        return "paper"
    return fallback

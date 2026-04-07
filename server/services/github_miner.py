"""
GitHub Miner — 从 GitHub 仓库的 commit 历史中提取特定作者的行为模式。

不克隆仓库，直接用 GitHub REST API，无需 auth（rate limit: 60 req/h）。
每个 "大牛" 对应一个 GitMentor，提取其真实 commit 行为作为可学习的模式。
"""
from __future__ import annotations

import re
import time
import urllib.request
import urllib.error
import json
from collections import Counter
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# 内置大牛名录
# ---------------------------------------------------------------------------

MENTOR_CATALOG: dict[str, dict] = {
    "torvalds": {
        "name": "Linus Torvalds",
        "repo": "torvalds/linux",
        "github_login": "torvalds",
        "tagline": "Linux 内核创始人 — 极度简洁、直接、不妥协的工程哲学",
        "focus": ["kernel", "C", "os"],
    },
    "antirez": {
        "name": "Salvatore Sanfilippo (antirez)",
        "repo": "redis/redis",
        "github_login": "antirez",
        "tagline": "Redis 作者 — 追求极致简洁、拒绝过度工程",
        "focus": ["redis", "C", "database"],
    },
    "gvanrossum": {
        "name": "Guido van Rossum",
        "repo": "python/cpython",
        "github_login": "gvanrossum",
        "tagline": "Python 之父 — 可读性优先，明确优于隐晦",
        "focus": ["python", "language-design"],
    },
    "dhh": {
        "name": "David Heinemeier Hansson (DHH)",
        "repo": "rails/rails",
        "github_login": "dhh",
        "tagline": "Ruby on Rails 作者 — 约定优于配置，开发者幸福感优先",
        "focus": ["rails", "ruby", "web"],
    },
    "yyx990803": {
        "name": "Evan You",
        "repo": "vuejs/core",
        "github_login": "yyx990803",
        "tagline": "Vue.js 作者 — 渐进式设计，开发体验与性能并重",
        "focus": ["vue", "javascript", "frontend"],
    },
    "tj": {
        "name": "TJ Holowaychuk",
        "repo": "expressjs/express",
        "github_login": "tj",
        "tagline": "Express/Koa 作者 — 极简主义，小而美",
        "focus": ["node", "javascript", "minimalism"],
    },
    "sindresorhus": {
        "name": "Sindre Sorhus",
        "repo": "sindresorhus/got",
        "github_login": "sindresorhus",
        "tagline": "npm 之王 — 单一职责，模块化极致，TypeScript-first",
        "focus": ["npm", "typescript", "open-source"],
    },
    "jaredpalmer": {
        "name": "Jared Palmer",
        "repo": "jaredpalmer/formik",
        "github_login": "jaredpalmer",
        "tagline": "Formik/Turborepo 作者 — DX 优先，工具链思维",
        "focus": ["react", "typescript", "dx"],
    },
    "mitchellh": {
        "name": "Mitchell Hashimoto",
        "repo": "hashicorp/vagrant",
        "github_login": "mitchellh",
        "tagline": "HashiCorp 创始人 — 基础设施即代码，长期主义",
        "focus": ["go", "infrastructure", "devops"],
    },
    "dan_abramov": {
        "name": "Dan Abramov",
        "repo": "facebook/react",
        "github_login": "gaearon",
        "tagline": "Redux/React Hooks 作者 — 教育优先，每个 commit 都是教程",
        "focus": ["react", "javascript", "open-source"],
    },
}


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class CommitRecord:
    sha: str
    message: str
    author_login: str
    author_name: str
    date: str
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0
    body: str = ""


@dataclass
class MentorPattern:
    name: str
    description: str
    evidence: list[str] = field(default_factory=list)
    confidence: str = "medium"   # low | medium | high
    category: str = "style"      # style | workflow | decision | tool


@dataclass
class MentorInsight:
    mentor_key: str
    mentor_name: str
    mentor_tagline: str
    repo: str
    commits_analyzed: int
    patterns: list[MentorPattern] = field(default_factory=list)
    error: str = ""


# ---------------------------------------------------------------------------
# GitHub API 封装
# ---------------------------------------------------------------------------

def _gh_get(url: str, token: str | None = None) -> dict | list | None:
    """GET GitHub API，失败返回 None。"""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "DevTwin-Workprint/1.0",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise RateLimitError("GitHub API rate limit exceeded")
        return None
    except Exception:
        return None


class RateLimitError(Exception):
    pass


# ---------------------------------------------------------------------------
# 核心挖掘逻辑
# ---------------------------------------------------------------------------

def mine_mentor(
    mentor_key: str,
    max_commits: int = 100,
    github_token: str | None = None,
) -> MentorInsight:
    """分析一位大牛的 commit 行为，返回 MentorInsight。"""
    if mentor_key not in MENTOR_CATALOG:
        return MentorInsight(
            mentor_key=mentor_key,
            mentor_name=mentor_key,
            mentor_tagline="",
            repo="",
            commits_analyzed=0,
            error=f"Unknown mentor: {mentor_key}",
        )

    meta = MENTOR_CATALOG[mentor_key]
    repo = meta["repo"]
    login = meta["github_login"]

    try:
        commits = _fetch_commits(repo, login, max_commits, github_token)
    except RateLimitError:
        return MentorInsight(
            mentor_key=mentor_key,
            mentor_name=meta["name"],
            mentor_tagline=meta["tagline"],
            repo=repo,
            commits_analyzed=0,
            error="GitHub API rate limit reached. Provide a token or try later.",
        )

    if not commits:
        return MentorInsight(
            mentor_key=mentor_key,
            mentor_name=meta["name"],
            mentor_tagline=meta["tagline"],
            repo=repo,
            commits_analyzed=0,
            error=f"No commits found for @{login} in {repo}",
        )

    patterns = _extract_patterns(commits, meta)
    return MentorInsight(
        mentor_key=mentor_key,
        mentor_name=meta["name"],
        mentor_tagline=meta["tagline"],
        repo=repo,
        commits_analyzed=len(commits),
        patterns=patterns,
    )


def _fetch_commits(
    repo: str,
    login: str,
    max_commits: int,
    token: str | None,
) -> list[CommitRecord]:
    """从 GitHub API 拉取指定作者的最近 commits。"""
    records: list[CommitRecord] = []
    page = 1
    per_page = min(max_commits, 100)

    while len(records) < max_commits:
        url = (
            f"https://api.github.com/repos/{repo}/commits"
            f"?author={login}&per_page={per_page}&page={page}"
        )
        data = _gh_get(url, token)
        if not data or not isinstance(data, list):
            break

        for item in data:
            commit = item.get("commit", {})
            author_info = item.get("author") or {}
            sha = item.get("sha", "")[:8]
            msg_full = commit.get("message", "")
            lines = msg_full.split("\n", 1)
            subject = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ""

            records.append(CommitRecord(
                sha=sha,
                message=subject,
                author_login=author_info.get("login", login),
                author_name=commit.get("author", {}).get("name", ""),
                date=commit.get("author", {}).get("date", "")[:10],
                body=body,
            ))

        if len(data) < per_page:
            break
        page += 1
        time.sleep(0.5)   # 避免触发 rate limit

    return records[:max_commits]


# ---------------------------------------------------------------------------
# 模式提取
# ---------------------------------------------------------------------------

def _extract_patterns(commits: list[CommitRecord], meta: dict) -> list[MentorPattern]:
    patterns: list[MentorPattern] = []
    patterns.extend(_commit_message_style(commits))
    patterns.extend(_commit_size_discipline(commits))
    patterns.extend(_commit_type_distribution(commits))
    patterns.extend(_body_usage(commits))
    patterns.extend(_fix_ratio(commits))
    return patterns


def _commit_message_style(commits: list[CommitRecord]) -> list[MentorPattern]:
    msgs = [c.message for c in commits if c.message]
    if not msgs:
        return []

    avg_len = sum(len(m) for m in msgs) / len(msgs)
    lengths = [len(m) for m in msgs]
    under_50 = sum(1 for l in lengths if l <= 50)
    under_72 = sum(1 for l in lengths if l <= 72)

    # 大写开头比例
    upper_ratio = sum(1 for m in msgs if m[0].isupper()) / len(msgs)
    # 以动词开头（祈使句）比例
    imperative_verbs = {"Add", "Fix", "Update", "Remove", "Refactor", "Improve",
                        "Change", "Implement", "Move", "Rename", "Clean", "Use",
                        "Make", "Allow", "Support", "Avoid", "Handle", "Enable",
                        "Disable", "Merge", "Revert", "Bump"}
    imperative_ratio = sum(
        1 for m in msgs if m.split()[0].rstrip(":") in imperative_verbs
    ) / len(msgs)

    evidence = [f"`{m[:70]}`" for m in msgs[:4]]
    confidence = "high" if len(msgs) >= 30 else "medium"

    patterns = []

    if avg_len < 50:
        patterns.append(MentorPattern(
            name="超短 commit message（≤50 字符）",
            description=(
                f"平均 commit 消息长度 {avg_len:.0f} 字符。"
                f"偏好极度简洁的单行描述，直击要害，无废话。"
                f"{int(under_50/len(msgs)*100)}% 的 commit 在 50 字符内。"
            ),
            evidence=evidence,
            confidence=confidence,
            category="style",
        ))
    elif avg_len < 72:
        patterns.append(MentorPattern(
            name="标准长度 commit message（≤72 字符）",
            description=(
                f"平均 {avg_len:.0f} 字符，遵循 Git 社区约定的 72 字符单行限制。"
                f"{int(under_72/len(msgs)*100)}% 符合规范。"
            ),
            evidence=evidence,
            confidence=confidence,
            category="style",
        ))
    else:
        patterns.append(MentorPattern(
            name="详细 commit message（>72 字符）",
            description=(
                f"平均 {avg_len:.0f} 字符，偏好在标题行详细描述变更内容。"
                "commit 本身就是文档。"
            ),
            evidence=evidence,
            confidence=confidence,
            category="style",
        ))

    if imperative_ratio > 0.6:
        patterns.append(MentorPattern(
            name="祈使句动词开头",
            description=(
                f"{int(imperative_ratio*100)}% 的 commit 以祈使动词开头"
                f"（Add/Fix/Remove/Refactor 等）。"
                "符合 Git 官方推荐的提交信息规范。"
            ),
            evidence=[f"`{m[:60]}`" for m in msgs if m.split()[0].rstrip(":") in imperative_verbs][:4],
            confidence=confidence,
            category="style",
        ))

    return patterns


def _commit_size_discipline(commits: list[CommitRecord]) -> list[MentorPattern]:
    # 从 message 特征推断（API 不包含 diff stats，需要额外请求）
    # 用消息长度 + 关键词作为代理指标
    multi_file_keywords = ["across", "all", "multiple", "various", "many", "several"]
    single_file_msgs = [
        c for c in commits
        if not any(kw in c.message.lower() for kw in multi_file_keywords)
        and len(c.message) < 60
    ]
    ratio = len(single_file_msgs) / len(commits) if commits else 0

    if ratio > 0.7:
        return [MentorPattern(
            name="原子化 commit 习惯",
            description=(
                f"约 {int(ratio*100)}% 的 commit 描述单一、聚焦的变更。"
                "每个 commit 只做一件事，便于 review 和 bisect。"
            ),
            evidence=[f"`{c.message[:60]}`" for c in single_file_msgs[:4]],
            confidence="medium",
            category="workflow",
        )]
    return []


def _commit_type_distribution(commits: list[CommitRecord]) -> list[MentorPattern]:
    msgs = [c.message.lower() for c in commits]
    type_counter: Counter = Counter()

    keyword_map = {
        "fix": ["fix", "bug", "correct", "repair", "resolve"],
        "feat": ["add", "implement", "introduce", "new", "support", "enable"],
        "refactor": ["refactor", "cleanup", "clean up", "reorganize", "restructure"],
        "docs": ["doc", "comment", "readme", "changelog"],
        "test": ["test", "spec", "coverage"],
        "chore": ["bump", "update", "upgrade", "dependency", "version"],
        "perf": ["perf", "performance", "optim", "speed", "faster"],
    }

    for msg in msgs:
        for tp, keywords in keyword_map.items():
            if any(kw in msg for kw in keywords):
                type_counter[tp] += 1
                break

    if not type_counter:
        return []

    total = sum(type_counter.values())
    top_type, top_count = type_counter.most_common(1)[0]
    pct = int(top_count / total * 100)

    label_map = {
        "fix": "bug 修复",
        "feat": "功能开发",
        "refactor": "重构整理",
        "docs": "文档写作",
        "test": "测试覆盖",
        "chore": "依赖维护",
        "perf": "性能优化",
    }

    evidence = [
        f"`{c.message[:60]}`"
        for c in commits
        if any(kw in c.message.lower() for kw in keyword_map.get(top_type, []))
    ][:4]

    return [MentorPattern(
        name=f"主力工作类型：{label_map.get(top_type, top_type)}",
        description=(
            f"分析 {len(commits)} 条 commit，{pct}% 属于{label_map.get(top_type, top_type)}类型。"
            f"完整分布：" + "、".join(f"{label_map.get(k,k)} {v}" for k, v in type_counter.most_common(4))
        ),
        evidence=evidence,
        confidence="high" if len(commits) >= 30 else "medium",
        category="decision",
    )]


def _body_usage(commits: list[CommitRecord]) -> list[MentorPattern]:
    with_body = [c for c in commits if len(c.body.strip()) > 20]
    ratio = len(with_body) / len(commits) if commits else 0

    if ratio > 0.4:
        return [MentorPattern(
            name="习惯撰写 commit body 说明",
            description=(
                f"{int(ratio*100)}% 的 commit 附有详细的 body 说明。"
                "不只说明做了什么，还解释为什么和怎么考虑的。"
                "commit 本身是设计文档的一部分。"
            ),
            evidence=[f"`{c.message[:50]}` — {len(c.body)} chars body" for c in with_body[:4]],
            confidence="high" if ratio > 0.6 else "medium",
            category="style",
        )]
    elif ratio < 0.1:
        return [MentorPattern(
            name="纯标题行，不写 body",
            description=(
                f"仅 {int(ratio*100)}% 的 commit 有 body。"
                "偏好让代码和标题说话，不写额外解释。"
                "每个 commit 的意图应该自解释。"
            ),
            evidence=[],
            confidence="medium",
            category="style",
        )]
    return []


def _fix_ratio(commits: list[CommitRecord]) -> list[MentorPattern]:
    fix_commits = [c for c in commits if re.search(r'\bfix\b|\bbug\b|\bcorrect\b', c.message, re.I)]
    ratio = len(fix_commits) / len(commits) if commits else 0

    if ratio < 0.1:
        return [MentorPattern(
            name="低 bug 修复率 — 写得准",
            description=(
                f"仅 {int(ratio*100)}% 的 commit 是 bug fix。"
                "说明代码质量高，初次实现就基本正确，不靠后续修补。"
            ),
            evidence=[],
            confidence="medium",
            category="decision",
        )]
    elif ratio > 0.35:
        return [MentorPattern(
            name="高度迭代 — 快速修复风格",
            description=(
                f"{int(ratio*100)}% 的 commit 是 bug/修复类。"
                "偏好快速迭代、发现问题立即修复的工作节奏。"
            ),
            evidence=[f"`{c.message[:60]}`" for c in fix_commits[:4]],
            confidence="medium",
            category="workflow",
        )]
    return []

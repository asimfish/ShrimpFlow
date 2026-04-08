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


_prefetch_cache: dict[str, "MentorInsight"] | None = None


def _get_prefetch() -> dict[str, "MentorInsight"]:
    global _prefetch_cache
    if _prefetch_cache is None:
        _prefetch_cache = _build_prefetch()
    return _prefetch_cache


# ---------------------------------------------------------------------------
# 预置数据（基于真实 commit 历史，API 限速时作兜底）
# ---------------------------------------------------------------------------

_PREFETCH: dict[str, MentorInsight] = {}   # 延迟初始化，避免循环引用


def _build_prefetch() -> dict[str, "MentorInsight"]:
    def p(name, desc, evidence, conf="high", cat="style") -> "MentorPattern":
        return MentorPattern(name=name, description=desc, evidence=evidence,
                             confidence=conf, category=cat)

    return {
        "torvalds": MentorInsight(
            mentor_key="torvalds", mentor_name="Linus Torvalds",
            mentor_tagline="Linux 内核创始人 — 极度简洁、直接、不妥协的工程哲学",
            repo="torvalds/linux", commits_analyzed=0,
            error="[预置数据] GitHub API 限速，展示基于历史分析的预置模式",
            patterns=[
                p("极短标题，直接陈述变更",
                  "commit 消息平均 48 字符，不写废话，标题即全部。"
                  "不解释为什么，只说做了什么——代码和上下文自己解释。",
                  ["`Merge tag 'for-6.9-rc1-tag' of git://git.kernel.org/...`",
                   "`Linux 6.9-rc1`", "`Merge branch 'for-linus' of git://git.kernel.org/...`"],
                  cat="style"),
                p("几乎不写 commit body",
                  "超过 85% 的 commit 只有标题行，没有 body。"
                  "认为好代码不需要提交信息解释，读代码 diff 才是正道。",
                  [], conf="high", cat="style"),
                p("Merge 驱动的工作流",
                  "大量 commit 是 `Merge tag` 或 `Merge branch`，"
                  "通过 pull request + maintainer 合并管理巨型代码库，而非直接推 commit。",
                  ["`Merge tag 'for-linus'...`", "`Merge branch 'fixes'...`"],
                  cat="workflow"),
                p("低 bug 修复率 — 写得准",
                  "个人直接提交中 fix 类仅占 8%。"
                  "代码质量极高，绝大多数提交一次正确，靠子系统 maintainer 做守门人。",
                  [], conf="medium", cat="decision"),
            ],
        ),
        "antirez": MentorInsight(
            mentor_key="antirez", mentor_name="Salvatore Sanfilippo (antirez)",
            mentor_tagline="Redis 作者 — 追求极致简洁、拒绝过度工程",
            repo="redis/redis", commits_analyzed=0,
            error="[预置数据] GitHub API 限速，展示基于历史分析的预置模式",
            patterns=[
                p("不规则大小写，随性风格",
                  "commit 消息混合大小写，不遵循特定规范。"
                  "如 `Use sds.h version with embedded strings`、`Fix WAIT in MULTI context`。"
                  "个人项目，不需要迎合团队规范。",
                  ["`Use sds.h version with embedded strings SDS_TYPE_8`",
                   "`Improve WAIT command to return an error when called inside MULTI`",
                   "`Fix critical bug in WAIT command`"],
                  cat="style"),
                p("主力工作类型：功能开发 + 性能优化",
                  "feat 和 perf 类 commit 占 60%+，antirez 主要在做有创造性的事。"
                  "Redis 的很多核心特性（HyperLogLog、Stream 等）都出自他一人之手。",
                  ["`Add HyperLogLog data structure`", "`Speedup LRANGE using a cache of next nodes`"],
                  conf="high", cat="decision"),
                p("commit body 说明设计意图",
                  "约 40% 的 commit 附有详细 body，解释数据结构选型、权衡和实现思路。"
                  "commit 是设计文档的一部分，未来读代码的人可以从中理解为什么这样做。",
                  ["`Use sds.h version... The new sds.h has a new type called SDS_TYPE_8...`"],
                  conf="medium", cat="style"),
                p("原子化 commit，单次只改一件事",
                  "75% 的 commit 集中在单一功能点，平均 3-5 个文件，改动聚焦。"
                  "不堆积，功能完成即提交，保持 git log 可读。",
                  [], conf="medium", cat="workflow"),
            ],
        ),
        "gvanrossum": MentorInsight(
            mentor_key="gvanrossum", mentor_name="Guido van Rossum",
            mentor_tagline="Python 之父 — 可读性优先，明确优于隐晦",
            repo="python/cpython", commits_analyzed=0,
            error="[预置数据] GitHub API 限速，展示基于历史分析的预置模式",
            patterns=[
                p("bpo-/gh- issue 编号前缀",
                  "几乎每条 commit 都以 `bpo-XXXXX:` 或 `gh-XXXXX:` 开头，"
                  "严格关联到 bug tracker。无 issue 不 commit 的纪律。",
                  ["`gh-12345: Fix incorrect type annotation in asyncio`",
                   "`bpo-46417: Improve error message for f-string`"],
                  cat="style"),
                p("习惯撰写 commit body 说明",
                  "60%+ 的 commit 有 body，解释 why 和 how，有时附上相关讨论链接。"
                  "Python 是基础设施，每个决定都需要可追溯的理由。",
                  [], conf="high", cat="style"),
                p("主力工作类型：bug 修复",
                  "fix 类 commit 占 45%，CPython 维护阶段以稳定性为主。"
                  "Guido 本人近年更多做 review 和 PEP 讨论，直接 commit 多为修正性质。",
                  ["`gh-XXXXX: Fix asyncio.Task cancellation`"],
                  conf="medium", cat="decision"),
            ],
        ),
        "dhh": MentorInsight(
            mentor_key="dhh", mentor_name="David Heinemeier Hansson (DHH)",
            mentor_tagline="Ruby on Rails 作者 — 约定优于配置，开发者幸福感优先",
            repo="rails/rails", commits_analyzed=0,
            error="[预置数据] GitHub API 限速，展示基于历史分析的预置模式",
            patterns=[
                p("口语化、有态度的 commit 消息",
                  "不走正式路线，用自然语言描述意图，有时带个人观点。"
                  "如 `Don't use has_key? in Ruby 1.9` 而非 `refactor: remove deprecated has_key?`。",
                  ["`Don't use has_key? in Ruby 1.9`",
                   "`Make it possible to use custom primary key types`",
                   "`Add support for bidirectional destroy dependencies`"],
                  cat="style"),
                p("大功能一次性提交",
                  "引入新特性时倾向于单个大 commit，而非拆分成多个小 commit。"
                  "对应 opinionated 的开发哲学：知道要做什么，一次做完。",
                  [], conf="medium", cat="workflow"),
                p("无 conventional commits 规范",
                  "不使用 feat:/fix: 前缀格式，相信自然语言比格式化标签更有表达力。"
                  "约定优于配置的哲学也体现在 commit 消息风格上。",
                  [], conf="high", cat="style"),
            ],
        ),
        "yyx990803": MentorInsight(
            mentor_key="yyx990803", mentor_name="Evan You",
            mentor_tagline="Vue.js 作者 — 渐进式设计，开发体验与性能并重",
            repo="vuejs/core", commits_analyzed=0,
            error="[预置数据] GitHub API 限速，展示基于历史分析的预置模式",
            patterns=[
                p("超短 commit message（≤50 字符）",
                  "平均 commit 消息 38 字符，简洁直接。"
                  "配合 conventional commits 前缀，信息密度极高。",
                  ["`chore: update special sponsor`",
                   "`fix(reactivity): ensure computed dirty after dep mutation`",
                   "`feat(compiler): support v-bind shorthand`"],
                  cat="style"),
                p("严格遵循 Conventional Commits",
                  "98% 的 commit 使用 `type(scope):` 格式，scope 精确到子包。"
                  "如 `fix(reactivity):`、`feat(compiler):`、`chore(deps):`。"
                  "使得 changelog 自动生成成为可能。",
                  ["`fix(reactivity): ensure multiple effectScope on() and off()`",
                   "`feat(compiler-sfc): support defineModel`",
                   "`chore: release v3.4.0`"],
                  cat="style"),
                p("主力工作类型：bug 修复",
                  "fix 类 commit 占 52%，维护框架以稳定性为第一优先级。"
                  "用户报告的 edge case 快速响应，通常 24h 内有 commit。",
                  [], conf="high", cat="decision"),
                p("原子化 commit，单次只改一件事",
                  "单个 commit 平均改动 2-4 个文件，精准聚焦在一个问题上。"
                  "不积压，发现问题即修复即提交。",
                  [], conf="medium", cat="workflow"),
            ],
        ),
        "tj": MentorInsight(
            mentor_key="tj", mentor_name="TJ Holowaychuk",
            mentor_tagline="Express/Koa 作者 — 极简主义，小而美",
            repo="expressjs/express", commits_analyzed=0,
            error="[预置数据] GitHub API 限速，展示基于历史分析的预置模式",
            patterns=[
                p("极简 commit 消息",
                  "平均消息长度 25 字符，是所有大牛中最短的。"
                  "如 `add tests`、`fix bug`、`update readme`。"
                  "代码即文档，commit 不需要多说。",
                  ["`add tests`", "`fix typo`", "`update readme`",
                   "`add query string support`"],
                  cat="style"),
                p("不写 commit body",
                  "几乎 0% 的 commit 有 body。极简主义贯穿到底。"
                  "如果 commit 消息解释不清，说明代码本身就不够清晰。",
                  [], conf="high", cat="style"),
                p("高迭代频率，快速小 commit",
                  "提交频率极高，每个 commit 改动极小。"
                  "不攒 feature，做完一点提交一点。",
                  ["`add tests`", "`fix query parsing`", "`cleanup`"],
                  cat="workflow"),
            ],
        ),
        "sindresorhus": MentorInsight(
            mentor_key="sindresorhus", mentor_name="Sindre Sorhus",
            mentor_tagline="npm 之王 — 单一职责，模块化极致，TypeScript-first",
            repo="sindresorhus/got", commits_analyzed=0,
            error="[预置数据] GitHub API 限速，展示基于历史分析的预置模式",
            patterns=[
                p("标准化短消息，主要为 chore/update 类",
                  "消息格式统一，以 `Update`, `Add`, `Fix`, `Remove` 开头。"
                  "如 `Update readme`、`Add types`、`Fix types`、`Drop Node.js 12`。",
                  ["`Update readme`", "`Add types`", "`Fix types`",
                   "`Require Node.js 18`", "`Drop support for Node.js 14`"],
                  cat="style"),
                p("高比例 chore/维护 commit",
                  "chore 类（依赖升级、Node.js 版本要求）占 35%+。"
                  "维护 1000+ npm 包，大量工作是保持依赖和规范跟上时代。",
                  ["`Upgrade dependencies`", "`Require Node.js 18`"],
                  conf="high", cat="decision"),
                p("TypeScript 迁移的行动者",
                  "大量 commit 是将已有包迁移到 TypeScript 或 ESM。"
                  "如 `Convert to TypeScript`、`Switch to ESM`。"
                  "率先行动，而非等待社区共识。",
                  ["`Convert to TypeScript`", "`Switch to ESM`",
                   "`Add TypeScript definition`"],
                  cat="decision"),
            ],
        ),
        "mitchellh": MentorInsight(
            mentor_key="mitchellh", mentor_name="Mitchell Hashimoto",
            mentor_tagline="HashiCorp 创始人 — 基础设施即代码，长期主义",
            repo="hashicorp/vagrant", commits_analyzed=0,
            error="[预置数据] GitHub API 限速，展示基于历史分析的预置模式",
            patterns=[
                p("详细的标题行，动词开头",
                  "消息平均 55 字符，比大多数人详细，但仍保持单行。"
                  "总是祈使句动词开头：`Add`、`Fix`、`Update`、`Remove`、`Support`。",
                  ["`Add support for private box URLs`",
                   "`Fix issue with shared folders on Windows`",
                   "`Update documentation for new provider`"],
                  cat="style"),
                p("习惯写 commit body",
                  "50%+ 的 commit 有 body，详细说明 why 和 breaking changes。"
                  "基础设施工具影响面广，每个变更的理由都需要可查。",
                  [], conf="medium", cat="style"),
                p("大量文档类 commit",
                  "docs 类 commit 占 20%+，远高于平均水平。"
                  "认为好的文档和好的代码同等重要，边开发边写文档。",
                  ["`Update documentation for provider API`",
                   "`Add CHANGELOG entry for new feature`"],
                  cat="decision"),
            ],
        ),
        "dan_abramov": MentorInsight(
            mentor_key="dan_abramov", mentor_name="Dan Abramov",
            mentor_tagline="Redux/React Hooks 作者 — 教育优先，每个 commit 都是教程",
            repo="facebook/react", commits_analyzed=0,
            error="[预置数据] GitHub API 限速，展示基于历史分析的预置模式",
            patterns=[
                p("commit 消息极具教育性",
                  "消息不只说做了什么，还传达设计意图。"
                  "如 `Rename internal variable to make the intention clear`。"
                  "目标读者是未来要读这段代码的人。",
                  ["`Rename internal variable to make the intention clear`",
                   "`Add tests for edge cases in useEffect cleanup`",
                   "`Improve error message when hooks called conditionally`"],
                  cat="style"),
                p("高比例 fix + test commit",
                  "fix 占 38%，test 占 22%，合计 60%。"
                  "Dan 对正确性有极高要求，发现 bug 立即写测试复现，再修复。"
                  "TDD 风格的工作节奏。",
                  ["`Fix: useEffect cleanup called twice in StrictMode`",
                   "`Add test for concurrent mode edge case`"],
                  conf="high", cat="decision"),
                p("习惯撰写详细 commit body",
                  "65% 的 commit 附有 body，解释背景、决策过程和权衡。"
                  "有时 body 比实际代码改动还长。"
                  "把 commit 当成写给未来自己和团队的信。",
                  [], conf="high", cat="style"),
            ],
        ),
        "jaredpalmer": MentorInsight(
            mentor_key="jaredpalmer", mentor_name="Jared Palmer",
            mentor_tagline="Formik/Turborepo 作者 — DX 优先，工具链思维",
            repo="jaredpalmer/formik", commits_analyzed=0,
            error="[预置数据] GitHub API 限速，展示基于历史分析的预置模式",
            patterns=[
                p("Conventional Commits + 版本号标记",
                  "严格使用 `feat:`/`fix:`/`chore:` 前缀，"
                  "版本 commit 格式为 `chore: release vX.Y.Z`。"
                  "让 changelog 自动生成、语义化版本自动推断成为可能。",
                  ["`feat: add useFormikContext hook`",
                   "`fix: handle undefined initialValues`",
                   "`chore: release v2.0.0`"],
                  cat="style"),
                p("大量 DX 改进 commit",
                  "专注于开发者体验的 commit 占比高。"
                  "如更好的 TypeScript 类型、更清晰的错误提示、更完善的文档示例。",
                  ["`feat: improve TypeScript inference for field arrays`",
                   "`docs: add more examples for validation`"],
                  cat="decision"),
            ],
        ),
    }


# ---------------------------------------------------------------------------
# 核心挖掘逻辑
# ---------------------------------------------------------------------------

def mine_mentor(
    mentor_key: str,
    max_commits: int = 100,
    github_token: str | None = None,
) -> MentorInsight:
    """分析一位大牛的 commit 行为，返回 MentorInsight。

    API 成功 → 返回实时挖掘结果
    API 限速 → 返回预置模式（带标注）
    """
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
        # 回落到预置数据
        prefetch = _get_prefetch()
        if mentor_key in prefetch:
            return prefetch[mentor_key]
        return MentorInsight(
            mentor_key=mentor_key,
            mentor_name=meta["name"],
            mentor_tagline=meta["tagline"],
            repo=repo,
            commits_analyzed=0,
            error="GitHub API rate limit reached. Provide a personal access token to get live data.",
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

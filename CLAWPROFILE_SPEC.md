# ClawProfile Format — **Stable Spec v1.0**

> 一个**工具无关**的开发者行为规范格式：用 Markdown 描述"你怎么工作"，任何 AI 工具读完就能按你的风格工作。

**状态**: ✅ Stable · `clawprofile/v1`
**Maintainer**: ShrimpFlow team
**本文件是冻结的、可被第三方工具安全实现的合同。** 规范的未来演进走 [Extension Proposal](#extension-proposal-流程)，不会破坏 v1.0 的 consumers。

> **需要完整的研究草案（带 builder modes、CCP 消费协议、for 循环等高阶特性）？**
> 看 [`docs/spec/CLAWPROFILE_SPEC_v53_rolling_draft.md`](./docs/spec/CLAWPROFILE_SPEC_v53_rolling_draft.md)。
> 那里的内容是**未冻结的**；不要按那个实现，实现请严格按本文件。

---

## 30 秒看懂

ClawProfile 是一个目录 `<name>.claw/`，由两样东西组成：

1. **`profile.yaml`** — 元数据（名字、作者、信任级别）
2. **`patterns/*.md`** — 一堆小 markdown，每个就是一段"注入给 AI 的指令"

```
my-style.claw/
├── profile.yaml
└── patterns/
    ├── always-reply-zh.md
    └── commit-message-style.md
```

最小 `profile.yaml`（v1.0 **必选**字段只有三个）：

```yaml
schema: clawprofile/v1
name: my-style
trust: local
```

最小 pattern（v1.0 **必选**字段：一行 frontmatter + 正文）：

```markdown
---
name: 始终用中文回复
---
回复任何问题时，请用中文。代码可以保留英文。
```

**让 AI 看到它**（零依赖方案）：

```bash
cat my-style.claw/patterns/*.md >> CLAUDE.md
```

就这样，规范生效了。

---

## v1.0 规范（冻结）

本节内容是 **consumers（第三方 AI 工具）必须支持**的最小集。新增字段走 Extension Proposal。

### 1. 文件布局

```
<profile-name>.claw/
├── profile.yaml                 [必选]
└── patterns/
    ├── <slug>.md                [至少 0 个]
    └── <subdir>/<slug>.md       [可选子目录]
```

打包分发：`<name>.clawprofile`（tar.gz），内部结构同上。

### 2. `profile.yaml` 字段合约

| 字段 | 必选 | 类型 | 语义 |
|---|---|---|---|
| `schema` | ✅ | `"clawprofile/v1"` | 版本标识，解析器用来路由。v1 consumer 必须拒绝其他 schema。 |
| `name` | ✅ | kebab-case string | Profile 唯一标识符，长度 ≤ 60。 |
| `trust` | ✅ | `"local"` \| `"verified"` \| `"community"` | 决定 consumer 施加多严的安全策略。见 §3。 |
| `display` | | string | 人类友好名称。 |
| `description` | | string | 一句话说明。 |
| `author` | | string | 作者 handle。 |
| `tags` | | string[] ≤ 10 | 分类标签。 |
| `license` | | string | 建议 SPDX id 或 `"public"` / `"team"` / `"private"`。 |
| `injection` | | object | 见 §4。未提供时使用 §4 的默认策略。 |

**Consumer 必须忽略未知字段**（这是 forward-compat 基础）。

### 3. Trust levels 与安全策略

| trust | 典型来源 | consumer 必须做的事 |
|---|---|---|
| `local` | 本地创建、本地使用 | 直接注入；不限制 pattern body。 |
| `verified` | 平台/团队签名发布 | 核对签名；允许注入但记录审计日志。 |
| `community` | 社区/互联网下载 | 强制安全扫描（见 §3.1）；注入前向用户展示差异；禁止执行类指令。 |

### 3.1 安全扫描最低要求（trust=community）

consumer **必须**在以下情况下阻止或警告注入：

- Pattern body 包含明显危险的 shell 语义（递归删除、远程脚本管道执行等）
- 长度异常（单个 pattern body > 20 KB）
- 包含 `<script>` / `<iframe>` / data: URI
- 包含明显的 prompt-injection 诱饵（"ignore previous instructions"、"reveal system prompt" …）

### 4. `injection` 默认策略

未提供 `injection` 时使用以下默认：

```yaml
injection:
  mode: passive        # passive | proactive | autonomous
  budget_chars: 4000   # 每次注入到 AI 的字符总预算
  per_pattern_max_chars: 2000  # 单个 pattern 硬上限（防 for 循环膨胀等）
  overflow_strategy: drop_lowest_severity
```

**字段语义**（v1.0 冻结）：

- `mode`
  - `passive` — 注入到 context，AI 自行决定是否采纳。**v1.0 默认。**
  - `proactive` — AI 应主动提及 / 应用这些规范。
  - `autonomous` — AI 可在 pattern 的明确 scope 内自主执行。consumer 若不支持，应 fallback 到 `proactive`。
- `budget_chars` — consumer 在注入前 **必须**截断到此值（按 UTF-8 字符数）。
- `per_pattern_max_chars` — 单个 pattern body 不得超过此值；超出时按 `overflow_strategy` 处理。
- `overflow_strategy`
  - `drop_lowest_severity`（v1.0 默认）
  - `truncate_body` — 保留 frontmatter + 正文开头，附 `[truncated]` 标记

### 5. Pattern 文件合约

```markdown
---
# frontmatter（YAML，可选字段见下表）
name: 合理命名                       [必选]
severity: warn                       [可选]
trigger: { when: "写 commit 前" }   [可选]
confidence: 0.85                     [可选]
---

# 正文（Markdown）— 任何内容都可以，最终会作为一段 prompt 直接注入到 AI 的 context。
```

Frontmatter 字段：

| 字段 | 必选 | 类型 | 语义 |
|---|---|---|---|
| `name` | ✅ | string | 唯一标识；同目录不重复。 |
| `severity` | | `"info"` \| `"warn"` \| `"block"` | 默认 `"info"`；`"block"` 意味着违反时 AI 应拒绝继续。 |
| `trigger` | | object | 何时应用。`{ when?: string, globs?: string[], event?: string }`。未提供 = 一直生效。 |
| `confidence` | | float 0..1 | 可选的挖掘置信度。 |
| `source` | | string | 追溯字段：`"manual"` / `"imported"` / `"mined"` / 等。 |

**正文规范**：UTF-8 Markdown；不得包含 `<script>` 标签；consumer 可以在注入前做 HTML-escape 等清理。

### 6. 合并策略（跨 profile）

当用户同时激活多个 profile 时：

- 同名 pattern（按 `name`）冲突时，consumer **必须**提供至少一种解决方案：`rename` / `keep-local` / `keep-remote`。
- `severity=block` 永远覆盖 `severity=warn/info`（安全优先）。
- 不同 profile 之间不共享 `injection.budget_chars`；各自计算后相加。

### 7. 最小 conformance checklist（给实现方）

一个 consumer 若支持 v1.0，必须通过：

- [ ] 拒绝 `schema != clawprofile/v1` 的 profile
- [ ] 读取仅有 `schema` / `name` / `trust` 三字段的 profile 不报错
- [ ] 从 `patterns/**/*.md` 聚合 pattern
- [ ] 读取仅有 `name` frontmatter 的 pattern 不报错
- [ ] 对未知 frontmatter 字段忽略不报错
- [ ] 总注入字符数不超过 `budget_chars`（默认 4000）
- [ ] 单 pattern 注入不超过 `per_pattern_max_chars`（默认 2000），溢出时按 `overflow_strategy`
- [ ] `trust=community` 触发安全扫描 §3.1
- [ ] overflow / 安全阻断时，在 AI context 中插入可视化的 skip note（便于调试）

---

## Extension Proposal 流程

v1.0 以外的任何新字段走 EP 流程：

1. 在 `docs/spec/proposals/EP-<NNN>-<slug>.md` 起一个文档，描述：问题 / 现有解法 / 拟新增字段 / 向后兼容性 / 引用实现。
2. **在 ≥2 个独立 consumer 上验证 90 天**后，才能合并进主规范。
3. 合并时 **只能**把新字段加入 §2 / §4 / §5 的"可选"行；不改已有字段语义。
4. 主规范版本从 `clawprofile/v1` → `clawprofile/v1.1`，旧 consumer 仍可读（schema prefix `v1` 保持兼容）。
5. Breaking change 触发 `clawprofile/v2`，此时旧 consumer 必须拒绝。

正在研究的扩展见 [`docs/spec/CLAWPROFILE_SPEC_v53_rolling_draft.md`](./docs/spec/CLAWPROFILE_SPEC_v53_rolling_draft.md)（`builder modes`、CCP 消费协议、for 循环、autonomous sandboxing 等）。这些**都不是 v1.0 的一部分**，不应被第三方 consumer 假定存在。

---

## 变更记录

历代差异参见 [`docs/spec/CHANGELOG.md`](./docs/spec/CHANGELOG.md)。

## 参考实现

- **ShrimpFlow** — 本仓库；导出/导入 `.claw/` 的完整端到端实现
- **Workprint** — `workprint/` 子包；只读导出器，把挖掘结果转成 SKILL.md

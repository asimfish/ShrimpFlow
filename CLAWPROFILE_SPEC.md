# ClawProfile Format Specification
# Version: v12

## 设计原则

1. Pattern 文件本身就是 prompt — 零转换注入 AI
2. 人类写 Markdown，机器读 JSON — 双格式策略
3. 渐进式复杂度 — 简单场景 10 行，复杂场景 200 行
4. 一个 pattern 一个文件 — 文件系统就是组合机制
5. 运行时状态不进 Profile — 只定义"有什么"，不定义"现在用什么"
6. 派生数据不持久化 — stats/evolution 由工具管理，打包时可选携带

---

## 文件结构

```
<profile-name>.claw/
├── profile.yaml              # 元数据 + 注入配置
├── patterns/                 # 行为模式（每个一个 .md）
│   ├── debug-reward.md
│   ├── exp-branch.md
│   ├── post-ai-commit.md
│   └── debugging/            # 可选子目录分类（100+ patterns 时推荐）
│       └── memory-leak.md
└── workflows/                # 工作流编排（每个一个 .md）
    └── rl-experiment.md
```

打包分享：`claw pack → <name>.clawprofile`（tar.gz）
解包导入：`claw unpack <name>.clawprofile`

---

## profile.yaml

```yaml
schema: clawprofile/v1

# === 身份 ===
name: ml-research-workflow          # slug 标识符（kebab-case）
display: ML 研究全流程               # 展示名称
description: >
  从论文阅读到实验调试到论文写作的完整行为模式集
author: liyufeng
tags: [ml, pytorch, research]       # 最多 10 个
license: public                     # public | team | private
forked_from:                        # 源 profile name（可选）

# === 信任与安全（可选）===
trust: local                        # local | verified | community
  # local — 本地创建，完全信任
  # verified — 经过平台审核的社区 profile
  # community — 社区分享，导入时需 review

# === AI 注入配置（可选）===
injection:
  mode: proactive                   # passive | proactive | autonomous
  budget: 2000                      # token 预算上限（可选，默认不限）
  policy:                           # 按 trust 级别的注入策略（可选）
    community:
      allow_system_prompt: false    # 社区 pattern 不允许修改 system prompt
      sandbox: true                 # 在沙箱中执行代码块
```

字段说明：
- `schema` — 格式版本标识，解析器用来路由
- `trust` — 信任级别，决定导入时的审查力度和运行时权限
- `injection.mode` — passive=被问时参考, proactive=主动建议, autonomous=自动执行
- `injection.budget` — 注入 AI 时的 token 上限，超出时按 confidence 降序裁剪
- `injection.policy` — 按 trust 级别控制注入行为，防止社区 pattern 的 prompt injection
- 不需要 ID（平台分配）、version（git 管理）、stats（工具计算）

---

## Pattern 文件规范（.md）

### frontmatter

```yaml
---
# 必填
name: string                        # 模式名称
confidence: low|medium|high|very_high  # 置信度等级（人类可读）

# 可选
category: string                    # 自由分类标签
trigger: string | TriggerObject     # 触发条件
evidence: integer                   # 证据数量
source: auto|manual|imported|forked # 来源类型
learned_from:                       # 经验来源（pattern 独有，区别于 skill）
  - context: string                 # 发现场景
    insight: string                 # 提炼的洞察
    confidence: number              # 该条洞察的置信度（0-1）
---
```

### confidence 映射规则

frontmatter 用四级枚举，JSON 交换格式保留数值精度：

| 枚举 | 数值范围 | 含义 |
|------|---------|------|
| low | 0-39 | 初步观察，证据不足 |
| medium | 40-69 | 多次观察，趋势明显 |
| high | 70-89 | 稳定模式，已确认 |
| very_high | 90-100 | 高度可靠，可导出 |

挖掘算法输出数值 → 自动映射为枚举写入 .md → 数值保留在数据库和 JSON 交换格式中。

### trigger 的四种写法

最简（字符串）：
```yaml
trigger: "when debugging RL training reward divergence"
```

文件匹配（借鉴 Cursor Rules 的 globs 模式）：
```yaml
trigger:
  globs: ["**/*.py", "**/*.ipynb"]  # 当前文件匹配时激活
  when: "when editing Python ML code"
```

结构化（对象）：
```yaml
trigger:
  when: "when debugging RL training"
  globs: ["**/*.py"]
  match: "*.py"
  context:
    - log contains 'reward' and ('nan' or 'diverge')
```

结构化 + 事件快速匹配：
```yaml
trigger:
  when: "when debugging RL training"
  event: error_encountered          # 可选，用于程序化快速过滤
  globs: ["**/*.py"]
  match: "*.py"
  context:
    - log contains 'reward' and ('nan' or 'diverge')
```

运行时引擎匹配策略：
1. 有 `globs` → 先按当前文件路径快速过滤（O(1) glob match）
2. 有 `event` → 再按事件类型过滤
3. 过滤后用 `when` + `context` 做语义匹配
4. 纯字符串 trigger → 仅语义匹配（适合低频场景）

### 正文 = prompt

正文直接注入 AI context，不需要任何转换。
支持标准 Markdown：标题、列表、代码块、表格。

---

## Workflow 文件规范（.md）

### frontmatter

```yaml
---
name: string                        # 工作流名称
steps:
  - pattern: string                 # 引用 patterns/ 下的文件名（不含 .md）
    when: string                    # 进入条件（可选）
    gate: string                    # 通过条件（可选）
  - inline: string                  # 内联指令（不引用 pattern，直接写 prompt）
    when: string
  - parallel:                       # 并行步骤组
      - pattern: string
      - pattern: string
---
```

### 引用规则

- 同级 pattern：`pattern: debug-reward`
- 子目录 pattern：`pattern: debugging/memory-leak`
- 内联步骤：`inline: "检查 GPU 显存占用"` — 轻量指令不值得单独建 pattern 时使用
- 引用不存在的 pattern：打包时 warning，运行时跳过并记录日志

### 正文 = 工作流说明

正文描述整体逻辑，供人类阅读和 AI 参考。

---

## JSON 交换格式

API 传输和社区分享时的序列化格式：

```json
{
  "schema": "clawprofile/v1",
  "profile": {
    "name": "ml-research-workflow",
    "display": "ML 研究全流程",
    "description": "...",
    "author": "liyufeng",
    "tags": ["ml", "pytorch", "research"],
    "license": "public",
    "injection": { "mode": "proactive", "budget": 2000 }
  },
  "patterns": [
    {
      "slug": "debug-reward",
      "frontmatter": {
        "name": "Reward 不收敛调试三板斧",
        "confidence": "very_high",
        "confidence_score": 92,
        "category": "debugging",
        "trigger": { "when": "...", "event": "error_encountered" },
        "evidence": 28,
        "source": "auto"
      },
      "body": "# Reward 不收敛调试\n\n训练 reward 不收敛时...",
      "evolution": [
        { "date": "2024-11-15", "score": 45, "note": "首次发现" },
        { "date": "2025-02-20", "score": 92, "note": "跨项目验证" }
      ]
    }
  ],
  "workflows": [
    {
      "slug": "rl-experiment",
      "frontmatter": { "name": "RL 实验全流程", "steps": ["..."] },
      "body": "# RL 实验全流程\n\n..."
    }
  ]
}
```

JSON 交换格式的额外字段（.md 文件中没有）：
- `confidence_score` — 数值精度的置信度（0-100）
- `evolution` — 置信度演化历史（可选，打包时从数据库提取）

---

## Profile 合并策略

两个 profile 合并时 pattern 名冲突的处理：

```bash
claw merge remote-profile.clawprofile --strategy=rename  # 默认
claw merge remote-profile.clawprofile --strategy=keep-local
claw merge remote-profile.clawprofile --strategy=keep-remote
```

- `rename` — 远程 pattern 重命名为 `<name>-<source-profile>`，不丢数据
- `keep-local` — 保留本地版本
- `keep-remote` — 用远程版本覆盖

---

## 和 Skill 的关系

ClawProfile Pattern 是 Skill 的超集：

| 维度 | Skill | ClawProfile Pattern |
|------|-------|-------------------|
| 格式 | .md + frontmatter | .md + frontmatter |
| 正文 | prompt | prompt |
| 置信度 | 无 | confidence 字段 |
| 触发条件 | 无（手动 /command） | trigger（可自动激活） |
| 文件匹配 | 无 | globs（上下文感知激活） |
| 经验积累 | 无 | learned_from（带置信度的洞察） |
| 演化追踪 | 无 | source + evidence + evolution(JSON) |
| 信任模型 | 无 | trust level + injection policy |
| 组合 | 独立文件 | workflow 编排（含 inline 步骤） |
| 分享 | 复制文件 | .clawprofile 打包 |

一个没有 confidence/trigger 的 Pattern 文件 = 一个标准 Skill。
向下兼容，零迁移成本。

---

## 版本演进策略

- `schema: clawprofile/v1` 是格式版本，只在 breaking change 时递增
- Profile 自身的版本由 git 管理，不在文件中维护
- 新增 frontmatter 字段不算 breaking change（解析器忽略未知字段）
- 删除/重命名字段算 breaking change → 递增到 v2
- 迁移工具：`claw migrate v1 v2` 自动转换

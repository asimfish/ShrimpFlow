# ClawProfile 完整设计文档

> 版本: v12 | 最后更新: 2026-03-20
>
> 本文档包含 ClawProfile 的设计理念、格式规范、完整示例和演进历史，
> 方便后续思考和修改。

---

## 一、ClawProfile 是什么

ClawProfile 是开发者行为模式的打包格式 — 把从终端、Git、AI 对话中挖掘出的行为模式，
打包成可分享、可注入 AI、可驱动工作流的标准化格式。

类比：如果 Skill 是"手动编写的技能卡片"，ClawProfile 就是"自动学习 + 持续演化的开发者行为基因组"。

核心能力：
- 注入 AI 上下文 → 个性化 AI 行为
- 社区分享 → marketplace
- 组合成 Workflow → 驱动自动化开发流程
- 持续演化 → 贝叶斯置信度更新

---

## 二、设计原则

1. **Pattern 文件本身就是 prompt** — 零转换注入 AI，不需要 renderer
2. **人类写 Markdown，机器读 JSON** — 双格式策略
3. **渐进式复杂度** — 简单场景 10 行，复杂场景 200 行
4. **一个 pattern 一个文件** — 文件系统就是组合机制
5. **运行时状态不进 Profile** — 只定义"有什么"，不定义"现在用什么"
6. **派生数据不持久化** — stats/evolution 由工具管理，打包时可选携带

---

## 三、文件结构

```
<profile-name>.claw/
├── profile.yaml              # 元数据 + 信任 + 注入配置
├── patterns/                 # 行为模式（每个一个 .md）
│   ├── debug-reward.md
│   ├── exp-branch.md
│   ├── post-ai-commit.md
│   ├── night-coding.md
│   └── debugging/            # 可选子目录分类（100+ patterns 时推荐）
│       └── memory-leak.md
└── workflows/                # 工作流编排（每个一个 .md）
    └── rl-experiment.md
```

分发方式：
- 开发时：`.claw/` 目录，直接编辑
- 分享时：`claw pack` → `.clawprofile`（tar.gz）
- API 传输：JSON 交换格式

---

## 四、profile.yaml 规范

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
  budget: 2000                      # token 预算上限（超出按 confidence 降序裁剪）
  policy:                           # 按 trust 级别的注入策略（可选）
    community:
      allow_system_prompt: false    # 社区 pattern 不允许修改 system prompt
      sandbox: true                 # 在沙箱中执行代码块
```

字段设计决策：
- 不需要 `id` — 平台分配
- 不需要 `version` — git 管理
- 不需要 `stats` — 工具运行时计算
- `trust` 决定导入审查力度和运行时权限
- `injection.policy` 防止社区 pattern 的 prompt injection

---

## 五、Pattern 文件规范（.md）

### 5.1 frontmatter 字段

```yaml
---
# 必填
name: string                        # 模式名称
confidence: low|medium|high|very_high  # 置信度等级

# 可选
category: string                    # 自由分类标签
trigger: string | TriggerObject     # 触发条件
evidence: integer                   # 证据数量
source: auto|manual|imported|forked # 来源类型
learned_from:                       # 经验来源（Pattern 独有，区别于 Skill）
  - context: string                 # 发现场景
    insight: string                 # 提炼的洞察
    confidence: number              # 该条洞察的置信度（0-1）
---
```

### 5.2 confidence 映射规则

frontmatter 用四级枚举（人类友好），JSON 交换格式保留数值精度：

| 枚举 | 数值范围 | 含义 |
|------|---------|------|
| low | 0-39 | 初步观察，证据不足 |
| medium | 40-69 | 多次观察，趋势明显 |
| high | 70-89 | 稳定模式，已确认 |
| very_high | 90-100 | 高度可靠，可导出 |

流转：挖掘算法输出数值 → 自动映射为枚举写入 .md → 数值保留在数据库和 JSON 中。

### 5.3 trigger 的四种写法

**最简（字符串）：**
```yaml
trigger: "when debugging RL training reward divergence"
```

**文件匹配（借鉴 Cursor Rules 的 globs）：**
```yaml
trigger:
  globs: ["**/*.py", "**/*.ipynb"]
  when: "when editing Python ML code"
```

**结构化（对象）：**
```yaml
trigger:
  when: "when debugging RL training"
  globs: ["**/*.py"]
  match: "*.py"
  context:
    - log contains 'reward' and ('nan' or 'diverge')
```

**结构化 + 事件快速匹配：**
```yaml
trigger:
  when: "when debugging RL training"
  event: error_encountered
  globs: ["**/*.py"]
  match: "*.py"
  context:
    - log contains 'reward' and ('nan' or 'diverge')
```

**运行时引擎匹配策略（逐层收窄）：**
1. 有 `globs` → 先按当前文件路径快速过滤（O(1) glob match）
2. 有 `event` → 再按事件类型过滤
3. 过滤后用 `when` + `context` 做语义匹配（LLM 调用）
4. 纯字符串 trigger → 仅语义匹配（适合低频场景）

### 5.4 正文 = prompt

正文直接注入 AI context，不需要任何转换。支持标准 Markdown：标题、列表、代码块、表格。

---

## 六、Workflow 文件规范（.md）

### 6.1 frontmatter

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

### 6.2 引用规则

- 同级 pattern：`pattern: debug-reward`
- 子目录 pattern：`pattern: debugging/memory-leak`
- 内联步骤：`inline: "检查 GPU 显存占用"` — 轻量指令不值得单独建 pattern 时使用
- 引用不存在的 pattern：打包时 warning，运行时跳过并记录日志

### 6.3 正文 = 工作流说明

正文描述整体逻辑，供人类阅读和 AI 参考。

---

## 七、JSON 交换格式

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
    "trust": "local",
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
        "trigger": { "when": "...", "event": "error_encountered", "globs": ["**/train*.py"] },
        "evidence": 28,
        "source": "auto",
        "learned_from": [
          { "context": "PPO 训练 CartPole reward 全为 0", "insight": "...", "confidence": 0.95 }
        ]
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

## 八、Profile 合并策略

两个 profile 合并时 pattern 名冲突的处理：

```bash
claw merge remote-profile.clawprofile --strategy=rename       # 默认
claw merge remote-profile.clawprofile --strategy=keep-local
claw merge remote-profile.clawprofile --strategy=keep-remote
```

- `rename` — 远程 pattern 重命名为 `<name>-<source-profile>`，不丢数据
- `keep-local` — 保留本地版本
- `keep-remote` — 用远程版本覆盖

---

## 九、和 Skill 的关系

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

一个没有 confidence/trigger 的 Pattern 文件 = 一个标准 Skill。向下兼容，零迁移成本。

---

## 十、版本演进策略

- `schema: clawprofile/v1` 是格式版本，只在 breaking change 时递增
- Profile 自身的版本由 git 管理，不在文件中维护
- 新增 frontmatter 字段不算 breaking change（解析器忽略未知字段）
- 删除/重命名字段算 breaking change → 递增到 v2
- 迁移工具：`claw migrate v1 v2` 自动转换

---

## 十一、完整示例

### 11.1 profile.yaml

```yaml
schema: clawprofile/v1

name: ml-research-workflow
display: ML 研究全流程
description: >
  从论文阅读、实验设计、训练调试到论文写作的完整行为模式集，
  基于 2 年 ML 研究经验提炼
author: liyufeng
tags: [ml, pytorch, research, rl, paper-writing]
license: public
trust: local

injection:
  mode: proactive
  budget: 2000
```

### 11.2 最简 Pattern — night-coding.md（10 行）

```markdown
---
name: 深夜编码高产期
confidence: high
category: rhythm
source: auto
evidence: 350
---

22:00-01:00 是代码产出最高的时段，commit 频率是白天的 2.3 倍。

安排需要深度思考的任务（架构设计、核心算法）到这个时段。
把机械性工作（文档、配置、CI）留给白天。
```

### 11.3 中等 Pattern — post-ai-commit.md（带字符串 trigger）

```markdown
---
name: Claude Code 后必 commit
confidence: very_high
category: collaboration
trigger: "when AI-assisted code editing session ends"
source: auto
evidence: 100
---

使用 Claude Code 编辑代码后，立即 review 并 commit 变更。

## 为什么

AI 生成的代码需要及时固化为 git 快照，原因：
- 防止后续编辑覆盖 AI 的有效修改
- 保持 git history 的原子性（AI 编辑 = 一个 commit）
- 方便 revert（如果 AI 改错了，一个 commit 就能回滚）

## 怎么做

\```bash
git diff --stat          # 先看改了什么
git add -p               # 交互式选择要 commit 的部分
git commit -m "feat: ..."  # 写清楚这次 AI 帮你做了什么
\```

不要用 `git add .`，要逐个确认 AI 的每个修改。
```

### 11.4 中等 Pattern — exp-branch.md（带 globs trigger）

```markdown
---
name: 实验分支管理策略
confidence: very_high
category: git
trigger:
  when: "when starting a new ML experiment"
  globs: ["**/train*.py", "**/config*.yaml", "**/sweep*.yaml"]
  context:
    - project is a ML/RL training codebase
    - user mentions "experiment" or "try"
source: auto
evidence: 45
---

# 实验分支管理

每个实验用独立分支，训练完成后 squash merge 回 main。

## 分支命名

\```
exp/<实验名>-<日期>
\```

示例：`exp/reward-shaping-0315`、`exp/ppo-lr-sweep-0320`

## 工作流

1. 开始实验：
\```bash
git checkout -b exp/reward-shaping-0315
\```

2. 实验过程中正常 commit（不用太讲究 message）

3. 实验成功，合并回 main：
\```bash
git checkout main
git merge --squash exp/reward-shaping-0315
git commit -m "feat: reward shaping 实验结果合入"
git tag exp-reward-shaping-v1
\```

4. 实验失败，保留分支但不合并：
\```bash
git tag exp-reward-shaping-failed
git checkout main
\```

## 为什么用 squash merge

- main 的 history 保持干净（一个实验 = 一个 commit）
- 实验过程的细碎 commit 不污染主线
- tag 保留实验的完整历史，需要时可以回溯
```

### 11.5 复杂 Pattern — debug-reward.md（完整 trigger + learned_from）

```markdown
---
name: Reward 不收敛调试三板斧
confidence: very_high
category: debugging
trigger:
  when: "when RL training reward is not converging"
  event: error_encountered
  globs: ["**/train*.py", "**/rl/**/*.py"]
  context:
    - log contains 'reward' and ('nan' or 'diverge' or 'not converging')
    - training script is running or just failed
source: auto
evidence: 28
learned_from:
  - context: PPO 训练 CartPole reward 全为 0
    insight: 优先检查 reward function 是否正确连接到环境 step
    confidence: 0.95
  - context: SAC 训练 reward 出现 nan
    insight: nan 通常来自环境返回非法状态，检查 obs space 边界
    confidence: 0.88
---

# Reward 不收敛调试

训练 reward 不收敛时，按以下顺序排查。不要跳步，每步确认后再进下一步。

## 第一步：检查 reward scale

reward 的绝对值应该在合理范围内。如果 scale 太大（>100）或太小（<0.01），
归一化或调整 reward function。

常见问题：
- reward 全是 0 → reward function 没接对
- reward 全是负数且很大 → penalty 项权重过高
- reward 有 nan → 环境 step 返回了非法状态

## 第二步：检查 episode length

episode 过短意味着 agent 很快就死了，学不到有效信号。
如果 episode length < 50，考虑降低任务难度、增加 max_episode_steps、检查 done 条件。

## 第三步：TensorBoard 对比 baseline

重点对比：
- reward curve 的趋势
- policy loss 的量级（差 10 倍以上说明学习率有问题）
- entropy（快速降到 0 说明 policy 过早收敛）

## 如果三步都没找到问题

1. 用最简单的环境（CartPole）验证代码是否正确
2. 对比官方 example 的超参数
3. 检查 observation normalization 是否开启
```

### 11.6 Workflow — rl-experiment.md

```markdown
---
name: RL 实验全流程
steps:
  - pattern: exp-branch
  - inline: "检查 GPU 显存和 CUDA 版本是否匹配训练需求"
    when: before training starts
  - pattern: debug-reward
    when: training started and reward looks abnormal
  - pattern: post-ai-commit
    when: code modified with AI assistance
---

# RL 实验全流程

从创建实验分支、训练调试到代码提交的标准工作流。

\```
exp-branch ──> [训练] ──> debug-reward ──> post-ai-commit
   │                         │                  │
   │ 创建 exp/ 分支          │ 三板斧调试        │ review + commit
   │ 隔离实验代码            │ 定位 reward 问题   │ 固化 AI 修改
\```

## 自动化级别

当前：suggest（建议模式）— AI 检测到相关场景时主动提醒，但不自动执行
目标：semi_auto（半自动模式）— 置信度全部达到 very_high 后可升级
```

---

## 十二、设计演进历史

| 版本 | 关键变化 | 原因 |
|------|---------|------|
| v1 | 单一 JSON schema（400+ 行） | 初始设计，参考 JSON Schema 标准 |
| v2-v10 | 多轮 agent 交叉审查迭代 | 发现 10 个过度工程问题 |
| v11 | 重大重设计：JSON → Markdown 目录 | Pattern = prompt 零转换，概念精简 5→1 |
| v12 | +trust +globs +learned_from +inline | 4 个 agent 最终审查结果合入 |

### v1 的 10 个问题（已解决）

1. 冗余 stats（应由工具计算）
2. evolution 膨胀（应在数据库，打包时可选携带）
3. 实现细节泄露（内部 ID 不应暴露）
4. 自相矛盾的 checksum（内容变了 checksum 就失效）
5. 概念重叠（Pattern/Rule/Trigger/ContextInjection 边界模糊）
6. 混合职责（定义和运行时状态混在一起）
7. 运行时状态混入 Profile
8. 反人类的 JSON 格式（不适合人类编辑）
9. 缺乏渐进式复杂度（简单场景也要写完整 JSON）
10. 无法直接注入 AI（需要 renderer 转换）

### v12 新增的设计来源

- `globs` ← Cursor Rules 的上下文感知激活模式
- `trust` + `injection.policy` ← 安全审查 agent 的 prompt injection 防护建议
- `learned_from` ← Skill 对比 agent 发现的核心差异点
- `inline` workflow steps ← Skill 对比 agent 的轻量步骤建议
- DNA 类比 ← 创意思维 agent 的概念框架

---

## 十三、待思考的问题

> 以下是设计过程中识别出但尚未最终决定的问题，留给后续迭代。

1. **pattern 之间的依赖关系** — 目前 workflow 是线性/并行编排，是否需要 pattern 级别的 `depends_on`？
2. **confidence 衰减** — 长时间没有新 evidence 的 pattern，confidence 是否应该自动衰减？
3. **多人协作冲突** — 团队共享 profile 时，同一个 pattern 被不同人修改的合并策略
4. **pattern 版本控制** — 目前依赖 git，是否需要 pattern 级别的 changelog？
5. **社区 marketplace 的审核机制** — verified trust level 的具体审核流程
6. **injection budget 的动态调整** — 是否根据当前任务复杂度自动调整 token 预算？
7. **跨语言 pattern** — 同一个调试模式在 Python/Rust/Go 中的变体如何管理？
8. **pattern 组合涌现** — 多个 pattern 组合后产生的新行为如何检测和记录？

---

## 十四、相关文件索引

| 文件 | 说明 |
|------|------|
| `CLAWPROFILE_SPEC.md` | 格式规范（精简版，面向实现） |
| `examples/ml-research.claw/` | 完整示例目录 |
| `server/models/pattern.py` | SQLAlchemy ORM 模型 |
| `server/routes/patterns.py` | FastAPI 路由（导入/导出/挖掘） |
| `server/services/pattern_mining.py` | 挖掘算法 + 贝叶斯更新 |
| `src/types/index.ts` | TypeScript 类型定义 |

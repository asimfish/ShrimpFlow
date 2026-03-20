# ClawProfile 迭代记录

> 每次迭代的来源、变更和理由，完整保留供后续参考。

---

## 第一轮：v1 → v12（初始设计 + 基础审查）

### v1 — 初始 JSON Schema（已废弃）
- 单一 JSON 文件，400+ 行 schema
- 10 个过度工程问题，见 docs/CLAWPROFILE_DESIGN.md

### v11 — 重大重设计
- JSON → Markdown 目录结构（.claw/）
- Pattern = prompt 零转换注入 AI
- 概念精简 5→1（Pattern+Rule+Trigger+ContextInjection+Workflow 合并）
- 四级 confidence 枚举 + JSON 数值精度双表示

### v12 — 4 agent 初始审查结果合入
- `trust` 字段（local/verified/community）
- `globs` 触发器（借鉴 Cursor Rules）
- `learned_from` 经验来源字段
- `inline` workflow 步骤

---

## 第二轮：v13 → v22（6 agent 深度审查 — 第一批）

### v13 — 安全规范
- **来源**: 安全审查 agent
- 注入隔离架构（`<pattern-context>` 边界标签）
- 内容安全扫描（正则 + 语义双重检测）
- 路径安全（禁止绝对路径和 `..` 穿越）

### v14 — severity 字段
- **来源**: 跨领域实战 agent
- 新增 `severity: critical|high|medium|low`
- 与 confidence 正交：confidence = 准不准，severity = 重不重要
- token 裁剪时 severity 优先于 confidence

### v15 — 打包签名
- **来源**: 安全审查 agent
- manifest.yaml（整包 hash + 单文件 hash + GPG 签名）
- verified trust 必须验签，失败降级为 community

### v16 — context 逻辑关系
- **来源**: 跨领域实战 agent
- `any` / `all` 显式 OR/AND
- 纯数组默认 OR

### v17 — 标准事件枚举 + 弃用 match
- **来源**: 技术可行性 agent
- 定义 9 个核心事件 + `custom:<name>` 扩展
- `match` 字段弃用，统一用 `globs`

### v18 — learned_from type 字段
- **来源**: 跨领域实战 agent
- `type: incident|observation|convention`
- 区分亲身经历、日常观察、行业共识

### v19 — 最小 pattern 降至 5 行
- **来源**: 可用性优化
- 只需 name + body 即可
- confidence 改为推荐但非必填

### v20 — 完整 trust policy 三级矩阵
- **来源**: 安全审查 agent
- local / verified / community 各有独立策略
- community 禁用 autonomous + 禁止命令执行

### v21 — 合并安全约束
- **来源**: 技术可行性 agent
- community confidence 上限 high（70-89）
- slug 冲突时 local/manual source 拒绝覆盖

### v22 — budget 裁剪策略优化
- **来源**: 跨领域实战 agent
- 裁剪顺序: severity → confidence（双维排序）

---

## 第三轮：v23 → v32（6 agent 深度审查 — 第二批）

### v23 — confidence 改为可选（默认 medium）
- **来源**: 用户可用性 agent
- **理由**: "强迫新用户在没有数据时做一个没有意义的判断"
- 必填字段从 2 个降到 1 个（只剩 name）
- 手动写的 pattern 不需要填 confidence
- 自动挖掘的 pattern 由算法填入

### v24 — category 改为数组，支持多标签
- **来源**: 跨领域实战 agent (两个)
- **理由**: 安全审查 pattern 既是 security 也是 code-review
- 向下兼容：单字符串仍然合法

### v25 — Pattern 级别 `scope` 字段
- **来源**: 跨领域实战 agent
- `scope: file | task | session | always`
- file = 基于当前文件激活（现有行为）
- task = 基于用户描述的任务激活（如"写博客"）
- session = 整个会话期间激活（如"深夜高产期"）
- always = 每次注入（全局规范类）

### v26 — Pattern 级别 `tools` 权限声明
- **来源**: 竞品对标 agent（排名第1建议）
- `tools: [read, search]` 或 `permissions: readonly|readwrite|execute|full`
- 安全模型的基石：community pattern 必须声明权限
- 没有 tools 声明的 community pattern 默认 readonly

### v27 — Pattern 参数化 `{{params}}`
- **来源**: 竞品对标 agent（排名第3建议）
- frontmatter 增加 `params` 声明参数
- 正文使用 `{{params.xxx}}` 占位符
- workflow 中通过 `with:` 传参

### v28 — Workflow 数据流（inputs/outputs）
- **来源**: 竞品对标 agent（排名第2建议）
- 步骤增加 `id`、`outputs`、`inputs` 字段
- `{{ steps.<id>.outputs.<name> }}` 引用语法
- 从"批量触发"升级为"真正编排"

### v29 — 命名空间 `@scope/name`
- **来源**: 竞品对标 agent（排名第5建议）+ 社区生态 agent
- `name: "@liyufeng/ml-research-workflow"`
- 社区规模化的基础设施

### v30 — 快速上手文档结构重组
- **来源**: 用户可用性 agent
- spec 顶部增加"30 秒理解 + 5 分钟上手"章节
- 进阶内容（JSON 交换格式、合并策略、版本演进）移到后半部分
- 第一个示例改为最简 pattern（3 行）

### v31 — evidence 字段 source-aware 规则
- **来源**: 跨领域实战 agent + 用户可用性 agent
- `source: auto` → evidence 必填（挖掘工具填入）
- `source: manual` → evidence 可选（不填也合法）
- 解决"手写 pattern 硬编 evidence 数字毫无意义"的问题

### v32 — 一句话价值主张 + elevator pitch
- **来源**: 社区生态 agent
- spec 开头增加: "把你的编程习惯打包成文件，让任何 AI 工具直接理解你的风格"
- 英文版: "Package your coding habits into files that any AI tool can understand"

---

## 第四轮：v33 → v35（3 agent 深度审查 — 质疑+体验+实战）

> 时间: 2026-03-20 | 方法: 3 个 agent 并行审查（质疑者、用户体验、实战验证 6 个新领域 pattern）

### v33 — Pattern 间关系 + 注入决策矩阵
- **来源**: 质疑者 agent (P1-1) + 实战验证 agent (问题一)
- **新增 `requires`/`conflicts`/`related` 字段**: 声明 Pattern 间的依赖、互斥和关联
  - requires 不满足时 warning，不阻止注入
  - conflicts 同时激活时按 severity→confidence 保留高优先
  - related 仅供参考，不影响运行时
- **新增 severity × confidence 4×4 决策矩阵**: 明确 16 种组合的注入行为
  - critical + low confidence → 注入但强标注⚠️（不能静默忽略安全规则）
  - low severity + low confidence → 不注入
- **learned_from 内 `confidence` 重命名为 `reliability`**: 避免与 Pattern 顶层 confidence 字段同名不同类型的混淆
- **理由**:
  - 质疑者: "没有依赖图，多个 Pattern 同时激活时的合并语义未定义"
  - 实战验证: "CI 排查 pattern 和 Docker 优化 pattern 应该有关联，但无法表达"

### v34 — 语义 trigger OPTIONAL + 条件 AND 明确 + prerequisites
- **来源**: 质疑者 agent (P0-3) + 实战验证 agent (trigger 问题)
- **语义 trigger（步骤 3/4）显式标注为 [OPTIONAL]**: 不支持语义匹配的工具应只用 globs + event 做确定性匹配
  - 纯字符串 trigger 在不支持语义的工具中视为 `scope: always`
  - 不得静默丢弃含语义 trigger 的 pattern
- **trigger 条件间关系明确为 AND**: globs AND event AND (when AND context)
  - 解决实战中"globs 和 event 同时存在是 AND 还是 OR"的歧义
- **新增 `prerequisites` 字段**: 声明 Pattern 工作环境前置条件
  - 纯文本描述（"kubectl configured"），供人类和 AI 参考
  - 运行时不强制校验
- **learned_from 增加 `source_link` 字段**: 支持引用来源 URL
- **理由**:
  - 质疑者: "规范定义了一个没有任何实现者能完全遵守的核心特性"
  - 实战验证: "K8s pattern 需要表达环境前置条件但 spec 无字段"

### v35 — Pattern 有效性 + 工具集成指南 + 验证机制
- **来源**: 用户体验 agent (P0/P1) + 实战验证 agent (问题二)
- **新增 `valid_for` 字段**: 防止技术债务 pattern 积累
  - `min_version`: 最低版本要求（如 `{ react: "18.0" }`）
  - `expires`: 过期日期，到期后自动降级为 `confidence: low`
  - `last_verified`: 人工验证日期，超 12 个月发 warning
- **新增"工具集成"章节**: 解决"Step 3 黑盒"问题
  - 列出 Claude Code / Cursor / Copilot / 无插件方案的集成路径
  - 优先实现 `claw export` 生成兼容文件
- **新增 Pattern 生效验证方式**: 解决"aha moment 缺失"问题
  - `claw test <pattern>` 验证匹配
  - `claw status` 查看当前激活的 patterns
  - 最简验证教学：写"始终用中文回复" pattern → 英文提问 → 验证
- **理由**:
  - 用户体验: "写完 pattern 后，你怎么知道它生效了？这是最大的信任杀手"
  - 实战验证: "K8s API 版本弃用会让 pattern 过时，但没有任何字段表达有效期"

---

## 第四轮各 Agent 核心发现摘要

### 质疑者 agent — 10 个问题
**P0（致命）：**
1. severity/confidence 正交但无冲突决策机制 → v33 修复
2. Prompt Injection 防护缺失于规范层（注入隔离标签对 LLM 无强制力）
3. 语义 trigger 无可实现标准 → v34 修复

**P1（严重）：**
4. Pattern 间无依赖/冲突/继承关系 → v33 修复
5. 双格式策略（MD + JSON）可能是伪需求 — **存疑待议**
6. `{{params}}` 模板语法与 Vue/Jinja2/Helm 冲突 — **待后续解决**
7. scope:always 无 token 预算控制 — 已有 budget 机制，但需加 always_scope_cap

**P2（重要）：**
8. 合并策略粒度不足（只有文件级，缺字段级）
9. 无 Pattern 效果验证反馈回路 → v35 部分修复
10. permissions 是声明性的，无运行时强制力

### 用户体验 agent — 第一印象 5/10
**最严重问题：**
- 5 分钟上手 Step 3 完全是黑盒——AI 怎么读取？需要装什么？→ v35 修复
- 没有 "aha moment"——写完 pattern 不知是否生效 → v35 修复
- "为什么不直接用 CLAUDE.md"没讲清楚

**改善建议已采纳：**
- 工具集成指南 → v35
- 验证反馈机制 → v35
- severity 建议改名 priority → **暂未采纳**（severity 在安全/DevOps 领域语义更准确，改名需 breaking change）

### 实战验证 agent — 6 个新领域 pattern
**编写的 pattern：** CI Pipeline 排查、Docker 镜像优化、K8s 部署检查清单、React 组件拆分、CSS 性能优化、React Error Boundary

**发现的 8 个摩擦点：**
1. evidence 在 manual source 下不自然 → v31 已修复但表述需更清晰
2. permissions 四级枚举粒度不够（DevOps 需更细权限）
3. 缺少 prerequisites 字段 → v34 修复
4. 缺少 Pattern 间关系声明 → v33 修复
5. 缺少 valid_for 有效性管理 → v35 修复
6. 事件枚举缺 deploy_completed/alert_triggered/pr_opened 等
7. learned_from 中 confidence 与顶层字段同名混淆 → v33 重命名为 reliability
8. params 模板语法（条件渲染 `{{#if}}`）规范不完整

---

## 各 Agent 核心发现摘要

### 用户可用性 agent
- 最大问题: 没有 "aha moment"——写完 pattern 不知道有没有生效
- confidence 不应该是必填
- 需要 "5 分钟快速上手" 章节
- 手写模板和自动挖掘模板应该分离

### 竞品对标 agent (10 个竞品)
- TOP 1: Pattern 级别 tools 权限声明（安全基石）
- TOP 2: Workflow 数据流 inputs/outputs（真正编排）
- TOP 3: Pattern 参数化 {{params}}（复用前提）
- TOP 4: expected_output 输出规范（自动化基础）
- TOP 5: @scope/name 命名空间（生态规模化）
- ClawProfile 已领先竞品: confidence+evidence+evolution 体系、learned_from 溯源、trust 模型

### 技术可行性 agent
- P0 缺口: 运行时触发引擎完全不存在

---

## 第五轮：Shadow / Mirror / Brain / Autopilot 主链路迭代框架

> 时间: 2026-03-21 | 方法: 多 agent 架构审视 + 本机 skill/config 侧向对照

### 当前最大结构缺口
- Brain 目前主要还是“统计候选 + 语义润色”，还没有进入基于任务片段的行为机制建模
- Shadow 采集保留的是平面事件，不足以支撑高质量行为规范学习
- OpenClaw runtime 更像关键词匹配，不是策略选择
- ClawProfile 缺少证据账本，置信度增长不可审计
- Autopilot 的执行结果没有有效回灌到 Brain，闭环不完整

### 2-15 代总体路线
- 第 2-3 代：把 Shadow 从日志流升级成结构化行为原子和 Episode 切片
- 第 4-5 代：引入 Pattern Prototype 与 Evidence Ledger，先学原型再编译规则
- 第 6-9 代：建立特征图库、相似度判断和 Mirror 的规则形成可视化
- 第 10-13 代：Autopilot 执行回写，ClawProfile 分层，支持领域扩展包
- 第 14-15 代：引入夜间安全闸门和真正的 ClawProfile 操作系统化闭环

### 关键新增结构
- EventAtom：intent / tool / artifact / outcome / error_signature
- Episode：有目标的行为片段，而不是孤立事件
- PatternPrototype：带 preconditions / anti-patterns / expected outcomes 的原型层
- PatternEvidenceLedger：support / conflict / novelty / utility 账本
- WorkflowOutcomeLedger：下游 workflow 执行结果回写

### 本机生态可直接借鉴的模式
- provider catalog：复用 Claude Code / OpenClaw / Codex 本机 provider 与模型目录
- stateful review loop：借鉴 auto-review-loop 的“状态持久化 + 多轮改进”
- verification loop：每轮变更后做 build / type / diff / test 闸门

### 已接入的保守自动化
- 后端启动后会开启一个每小时一次的高层迭代审视任务
- 该任务只会把下一轮 ClawProfile 主链路设计记录写入本文件，不会在夜间无提示改代码
- P0 缺口: .claw/ 目录 Parser 不存在
- 贝叶斯更新单调递增无衰减
- trigger context DSL 是伪代码，无解析器
- JSON ↔ .md 双向转换有多个边界问题
- trust 自声明无签名验证
- slug 冲突静默覆盖

### 社区生态 agent
- 核心洞察: "自动生成是护城河"——claw init --auto 从 git log 生成第一个 profile
- 最大风险不是技术而是引导
- "Skill 的超集"定位要大声说
- 推荐命名: ClawDNA（与"行为基因组"类比一致）
- 先做 CLI 工具 + 10 个种子 profile，marketplace 后做

### 安全审查 agent (两个)
- 核心风险: "零转换注入"设计本身就是攻击面
- 5 种具体攻击: system override、数据窃取、trust 升级欺骗、inline 链式注入、打包投毒
- 当前防御覆盖不完整: allow_system_prompt 只防一种路径
- P0 修复: 注入隔离边界 + community 禁用 autonomous + unpack 强制扫描
- 建议区分 local_authored vs local_imported

### 跨领域实战 agent (两个)
- 5 个领域 pattern 实测: React/K8s/Pandas/安全审查/博客写作
- 最顺畅: 技术调试类（debug-reward 风格）
- 最别扭: 软技能/写作类（trigger 虚、learned_from 不自然）
- 缺少: severity、scope、tags(多标签)、prerequisites
- context 逻辑关系（AND/OR）不明确
- event 枚举范围缺失

---

## 第五轮：v36 → v38（3 agent 深度审查 — 质疑者+UX+互操作架构，2026-03-20）

### v36 — 价值主张强化 + 模板语法迁移 + MD 唯一源
- **来源**: UX agent + 质疑者 agent
- **变更**:
  1. 新增"为什么用 ClawProfile"章节：问题-解法对照表 + 三个杀手级用例
  2. 设计原则第 2 条改为"Markdown 是唯一源"（JSON 是导出格式）
  3. 模板语法从 `{{params}}` 迁移到 `<%%>`，解决与 Vue/Jinja2/Helm 的语法冲突
  4. 新增 ClawTemplate 最小规范：变量插值、条件渲染、列表迭代、步骤引用
  5. ClawTemplate 按 Conformance Level 分级：L0/L1 只需变量插值，L2+ 支持条件/循环
- **理由**: 质疑者指出 `{{params}}` 与主流模板语言冲突是已知问题 #1；UX 指出缺乏"为什么"叙事导致新用户 10 分钟内放弃

### v37 — ClawProfile 消费协议（CCP）
- **来源**: 互操作架构 agent
- **变更**:
  1. 新增 §4.1 Discovery 发现机制：三级优先级扫描（项目 > 用户 > 远程依赖）
  2. 新增 §4.2 Injection 注入协议：6 步标准流程（触发→关系→裁剪→排序→隔离→注入）
  3. 新增 §4.3 Ordering 6 维排序算法：scope > severity > confidence > trust > specificity > declaration_order
  4. 新增 §4.4 Conformance Levels：L0 声明式 → L1 触发式 → L2 模板式 → L3 完整式
- **理由**: 互操作架构 agent 指出"规范定义了格式但不定义消费方式"是跨工具不一致的根源；L0/L1 分级解决"最低门槛太高导致无人实现"

### v38 — Params 安全 + 运行时约束 + 事件扩展 + 字段级合并
- **来源**: 质疑者 agent + 互操作架构 agent
- **变更**:
  1. Params 安全增强：`sensitive` 标记（日志/导出 mask）、`enum` 枚举约束、`min`/`max` 数值范围、注入前 sanitization
  2. `always_scope_cap`：限制 always pattern 数量（默认 10）和 budget 占比（默认 50%）
  3. 事件枚举从 9 个扩展到 15 个：新增 build_succeeded、test_passed、deploy_completed、pr_opened、pr_merged、file_deleted、alert_triggered
  4. 字段级合并策略 `--strategy=field-merge`：按字段语义智能合并（confidence 取高、category 取并集等）
- **理由**: 质疑者指出 params 注入是潜在安全漏洞（尤其 community pattern）；always_scope_cap 解决已知问题 #5；事件枚举扩展解决已知问题 #3

## 第五轮各 Agent 核心发现摘要

### 质疑者 agent
- 解决了 v35 遗留的全部 7 个已知问题：params 语法冲突、permissions 声明性、事件枚举不足、合并策略粒度、always_scope_cap、params 条件渲染、双格式价值
- 发现 3 个新深层问题：
  1. FQN 全局身份（`<registry>/<namespace>/<name>@<version>`）未规范化
  2. Params 注入安全（community pattern 可通过 params 注入恶意内容）
  3. 依赖锁定机制（claw.lock）缺失

### UX agent
- 写了"为什么用 ClawProfile"叙事，将 UX 评分从 5/10 提升到预期 7.5/10
- 三个杀手级用例：个人习惯便携化、团队规范标准化、社区共享生态
- 强调 MD 作为唯一源的简化效果

### 互操作架构 agent
- 设计了完整的消费协议（CCP），解决"Step 3 黑盒"问题
- 4 级 Conformance Level 让不同能力的工具都能参与
- 6 维排序算法确保多 Pattern 激活时行为确定性

---

## 第六轮：v39 → v41（3 agent 深度审查 — 质疑者+UX+实战验证，2026-03-20）

> 时间: 2026-03-20 | 方法: 3 个 agent 并行审查（质疑者 11 个问题、UX 评分 5.5/10、实战验证 2 个新领域 pattern）

### v39 — 内部一致性修复 + scope 语义修正
- **来源**: 质疑者 agent (P0-1, P2-9) + 实战验证 agent (摩擦点 2, 3)
- **变更**:
  1. **JSON 示例 learned_from.confidence 修正为 reliability**（P0 级内部矛盾：v33 重命名了 frontmatter 但漏改 JSON 示例）
  2. **scope 默认值智能推导**：有 globs → file，有 event 无 globs → task，无 trigger → always（修复"无 trigger + 默认 file = 死代码"）
  3. **scope × trigger 交互矩阵**：明确 task scope 忽略 globs、session scope 仅响应 session_started 事件、always scope 忽略所有 trigger
  4. **confidence 语义分流**：auto = 观察频率，manual = 建议正确性自信度，imported = 继承（解决手写 pattern 不知怎么填 confidence 的困惑）
- **理由**:
  - 质疑者: "JSON 示例和 frontmatter 规范字段名不一致，任何实现者都会做错"
  - 实战验证: "scope: task 下 globs 还有意义吗？规范完全沉默"

### v40 — ClawTemplate 补全 + 安全加固 + 合并安全
- **来源**: 实战验证 agent (摩擦点 1) + 质疑者 agent (P0-2, P1-3, P2-7)
- **变更**:
  1. **ClawTemplate 完整语法**：补充比较运算符（==, !=, >, <, >=, <=）、逻辑运算符（and, or, not）、嵌套条件规则
  2. **隔离标签 nonce 安全加固**：每次注入生成随机 8 位 nonce 作为标签名一部分，防止 body 中注入 `</pattern-context>` 绕过隔离
  3. **field-merge 安全原则**：影响运行时行为的字段（confidence/severity/expires）保留本地值，只有纯信息字段（category/learned_from）取并集
  4. **sensitive 参数职责限定**：明确 Pattern 不承担密钥管理，sensitive 仅防泄露，推荐通过环境变量传入
  5. L0 工具遇到模板控制结构应原样保留为文本，不静默删除
- **理由**:
  - 实战验证: "想写 `<% if params.level == 'AAA' %>`，规范不说支不支持比较运算符"
  - 质疑者: "pattern body 可包含 `</pattern-context>` 提前关闭隔离边界"
  - 质疑者: "field-merge 的 confidence 取较高值可被远程 pattern 利用来提升注入优先级"

### v41 — CCP 排序调整 + 枚举扩展 + 文档结构
- **来源**: 质疑者 agent (P2-11) + 实战验证 agent (摩擦点 5, 7) + UX agent (文档结构)
- **变更**:
  1. **CCP 排序调整**：severity 提升到第 1 维（重要性比范围更应决定优先级），scope_priority 方向反转为 file > always（利用 LLM recency bias，精确匹配 pattern 更靠近用户消息）
  2. **learned_from.type 扩展**：增加 `documentation`（来自官方文档）和 `standard`（来自 RFC/WCAG 等标准）
  3. **min_level 字段**：Pattern 声明最低一致性等级要求（默认 L0），低于此等级的工具跳过此 pattern 而非损坏注入
  4. **文档三部分结构指引**：Part 1 用户指南 / Part 2 完整参考 / Part 3 实现者规范
- **理由**:
  - 质疑者: "范围越大越优先注入，但 LLM 上下文中后注入的内容影响力更大"
  - 实战验证: "learned_from.type 只有 3 种，无法表达'来自 WCAG 标准'或'来自 Terraform 官方文档'"
  - UX: "文档混合了用户指南和实现规范，开发者看到决策矩阵和 CCP 协议就放弃了"

## 第六轮各 Agent 核心发现摘要

### 质疑者 agent — 11 个问题
**P0（致命）：**
1. JSON 示例 learned_from 字段名与 frontmatter 不一致 → v39 修复
2. 隔离标签可被 `</pattern-context>` 注入绕过 → v40 nonce 修复

**P1（严重）：**
3. `sensitive: true` 参数与"零转换注入"原则矛盾 → v40 职责限定
4. Workflow 数据流缺运行时语义（outputs 如何从 AI 回复中提取） — **架构级待解决**
5. token budget 计算方式未定义（哪个 tokenizer？计量范围？）— **待解决**

**P2（重要）：**
6. L0-L3 跨度过大，L0 工具看到原始模板文本 → v41 min_level 缓解
7. field-merge confidence/severity 取较高值可被利用 → v40 安全修正
8. prerequisites 与 valid_for.min_version 职责重叠 — **待后续合并**
9. 默认 scope file + 无 trigger = 死代码 → v39 修复
10. v27 变更日志中 `{{params}}` 旧语法需勘误说明 — **低优先**
11. 排序方向反直觉 → v41 修复

### UX agent — 评分 5.5/10（体验时间估计 30-45 分钟）
- **致命问题**：所有工具集成"规划中"，CLI 不存在，"5分钟上手"第3步不可能完成
- **核心建议**：先实现 `claw export --target claude`，文档拆分用户指南/实现规范
- **概念过载**：28+ 概念，建议入门只需 name/trigger/severity 三个字段
- **"为什么不用 CLAUDE.md"回答力度不足**：价值主张依赖不存在的生态
- 文档结构指引 → v41 采纳

### 实战验证 agent — 2 个新领域 pattern（Terraform + React a11y）
- **编写了完整的 Terraform State 安全规范 pattern**（critical severity, task scope, 3 个 learned_from）
- **编写了完整的 React a11y 检查 pattern**（high severity, file scope, 含 ClawTemplate 条件渲染）
- **12 个摩擦点**：ClawTemplate 语法不足(红)、scope×trigger 交互未定义(红)、confidence 语义模糊(红)、自定义事件缺规范(黄)、learned_from.type 枚举太窄(黄)、prerequisites 重叠(黄)、CCP 排序假设错误(黄)、缺标准 category 词汇表(黄)

---

## 第七轮：v42 → v44（3 agent 深度审查 — 质疑者+UX+实战验证，2026-03-21）

> 时间: 2026-03-21 | 方法: 3 个 agent 并行审查（质疑者 13 个问题、UX 评分 5.0/10、实战验证 2 个新领域 pattern）

### v42 — budget 标准化 + body 裁剪策略 + 安全要求分层
- **来源**: 质疑者 agent (P0-2, P0-3) + 实战验证 agent (R1)
- **变更**:
  1. **budget 标准计量方式**：新增 `budget_unit`（默认 `chars` 即 UTF-8 字符数，跨 tokenizer 一致）、`budget_scope`（默认 `body` 仅计量正文）、`budget_tokenizer`（使用 tokens 时的参考 tokenizer）
  2. **body 裁剪策略**：超长 pattern 按 Markdown heading 分段保留高优 sections，仍超长则截断并附 `[TRUNCATED]` 提示。新增 `truncation: deny` frontmatter 字段，安全类 pattern 可声明"宁可不注入也不要截断"
  3. **安全要求按一致性等级分层**：L0 不要求隔离标签但仅限 local trust；L1+ 必须实现隔离标签；L0 不得消费 community/verified pattern
- **理由**:
  - 质疑者: "budget 2000 用什么 tokenizer？同一 budget 在不同工具上行为完全不同"
  - 质疑者: "L0 原样注入与安全规范的'必须添加隔离边界'直接矛盾"
  - 实战验证: "database-migration-safety 约 800-1000 tokens，不知 budget 超出时是整体移除还是截断"

### v43 — tools/permissions 互斥 + 分工明确 + min_level 行为 + specificity 量化
- **来源**: 质疑者 agent (P1-1, P1-3, P1-4, P1-5)
- **变更**:
  1. **tools 与 permissions 互斥**：同一 pattern 不得同时声明两者，解析器遇到同时存在时报错
  2. **prerequisites 与 valid_for.min_version 分工明确化**：prerequisites 用于不可机器校验的环境状态，min_version 用于可量化的版本号约束
  3. **min_level 运行时行为定义**：工具等级低于 min_level 时仍注入但追加提示语，不得静默跳过
  4. **specificity 量化计分**：globs +1, event +1, when +1, context +1，总分 0-4，解决排序第 5 维"无法跨工具一致计算"
- **理由**:
  - 质疑者: "tools 和 permissions 同时存在时以哪个为准？"
  - 质疑者: "min_level 没有运行时语义就是死代码"
  - 质疑者: "specificity 的'条件越多越优先'无法量化"

### v44 — 零依赖上手 + frontmatter 分级 + category 词汇表 + 自定义事件规范
- **来源**: UX agent (问题 1, 2, 4) + 实战验证 agent (Y1, Y3)
- **变更**:
  1. **零依赖上手路径**：5 分钟上手 Step 3 改为 `cat patterns/*.md >> CLAUDE.md`（今天就能用，不依赖任何 CLI），提供方案 A/B 两种路径
  2. **frontmatter 三级分层展示**：入门字段（name/severity/confidence/category/trigger）、进阶字段、工具字段，物理分离
  3. **category 推荐词汇表**：提供 18 个标准分类词汇（debugging、security、api 等），非强制但推荐
  4. **自定义事件命名规范**：定义 `custom:<scope>.<event_name>` 格式、命名规则（kebab-case/snake_case，仅 `[a-z0-9_-]`，最长 64 字符）、profile.yaml 注册声明、触发方式
  5. **价值主张强化**：新增"为什么不直接用 CLAUDE.md"的诚实回答——承认单工具场景 CLAUDE.md 够用，给出"今天就有价值"的理由（文件组织优于单文件管理）
- **理由**:
  - UX: "用户在第 5 分钟必须看到 pattern 真正影响了 AI 的行为，cat >> CLAUDE.md 是那条生命线"
  - UX: "28+ 字段平铺，新用户无法区分'必须看'和'以后再说'"
  - 实战验证: "自定义事件 custom:<event-name> 只有一行提及，没有命名规范和触发机制"

## 第七轮各 Agent 核心发现摘要

### 质疑者 agent — 13 个问题
**P0（致命）：**
1. Workflow outputs 运行时提取协议完全未定义 — **架构级待解决**
2. token budget 计量单位和范围未标准化 → v42 修复
3. 安全隔离要求与 L0 一致性等级矛盾 → v42 修复

**P1（严重）：**
4. prerequisites/min_version 职责重叠 → v43 分工明确
5. 自定义事件缺命名规范和注册机制 → v44 修复
6. min_level 运行时行为未定义 → v43 修复
7. tools/permissions 同时存在优先级未定义 → v43 互斥约束
8. specificity 排序维度缺量化定义 → v43 计分规则

**P2（重要）：**
9. 缺标准 category 分类词汇表 → v44 推荐词汇表
10. FQN 全局身份未规范化 — **待解决**
11. claw.lock 依赖锁定未定义 — **待解决**
12. ClawTemplate for 循环语法不完整 — **待解决**
13. always 降级为 session 的语义矛盾 — **待解决**

### UX agent — 评分 5.0/10
- **致命问题**：Step 3 黑盒（用户创建 pattern 后无法让它生效） → v44 零依赖路径修复
- **概念过载**：28+ 字段平铺，入门应只需 5 个字段 → v44 frontmatter 分级修复
- **文档三部分结构声称存在但无物理分隔** — 部分修复
- **价值主张弱点**：优势全建立在未来功能上 → v44 "今天就有价值"修复
- **渐进式学习路径断层** — 待下轮改进

### 实战验证 agent — 2 个新领域 pattern（数据库迁移安全 + API 版本管理）
- **编写了 database-migration-safety pattern**（critical severity, task scope, 3 个 learned_from, execute 权限）
- **编写了 api-version-management pattern**（high severity, file scope, 含 ClawTemplate 条件渲染 + params 参数化）
- **2 个红色摩擦点**：body 超长裁剪策略未定义(→v42)、pattern 自身不能声明 outputs(待解决)
- **6 个黄色摩擦点**：自定义事件(→v44)、prerequisites 重叠(→v43)、category 无词汇(→v44)、learned_from.type 边界模糊、params default 哲学冲突、FQN 解析规则未定义
- **8 个绿色顺畅点**：frontmatter 整体好、trigger 表达力够、决策矩阵直觉、learned_from 优秀、ClawTemplate 无冲突、scope 推导合理、related/conflicts 顺畅、valid_for 实用

---

## 第八轮：3 agent 深度审查（v45-v47, 2026-03-21）

**起始版本**：v44 → **结束版本**：v47

### 质疑者 agent — 稳定性评估 + 11 个问题

**稳定性评估**：
- Pattern 定义层（frontmatter/body/trigger/scope）→ ~成熟，变更速率下降
- 编排层（workflow/for 循环/FQN/outputs）→ ~不成熟，仍有架构级缺口

**P0（阻断级）：**
1. Workflow outputs 运行时提取语义缺失 — **待解决**（架构级）
2. always 降级为 session 后可能变成死代码 → **v45 修复**（_original_scope 标记 + 自动恢复）
3. for 循环语法不完整（迭代变量、空列表、作用域） → **v45 修复**（EXPERIMENTAL 标注 + 语法完善）

**P1（高优先）：**
4. Pattern 自身不能声明 outputs → **v46 修复**（outputs 字段 + extract 提取方式）
5. FQN 全局身份未规范化 — **待解决**
6. claw.lock 依赖锁定机制缺失 — **待解决**
7. learned_from.type 边界模糊（documentation vs standard vs convention） — **待解决**

**P2（重要）：**
8. 自定义事件 scope 来源模糊 — **待跟踪**
9. budget_unit tokens ±20% 容差过松 — **待跟踪**
10. Changelog 在 spec 中越来越长 — **待跟踪**（v47 预告未来拆分）
11. category 词汇表缺扩展机制 — **待跟踪**

### UX agent — 评分 6.5/10（↑1.5）

**核心洞察**："问题在于呈现而非内容"——规范内容已足够好，但文档组织需要改进

**TOP 5 改进建议**：
1. 文档应物理拆分为 QUICKSTART.md（~150行）+ SPEC + CCP → **v47 部分修复**（添加 `<!-- PART N -->` 标记 + 未来拆分预告）
2. Part 1 内容顺序需调整（profile.yaml 太早出现） — **待下轮**
3. 最小 profile.yaml 示例 → **v47 修复**（3 字段即可）
4. 中级学习路径示例缺失 — **待下轮**
5. 价值主张措辞可进一步强化 — **待下轮**

### 实战验证 agent — 2 个新领域 pattern + v42-v44 功能验测

**编写了 structured-logging-standards pattern**（high severity, always scope, category: [logging, observability]）
**编写了 pr-review-process pattern**（medium severity, task scope, category: [review, collaboration]）

**v42-v44 功能验测结果**：
- `truncation: deny` — 实用，但跳过时缺通知 → **v45 修复**
- `budget_unit: chars` — 直觉、跨工具一致、实用
- `category 推荐词汇表` — 缺 logging/observability/compliance → **v46 修复**

**红色摩擦（3 个）**：
1. Pattern outputs 功能缺口 → **v46 修复**
2. truncation:deny 跳过无感知 → **v45 修复**
3. for 循环迭代变量未定义 → **v45 修复**

**黄色摩擦（4 个）**：
1. category 缺运维类词汇 → **v46 修复**
2. learned_from.type 边界模糊 — 待解决
3. FQN 解析规则未定义 — 待解决
4. 文档查找特定内容困难 → **v47 部分修复**

### 本轮解决的已知问题

| # | 问题 | 解决版本 |
|---|------|---------|
| 4 | ClawTemplate for 循环语法不完整 | v45（EXPERIMENTAL + 语法完善） |
| 5 | always→session 降级语义矛盾 | v45（_original_scope + 自动恢复） |
| 6 | Pattern 自身不能声明 outputs | v46（outputs 字段） |

### 新增/更新的已知问题

| # | 问题 | 优先级 | 状态 |
|---|------|--------|------|
| 1 | Workflow outputs 运行时提取语义 | P0 | 待解决（架构级） |
| 2 | FQN 全局身份规范化 | P1 | 待解决 |
| 3 | claw.lock 依赖锁定 | P1 | 待解决 |
| 4 | learned_from.type 边界定义 | P1 | 待解决 |
| 5 | 文档物理拆分为 3 文件 | P1 | v47 预告，待实施 |
| 6 | 自定义事件 scope 来源精确化 | P2 | 待跟踪 |
| 7 | budget_unit tokens 容差收紧 | P2 | 待跟踪 |
| 8 | Changelog 独立文件 | P2 | 待跟踪 |

# DevTwin 开发会话记录 — 2026-04-03

## 会话概要

本次会话完成了 DevTwin 项目的全面分析、规划和 10 代迭代改进。

---

## 一、项目分析阶段

### 1.1 项目结构分析
- 技术栈: Vue 3 + TypeScript + Vite 8 + Tailwind v4 + Pinia + d3 (前端) / Python 3.11+ + FastAPI + SQLAlchemy 2 + Anthropic SDK (后端)
- 架构: 前端 localhost:5173 → Vite API 代理 → 后端 localhost:7891 → SQLite
- 33 个服务文件, 16 个路由模块, 15+ 页面

### 1.2 项目意义分析
- 核心命题: 从"记忆"到"认知" — AI 不只记得你做过什么，而是知道你怎么思考
- 三层价值: 个人(编码习惯便携化) → 工程(行为模式可版本化) → 生态(认知社区共享)
- 独特性: 在"认知建模 + 可执行规范"交叉点无直接竞品

### 1.3 竞争格局
| 竞品 | 做什么 | 与 DevTwin 的差异 |
|------|--------|-------------------|
| Mem0 (48k star) | 通用 AI 记忆层 | 做记忆检索(what), DevTwin 做认知建模(how) |
| Vibe Coding Profiler | Git 行为分析 | 只做可视化报告, 不生成可执行规范 |
| CatchMe | 活动记忆回放 | 做"你做过什么", 不做"你怎么思考" |
| RuleForge | 模板化规则生成 | 静态扫描, 无行为学习 |
| CodeMem / Codevira | 持久记忆 | 基础设施层, 不做认知建模 |

### 1.4 开源可行性
- ClawProfile 规范 v53 成熟度高, 可独立开源
- 阻塞项: _snapshot.json 含真实 API key (已在 Gen 6 修复), README 为占位 (已在 Gen 8 修复), 无 LICENSE (已在 Gen 9 添加)

### 1.5 投资人视角
- 市场时机: Agentic AI $60亿(2025) → $1360亿(2035), 37% CAGR
- 定位: 不是平台层也不是基础设施层, 而是"认知建模 + Skill 编排层"(空白市场)
- Pitch: "Cursor 让 AI 写代码，DevTwin 让 AI 像你一样写代码"
- 收入模型: 本地免费 + Cloud 同步 $9/月 + 团队品味继承 $29/人/月

---

## 二、用户四大长期方向（最高宗旨）

> 每次讨论 DevTwin 计划时必须带上这四个方向。

1. **Skill Workflow 挖掘**: 用户使用 skill 时的 CoT 调用模式和人为调用方式, 作为数据让模型总结 skill 组合的 workflow
2. **Skill 发掘与推荐**: 结合用户反馈、会话数据和开源 skill 生态, 帮用户发现相关/进阶的 skill 库
3. **人参与的行为建模**: 纯自动从交互中挖规范太嘈杂, 需要人的参与(如已配好的 skill 库)作为高质量数据源
4. **Claw the Claw 自主体**: 学习用户的工作习惯和使用 Claw 的习惯, 让 agent 代替人的品味来指挥 Claw 干活

四层进化逻辑: 人手动配 skill → 从用法挖 workflow → 结合开源推荐新 skill → agent 自主指挥 Claw

核心洞察: 纯自动行为挖掘太嘈, 已配好的 skill 库本身是最好的高质量数据源。

---

## 三、核心闭环改进（Plan 1 — 已完成）

### 改进项
1. **P0 飞轮可证明性 (V8)**: 新增 `GET /stats/flywheel-trend` + d3 折线图, 替换 Twin 页静态数字
2. **P1 拒绝反馈闭环 (V4)**: `rejectPatternApi` 支持 reason 参数 + 拒绝原因输入 UI (4 个 preset + 自由文本)
3. **P2 演化时间轴 (V7)**: 点击 pattern 展开 evolution 迷你折线图 (d3 绘制, 节点按事件着色)
4. **P3 证据溯源 (V3)**: CLAUDE.md 导出每条规则下附加 `<details>` 证据脚注

---

## 四、10 代迭代改进（Plan 2 — 已完成）

### Gen 1: 全局扫描 + 快速修复
- 10 个 agent 并行分析 (前端UI/数据流/后端路由/服务/模型/安全/性能/文档/规范/功能)
- 发现 ~45 项问题
- 修复: 6 个服务文件 14 处 JSON 解析安全化, .gitignore 补全, host 改 127.0.0.1

### Gen 2: 管线修复 + 方向1基础
- cot_miner → InvocationLog 打通 (selector_type='cot')
- workflow_inferrer → Skill 表匹配 (matched_skills + skill_coverage)
- reject reason → taste_model 聚合进 taste_summary

### Gen 3: 功能补全 + 方向1核心
- Autopilot 页面 workflow 创建接入真实 API
- Mirror 页面画像从写死改为 computed
- 新增 SkillWorkflow 模型 + 持久化 + GET /skills/workflows/mined API

### Gen 4: 数据流 + 方向2基础
- 5 个 Store 添加 error/loading + try/catch
- 新增 getMinedWorkflowsApi + SkillWorkflowItem 类型
- Skill 页面新增 "Skill Workflow 挖掘" 面板

### Gen 5: 方向2核心
- skill_discovery.py 接入 GET /skills/discovery API
- taste_model 接入 skill_recommender (偏好类别 +10, 拒绝主题 -8)
- InvocationLog slug 归一化 (_name_to_slug)

### Gen 6: 安全 + 方向3
- import_skills_as_patterns(): 本地 skill 库 → BehaviorPattern (status=learning)
- POST /skills/import-from-library API
- _snapshot.json 替换为合成数据 (删除 67,000+ 行含 API key 数据)

### Gen 7: 方向4基础
- Taste 驱动调度器: preferred_categories 影响挖掘, confidence_threshold 影响自动确认
- record_task_preference(): 追踪用户触发/跳过哪些任务
- get_preferred_task_schedule(): 分析习惯, 计算任务偏好分

### Gen 8: 方向4核心
- README.md 重写 (从 Vue 占位到完整项目文档)
- suggest_autonomous_tasks(): 品味驱动的自主任务建议系统
- GET /agent-taste/autonomous-suggestions API
- 建议安全 (只建议不执行, 用户需批准)

### Gen 9: 集成验证
- 发现 4 个方向的集成断裂点并修复:
  - 方向1: CoT 后自动调 mine_skill_workflows + 降低短序列阈值
  - 方向2: 技能发现结果在推荐 tab 展示
  - 方向3: 导入 pattern 改为 learning 状态进入确认队列
  - 方向4: Brain 页面展示自主任务建议卡片
- 添加 MIT LICENSE

### Gen 10: 最终验证
- TypeScript: PASS
- Python: PASS
- 无回归

### 最终状态
| 方向 | 完成度 |
|------|--------|
| 方向1: Skill Workflow 挖掘 | 95% |
| 方向2: Skill 发掘推荐 | 90% |
| 方向3: 人参与闭环 | 85% |
| 方向4: Claw 自主体 | 70% |

---

## 五、新增 API 端点汇总

| 端点 | 方法 | 用途 |
|------|------|------|
| `/stats/flywheel-trend` | GET | 飞轮时间序列 |
| `/skills/workflows/mined` | GET | 挖掘出的 Skill Workflow |
| `/skills/discovery` | GET | 本地 Skill 库发现 |
| `/skills/import-from-library` | POST | Skill 库导入为 Pattern |
| `/agent-taste/autonomous-suggestions` | GET | 自主任务建议 |

---

## 六、Git 提交记录

```
5ca3df8 docs: Gen 10 - Final verification report
8999666 feat: Gen 9 - Integration fixes + code cleanup
a167b96 feat: Gen 8 - Documentation + Autonomous Claw Agent
f6b1314 feat: Gen 7 - Taste Model expansion
05c821d feat: Gen 6 - Security + Human-in-loop
f7b3a20 feat: Gen 5 - Direction 2 core
206aa78 feat: Gen 1-4 iterative improvements
```

---

## 七、下一步建议

1. 远程 Skill 源: 接入 GitHub/ClawHub skill 仓库
2. 推荐反馈: skill 推荐添加"有用/忽略"闭环
3. 自主执行: 从"建议"升级为"批准后自动执行"
4. API 认证: 写操作添加 Bearer token
5. Git 历史清理: git filter-repo 移除旧密钥

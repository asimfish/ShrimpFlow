

## 第 2 代：Shadow 结构化事件抽取

- 时间: 2026-03-21 03:50:15
- 核心焦点: 把原始事件升级成包含 intent/tool/artifact/outcome/error_signature 的行为原子。
- 当前快照: events=3570, sessions=225, patterns=71, workflows=9, shared_profiles=9
- 本轮目标:
  - 新增 EventAtom 层而不是继续只看 action 文本
  - 把 command family / error signature / artifact ref 作为统一字段采集
  - 为后续 Episode 切分准备 task_hint 和 outcome 标签
- 完成状态: 已实现 models/episode.py (EventAtom 模型) + services/event_atom_extractor.py

## 第 3 代：Shadow 到 Episode 切片

- 时间: 2026-03-21 14:00:00
- 核心焦点: 从事件流切出有目标的任务片段，而不是直接统计共现。
- 本轮目标:
  - 定义 Episode 边界和 task-level success label
  - 把 session / project / artifact 关联进同一任务片段
  - 为 Brain 提供任务推进片段而不是孤立日志
- 完成状态: 已实现 models/episode.py (Episode 模型) + services/episode_slicer.py

## 第 4 代：Brain 深层挖掘

- 时间: 2026-03-21 14:00:00
- 核心焦点: 基于 Episode 提取可操作的行为规范，而非浅层统计。
- 本轮目标:
  - 工作流习惯挖掘: 固定的工具切换序列
  - 错误恢复模式: 遇到错误后的典型修复路径
  - 质量关卡: 提交前的检查习惯
  - 工具偏好: 特定场景下的工具选择
  - AI 深度语义精炼: when/do/expect/anti_pattern 可执行规范
- 完成状态: 已实现 services/deep_mining.py + routes/episodes.py + 集成到 collector 流水线

## 第 5 代：Evidence Ledger 账本

- 时间: 2026-03-21 14:02:55
- 核心焦点: 把每次模式置信度变化变成可审计账本。
- 本轮目标:
  - 记录 support / conflict / novelty / utility 四类证据
  - 让 confidence 更新不再只是 occurrence 累加
  - 支持解释"为什么这条规范变强/变弱"
- 完成状态: 已实现 models/feature_graph.py (EvidenceLedger 模型) + services/evidence_ledger.py + 贝叶斯更新 + 前端可视化

## 第 6 代：Feature Graph + Session Mining + 有意义性判断

- 时间: 2026-03-21 15:00:00
- 核心焦点: 三维度深化行为模式提取能力，使系统真正能从用户数据中提炼有效行为规范。
- 本轮目标:
  - Feature Graph 特征图谱: EpisodeFeature + FeatureEdge 图结构，余弦相似度计算，7种行为原型聚类
  - OpenClawSession 对话挖掘: 从AI对话内容中提取协作偏好/技术栈/问题解决风格/使用模式
  - 有意义性判断 (is_meaningful_rule): 6项检查过滤无价值模式，conflict证据自动降权
  - Evidence Ledger 集成: deep_mining/session_mining/pattern_confirm 全链路证据记录
  - AI 默认供应商优先级调整: aipor 优先于 office3
- 完成状态: 已实现
  - models/feature_graph.py (EpisodeFeature + FeatureEdge + EvidenceLedger)
  - services/feature_graph.py (图谱构建 + 原型聚类 + 相似度边)
  - services/session_mining.py (对话信号提取 + 技术栈偏好 + 问题解决模式 + AI精炼)
  - services/evidence_ledger.py (四类证据 + 贝叶斯更新 + 有意义性判断 + 过滤)
  - 前端 brain_page.vue (Feature Graph + Evidence Ledger 可视化)
  - collector 流水线完整集成: Shadow→Atom→Episode→DeepMining→SessionMining→FeatureGraph→EvidenceLedger→MeaningfulFilter→Push


## 第 7 代：相似度与去重

- 时间: 2026-03-21 16:56:30
- 核心焦点: 把新增证据和旧原型进行稳健比对，减少杂乱规则。
- 当前快照: events=3603, sessions=255, patterns=78, workflows=9, shared_profiles=9
- 本轮目标:
  - 先做硬过滤，再做结构相似，最后做语义相似
  - 让重复证据合并到旧原型而不是继续长新规则
  - 显式处理冲突证据和反例
- 备注: 这是自动化的高层迭代审视记录，不会在夜间无提示修改代码。


## 第 8 代：ClawProfile 编译器

- 时间: 2026-03-21 18:00:18
- 核心焦点: 把 prototype 编译成可注入、可执行、可维护的 ClawProfile 单元。
- 当前快照: events=3605, sessions=255, patterns=78, workflows=9, shared_profiles=9
- 本轮目标:
  - 输出 when/scope/evidence/strategy/expected outcome/failure mode
  - 为 Autopilot 工作流提供可编排步骤
  - 保留原型与编译产物之间的映射
- 备注: 这是自动化的高层迭代审视记录，不会在夜间无提示修改代码。


## 第 9 代：Mirror 反馈增强

- 时间: 2026-03-21 23:26:22
- 核心焦点: 让 Mirror 不只是展示数据，而是展示规则形成过程。
- 当前快照: events=3605, sessions=255, patterns=78, workflows=9, shared_profiles=9
- 本轮目标:
  - 可视化 prototype 到 ClawProfile 的演化链路
  - 显示证据账本和冲突记录
  - 让用户能审查为什么某条规范存在
- 备注: 这是自动化的高层迭代审视记录，不会在夜间无提示修改代码。


## 第 10 代：Autopilot 执行回写

- 时间: 2026-03-22 01:00:34
- 核心焦点: 让下游 workflow 的执行结果回灌到 Brain。
- 当前快照: events=3605, sessions=255, patterns=78, workflows=9, shared_profiles=9
- 本轮目标:
  - 记录 workflow step success/failure/override
  - 把 usefulness 写回 PatternEvidenceLedger
  - 建立从相关性到有效性的升级路径
- 备注: 这是自动化的高层迭代审视记录，不会在夜间无提示修改代码。


## 第 11 代：ClawProfile 分层

- 时间: 2026-03-22 02:00:34
- 核心焦点: 把规则分成核心层、领域层、项目层、个人层。
- 当前快照: events=3605, sessions=255, patterns=78, workflows=9, shared_profiles=9
- 本轮目标:
  - 支持 profile overlays
  - 避免规则仓库越长越乱
  - 让下游 workflow 可以按层选用规则
- 备注: 这是自动化的高层迭代审视记录，不会在夜间无提示修改代码。


## 第 12 代：可维护置信度机制

- 时间: 2026-03-22 03:08:23
- 核心焦点: 把 support/diversity/utility/conflict/staleness 纳入统一分数。
- 当前快照: events=3641, sessions=257, patterns=82, workflows=9, shared_profiles=9
- 本轮目标:
  - 实现多因子 confidence 更新
  - 支持 stale rule 自动衰减
  - 支持 utility 高但证据少的人工保留规则
- 备注: 这是自动化的高层迭代审视记录，不会在夜间无提示修改代码。


## 第 13 代：领域扩展包

- 时间: 2026-03-22 04:08:23
- 核心焦点: 让 ClawProfile 能承载 robotics、research、release 等扩展包。
- 当前快照: events=3641, sessions=257, patterns=82, workflows=9, shared_profiles=9
- 本轮目标:
  - 用 pack/namespace 组织规则
  - 支持社区导入时保留来源与 trust
  - 减少不同领域规范互相污染
- 备注: 这是自动化的高层迭代审视记录，不会在夜间无提示修改代码。


## 第 14 代：审查与验证闸门

- 时间: 2026-03-22 05:08:23
- 核心焦点: 把夜间自动迭代和 build/test/review 闸门整合。
- 当前快照: events=3641, sessions=257, patterns=82, workflows=9, shared_profiles=9
- 本轮目标:
  - 每轮改进都写 iteration report
  - 自动验证失败时只记录建议，不盲目改动代码
  - 为真正无人值守迭代建立安全边界
- 备注: 这是自动化的高层迭代审视记录，不会在夜间无提示修改代码。


## 第 15 代：ClawProfile 操作系统化

- 时间: 2026-03-22 12:14:00
- 核心焦点: 把规则学习、执行反馈和社区分发合成完整闭环。
- 当前快照: events=3641, sessions=257, patterns=86, workflows=9, shared_profiles=9
- 本轮目标:
  - Shadow/Mirror/Brain/Autopilot 统一围绕 ClawProfile 演化
  - 让 ClawProfile 成为可增长、可审计、可复用的核心产物
  - 为后续真正生成性 workflow 奠定数据和规则基础
- 备注: 这是自动化的高层迭代审视记录，不会在夜间无提示修改代码。

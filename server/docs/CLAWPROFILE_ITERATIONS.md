

## 第 2 代：Shadow 结构化事件抽取

- 时间: 2026-03-21 03:50:15
- 核心焦点: 把原始事件升级成包含 intent/tool/artifact/outcome/error_signature 的行为原子。
- 当前快照: events=3570, sessions=225, patterns=71, workflows=9, shared_profiles=9
- 本轮目标:
  - 新增 EventAtom 层而不是继续只看 action 文本
  - 把 command family / error signature / artifact ref 作为统一字段采集
  - 为后续 Episode 切分准备 task_hint 和 outcome 标签
- 备注: 这是自动化的高层迭代审视记录，不会在夜间无提示修改代码。

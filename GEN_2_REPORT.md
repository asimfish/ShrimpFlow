# Gen 2 Report: 管线修复 + 方向1基础

## 修复清单

| 文件 | 修复 | 方向 |
|------|------|------|
| `server/services/cot_miner.py` | `mine_cot_skills()` 末尾写入 `OpenClawInvocationLog`，`selector_type='cot'`，供 `skill_tracker.mine_skill_workflows()` 消费 | 方向1 |
| `server/services/workflow_inferrer.py` | `infer_workflows_from_episodes()` 新增 Skill 表交叉匹配，每个 workflow 输出 `matched_skills` + `skill_coverage` 分数 | 方向1 |
| `server/services/taste_model.py` | `learn_from_history()` 新增 reject reason 聚合，提取用户拒绝原因统计写入 `taste_summary`，作为负向信号 | 方向3 |

## 管线连通状态

```
Before Gen 2:
  cot_miner ──✗──→ InvocationLog ←── skill_tracker
  workflow_inferrer ──✗──→ Skill table
  reject reason ──✗──→ taste_model

After Gen 2:
  cot_miner ──✓──→ InvocationLog ←── skill_tracker
  workflow_inferrer ──✓──→ Skill table (matched_skills, skill_coverage)
  reject reason ──✓──→ taste_model (聚合进 taste_summary)
```

## 四方向推进

| 方向 | Gen 2 进展 |
|------|-----------|
| 方向1: Skill Workflow 挖掘 | CoT -> InvocationLog 打通；Workflow -> Skill 匹配打通 |
| 方向2: Skill 推荐 | 未触及（Gen 4-5） |
| 方向3: 人参与闭环 | reject reason 进入 taste 负向信号 |
| 方向4: Claw 自主体 | 未触及（Gen 7-8） |

## 验证
- TypeScript: PASS
- Python: PASS

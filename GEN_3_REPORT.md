# Gen 3 Report: 功能补全 + Skill Workflow 挖掘管线

## 修复清单

| 文件 | 修复 | 方向 |
|------|------|------|
| `src/pages/layers/autopilot_page.vue` | Workflow 创建按钮接入真实 API，增加 loading/error 状态 | 功能补全 |
| `src/http_api/patterns.ts` | 新增 `createWorkflowApi` | 功能补全 |
| `src/pages/layers/mirror_page.vue` | 画像文案从写死改为 computed（events/skills/patterns store 驱动） | 功能补全 |
| `server/models/skill_workflow.py` | **新增** SkillWorkflow 模型（方向1核心数据结构） | 方向1 |
| `server/models/__init__.py` | 导入 SkillWorkflow | 方向1 |
| `server/db.py` | ensure_runtime_schema 新增 skill_workflows 建表 | 方向1 |
| `server/services/skill_tracker.py` | `mine_skill_workflows()` 末尾持久化到 SkillWorkflow 表（幂等 upsert） | 方向1 |
| `server/routes/skills.py` | 新增 `GET /skills/workflows/mined` 返回持久化的 Skill Workflow | 方向1 |

## 方向1 管线完成度

```
CoT 会话 → cot_miner → InvocationLog → skill_tracker → mine_skill_workflows
                                                              ↓
                                                    SkillWorkflow 表（持久化）
                                                              ↓
                                              GET /skills/workflows/mined（API）
                                                              ↓
                                           workflow_inferrer → matched_skills
```

## 验证
- TypeScript: PASS
- Python: PASS

# Gen 4 Report: 数据流优化 + Skill 推荐前端

## 修复清单

| 文件 | 修复 | 方向 |
|------|------|------|
| `src/http_api/skills.ts` | 新增 `getMinedWorkflowsApi` | 方向2 |
| `src/types/index.ts` | 新增 `SkillWorkflowItem` 类型 | 方向2 |
| `src/stores/patterns.ts` | 添加 try/catch 错误处理 | 数据流 |
| `src/stores/events.ts` | 添加 error ref + try/catch | 数据流 |
| `src/stores/skills.ts` | 添加 error ref + try/catch | 数据流 |
| `src/stores/digest.ts` | 添加 error ref + try/catch | 数据流 |
| `src/stores/openclaw.ts` | 添加 error ref + loading + try/catch | 数据流 |
| `src/pages/skills/skill_tree_page.vue` | 推荐 tab 新增 "Skill Workflow 挖掘" 面板，展示挖掘出的 workflow 序列 | 方向2 |

## 验证
- TypeScript: PASS
- Python: PASS

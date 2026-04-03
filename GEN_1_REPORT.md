# Gen 1 Report: 全局扫描 + 快速修复

## 扫描统计

- 10 个 agent 并行分析完成
- 发现问题总计: ~45 项
- 本代修复: 16 项（全部为低风险安全化改动）
- 剩余待处理: ~29 项（移交 Gen 2+）

## 修复清单

### 已修复（Gen 1）

| 文件 | 修复 | 数量 |
|------|------|------|
| `server/services/cot_miner.py` | JSON 解析安全化 | 1 |
| `server/services/workflow_inferrer.py` | JSON 解析安全化 | 1 |
| `server/services/evidence_ledger.py` | JSON 解析安全化 | 1 |
| `server/services/consolidation_service.py` | JSON 解析安全化 | 4 |
| `server/services/memory_lifecycle.py` | JSON 解析安全化 | 1 |
| `server/services/deep_mining.py` | JSON 解析安全化 | 6 |
| `.gitignore` | 新增 `*.db-wal`, `*.db-shm`, `.env`, `.env.local` | 1 |
| `server/main.py` | `host` 从 `0.0.0.0` 改为 `127.0.0.1` | 1 |

### 发现但未修复（移交后续代）

**P0 安全问题（Gen 6 处理）:**
- `src/http_api/_snapshot.json` 含真实 API key (`sk-*`)
- `docs/assets/*.js` 构建产物含敏感数据
- API 无认证（所有路由匿名可访问）

**P1 管线断裂（Gen 2 处理）:**
- `cot_miner` 不写 `InvocationLog`（方向1基础缺失）
- `workflow_inferrer` 不使用 `Skill` 表数据
- `skill_tracker` 与 `workflow_inferrer` 两条链路未统一
- `reject reason` 未进入挖掘过滤/提示词（方向3缺失）
- 并发修改 `BehaviorPattern` 无协调

**P1 前端缺口（Gen 3 处理）:**
- Autopilot 页面 workflow 创建未接 API
- Mirror 页面部分画像文案写死
- Security 页面数据为静态演示

**P2 性能/规范（Gen 7-9 处理）:**
- 多处 N+1 查询模式
- d3 全量导入未 tree-shake
- README 仍为 Vue 模板占位
- 无 LICENSE 文件

## 四方向推进

| 方向 | Gen 1 进展 |
|------|-----------|
| 方向1: Skill Workflow 挖掘 | 识别管线断裂点（cot_miner↛InvocationLog, workflow_inferrer↛Skill） |
| 方向2: Skill 推荐 | 确认本地推荐可用，远程源完全缺失 |
| 方向3: 人参与闭环 | 确认 reject reason 已传到后端，但未进入挖掘反馈 |
| 方向4: Claw 自主体 | 确认 taste_model 仅驱动 pattern 生命周期，未驱动任务编排 |

## 验证

- TypeScript: PASS
- Python: PASS
- 无回归

## Gen 2 重点

1. 打通 cot_miner -> InvocationLog 写入链路
2. workflow_inferrer 引入 Skill 表关联
3. reject reason 进入 taste_model 的负向信号

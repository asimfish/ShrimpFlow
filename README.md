# ShrimpFlow — 让 AI 认识你这个人

**一句话**：第一个将用户认知风格编码为可执行 AI 规范的系统。

> **命名约定**：对外产品名是 **ShrimpFlow**；内部代号与引擎是 **ShrimpFlow**（见目录、包名、DB 文件）；协作协议与注入格式是 **OpenClaw / ClawProfile**。三者分工明确，不是三个产品。

## 核心叙事

不是「AI 记得你做过什么」，而是 **AI 知道你怎么思考**（how you think, not what you did）。ShrimpFlow 观察行为、建模认知、对齐偏好，并输出可粘贴到各工具中的行为规范（ClawProfile / `CLAUDE.md`），形成持续进化的闭环。

## 功能概览

| 能力 | 说明 |
|------|------|
| **研究品味 5 维量化** | Rigor / Elegance / Novelty / Simplicity / Reproducibility 五维刻画 research taste |
| **认知对齐分数** | 衡量 ClawProfile 与实际行为的一致性 |
| **ClawProfile 格式** | 跨 IDE / Agent 便携的行为规范载体 |
| **Skill Workflow 自动挖掘** | 从使用轨迹中抽取可复用 workflow |
| **Skill 发掘推荐** | 基于上下文推荐可安装的 skills |
| **飞轮效应可视化** | 量化「越用越准」的对齐与演化 |
| **CLAUDE.md 一键导出** | 带证据引用、可直接使用的导出 |

## 快速开始

前置：macOS 或 Linux；`setup.sh` 会引导安装 **uv**；需本机已有 **Node.js**（无则按脚本提示用 brew / NodeSource 安装），并安装 **pnpm**。

```bash
git clone <YOUR_REPO_URL> shrimpflow
cd shrimpflow
bash setup.sh    # 安装依赖、uv sync、初始化 server/.env（请配置 ANTHROPIC_API_KEY）
bash start.sh    # 同时启动后端与前端开发服务
```

浏览器打开：**http://localhost:5173**

- 后端 API：**http://localhost:7891**
- OpenAPI 文档：**http://localhost:7891/docs**
- Liveness 探针：**http://localhost:7891/api/health**

### 验证安装 / 开发者入口

```bash
make smoke          # 一键冒烟：依赖 → import → 57 个测试 → vue-tsc → /api/health
make test           # 仅跑后端测试
make lint           # 仅跑前端 type-check
make dev            # 同时启动前后端开发服务
```

### 运行时环境变量

| 变量 | 默认 | 含义 |
|---|---|---|
| `DEVTWIN_DATABASE_URL` | `sqlite:///shrimpflow.db` | SQLAlchemy URL，测试/多租户可覆盖 |
| `DEVTWIN_CORS_ORIGINS` | `http://localhost:5173` | CORS 允许源，逗号分隔 |
| `DEVTWIN_PORT` | `7891` | 后端监听端口 |
| `DEVTWIN_HOST` | `127.0.0.1` | 后端监听地址 |
| `DEVTWIN_RELOAD` | `1` | 1=开启 uvicorn reload |
| `DEVTWIN_SEED_RNG` | `2026` | Demo 数据 RNG 种子（保证可复现） |

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3, TypeScript, Vite, Tailwind CSS v4, d3 |
| 后端 | FastAPI, SQLAlchemy, SQLite |
| AI | Anthropic API（Claude） |

## 架构（简图）

```
Browser (Vue 3)
    →  Vite dev server :5173（前端 + API 代理）
    →  FastAPI :7891
    →  SQLite
```

生产或自定义部署时，保持「前端 → 后端 REST → 数据库」这一链路即可。

## 战略方向（与 VISION 一致）

1. **认知优于记忆**：产品重心是思维与决策风格的可建模、可对齐，而非单纯会话记忆与检索。
2. **品味可度量**：用多维量化支撑「我的研究 / 工程品味是什么」的表达与对比。
3. **规范可执行、可迁移**：ClawProfile / 导出物能在不同工具链中落地，减少「换环境就丢人格」。
4. **闭环进化**：对齐分数、修正信号与飞轮指标，让规范随真实使用迭代，而非一次性配置。

更完整的路线图与成功标准见仓库内 **[VISION.md](./VISION.md)**。

## 文档与规范

- **[VISION.md](./VISION.md)** — 产品愿景与迭代目标
- **[CLAWPROFILE_SPEC.md](./CLAWPROFILE_SPEC.md)** — ClawProfile Stable Spec v1.0（冻结合同）
- **[docs/spec/CHANGELOG.md](./docs/spec/CHANGELOG.md)** — 规范演进与 Extension Proposal 流程
- **[docs/spec/CLAWPROFILE_SPEC_v53_rolling_draft.md](./docs/spec/CLAWPROFILE_SPEC_v53_rolling_draft.md)** — 未冻结研究草案（仅参考）
- **[docs/development-history/](./docs/development-history/)** — 十代迭代报告（Gen 1–10）

## 质量保障（2026-Q2 冻结版本）

- **57 个单元/契约/冒烟测试** 覆盖 AI provider 级联、贝叶斯证据账本、pattern 挖掘 primitives、配额闸门、taste 鲁棒化、日志脱敏、FastAPI 生命周期。`make test` 全绿是提 PR 的前置条件。
- **Pattern 爆炸防护**：全局 500 条上限 + 每日 30 条 auto 新增上限；超限时 hard-prune archived/compressed & 低价值模式，永不误删 confirmed。
- **Taste 维度鲁棒化**：empirical-Bayes 平滑 + 样本量门槛 + 类别加分上限，防止小样本 / 关键词刷分 / 长尾类别推到 100 分。
- **日志脱敏**：monkey-patch `LogRecord.getMessage`，任何 handler / 第三方库产生的日志都会过滤 `sk-*` / `Bearer` / `api_key=` 等 6 种形状。

## 许可证

本项目采用 **MIT License**。

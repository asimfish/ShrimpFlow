# DevTwin（ShrimpFlow）— 让 AI 认识你这个人

**一句话**：第一个将用户认知风格编码为可执行 AI 规范的系统。

## 核心叙事

不是「AI 记得你做过什么」，而是 **AI 知道你怎么思考**（how you think, not what you did）。DevTwin 观察行为、建模认知、对齐偏好，并输出可粘贴到各工具中的行为规范（ClawProfile / `CLAUDE.md`），形成持续进化的闭环。

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
git clone <YOUR_REPO_URL> devtwin
cd devtwin
bash setup.sh    # 安装依赖、uv sync、初始化 server/.env（请配置 ANTHROPIC_API_KEY）
bash start.sh    # 同时启动后端与前端开发服务
```

浏览器打开：**http://localhost:5173**

- 后端 API：**http://localhost:7891**
- OpenAPI 文档：**http://localhost:7891/docs**

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
- **[CLAWPROFILE_SPEC.md](./CLAWPROFILE_SPEC.md)** — ClawProfile 格式说明  

## 许可证

本项目采用 **MIT License**（仓库将补充 `LICENSE` 文件；在此之前以 MIT 意图为准）。

# Contributing to DevTwin

感谢参与。本文说明如何搭建环境、理解仓库结构与提交约定。

## 环境搭建

1. 克隆仓库后执行 `bash setup.sh`（会引导 **uv**、Python 依赖与 `server/.env`；需自行配置如 `ANTHROPIC_API_KEY`）。
2. 需本机 **Node.js** 与 **pnpm**（脚本会提示安装方式）。
3. 日常开发：`bash start.sh` 同时启动 FastAPI（默认 **7891**）与 Vite 前端（**5173**）。
4. API 说明见 [docs/API.md](./docs/API.md)；交互式文档：`http://localhost:7891/docs`。

## 架构概览

- **前端**：`src/` — Vue 3、TypeScript、Vite；经 dev server 代理访问后端。
- **后端**：`server/` — FastAPI 入口 `main.py`，路由在 `server/routes/`，业务在 `server/services/`，ORM 模型在 `server/models/`，SQLite。
- **契约**：前后端通过 `/api/*` REST 通信；新增端点请同步更新 `docs/API.md`。

## 代码约定

- **前端样式**：使用项目已采用的 **Tailwind CSS v4**，与现有组件间距、字号保持一致。
- **文件命名**：新建文件优先 **snake_case**（与仓库 Python 及部分前端约定一致；若某目录已有另一惯例，跟随该目录）。
- **TypeScript / JS**：在符合项目风格的前提下，优先用 **`const` 箭头函数** 声明可复用逻辑，避免不必要的 `function` 声明。
- **Python**：保持与现有 routes/services 相同的类型标注与依赖注入模式；避免无依据的宽泛 `try/except`。

## Pull Request 流程

1. 从 `main`（或指定基线）开分支，改动聚焦单一主题。
2. 本地确认后端可启动、前端可构建；如有相关脚本请在 PR 中写明已执行的命令。
3. PR 描述写清**动机**、**行为变化**与**风险/回滚**；若改 API，已更新 `docs/API.md`。
4. 审查通过后由维护者合并；避免在 PR 中夹带无关格式化或大范围重命名。

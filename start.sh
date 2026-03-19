#!/bin/bash
# ShrimpFlow 一键启动脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"
FRONTEND_DIR="$SCRIPT_DIR"

echo "=== ShrimpFlow 启动 ==="
echo ""

# 检查 uv
if ! command -v uv &> /dev/null; then
  echo "[ERROR] uv 未安装，请先安装: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

# 检查 pnpm
if ! command -v pnpm &> /dev/null; then
  echo "[ERROR] pnpm 未安装，请先安装: npm install -g pnpm"
  exit 1
fi

# 启动后端
echo "[1/2] 启动后端 (port 7890)..."
cd "$SERVER_DIR"
uv sync --quiet 2>/dev/null
uv run python main.py &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

# 等待后端就绪
echo "  等待后端启动..."
for i in $(seq 1 10); do
  if curl -s http://localhost:7890/api/stats > /dev/null 2>&1; then
    echo "  后端已就绪"
    break
  fi
  sleep 1
done

# 启动前端
echo "[2/2] 启动前端 (port 5173)..."
cd "$FRONTEND_DIR"
pnpm dev &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"

echo ""
echo "=== ShrimpFlow 已启动 ==="
echo "  前端: http://localhost:5173"
echo "  后端: http://localhost:7890"
echo "  API 文档: http://localhost:7890/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 捕获退出信号
trap "echo ''; echo '正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait

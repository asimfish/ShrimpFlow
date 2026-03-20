#!/bin/bash
# ShrimpFlow 一键启动脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"
FRONTEND_DIR="$SCRIPT_DIR"
BACKEND_PORT=7891
FRONTEND_PORT=5173
PID_FILE="$SCRIPT_DIR/.shrimpflow-dev.pids"
BACKEND_LOG="$SCRIPT_DIR/.shrimpflow-backend.log"
FRONTEND_LOG="$SCRIPT_DIR/.shrimpflow-frontend.log"

stop_pid() {
  local pid="$1"

  if ! kill -0 "$pid" 2>/dev/null; then
    return 0
  fi

  kill "$pid" 2>/dev/null || true

  for _ in $(seq 1 20); do
    if ! kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
    sleep 0.2
  done

  kill -9 "$pid" 2>/dev/null || true
}

is_project_process() {
  local pid="$1"
  local cwd

  cwd="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1)"
  [[ -n "$cwd" ]] || return 1
  [[ "$cwd" == "$SCRIPT_DIR"* ]]
}

stop_pid_file_processes() {
  if [[ ! -f "$PID_FILE" ]]; then
    return 0
  fi

  while IFS= read -r pid; do
    [[ "$pid" =~ ^[0-9]+$ ]] || continue
    stop_pid "$pid"
  done < "$PID_FILE"

  rm -f "$PID_FILE"
}

stop_port_owner_if_project_process() {
  local port="$1"
  local label="$2"
  local pids
  local pid

  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  [[ -n "$pids" ]] || return 0

  for pid in $pids; do
    if is_project_process "$pid"; then
      echo "  清理旧${label}进程 PID: $pid (port $port)"
      stop_pid "$pid"
    else
      echo "[ERROR] port $port 被其他进程占用，已停止启动以避免连到错误版本。"
      lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed 's/^n/  cwd: /'
      exit 1
    fi
  done
}

cleanup_previous_run() {
  echo "[0/2] 清理旧的 ShrimpFlow 进程..."
  stop_pid_file_processes
  stop_port_owner_if_project_process "$BACKEND_PORT" "后端"

  for port in "$FRONTEND_PORT" "$((FRONTEND_PORT + 1))" "$((FRONTEND_PORT + 2))"; do
    stop_port_owner_if_project_process "$port" "前端"
  done
}

wait_for_http_ready() {
  local url="$1"
  local label="$2"

  for _ in $(seq 1 30); do
    if curl -s "$url" > /dev/null 2>&1; then
      echo "  ${label}已就绪"
      return 0
    fi
    sleep 1
  done

  echo "[ERROR] ${label}启动超时: $url"
  return 1
}

cleanup_children() {
  [[ -n "${BACKEND_WRAPPER_PID:-}" ]] && stop_pid "$BACKEND_WRAPPER_PID"
  [[ -n "${BACKEND_PID:-}" ]] && stop_pid "$BACKEND_PID"
  [[ -n "${FRONTEND_PID:-}" ]] && stop_pid "$FRONTEND_PID"
  rm -f "$PID_FILE"
}

resolve_listener_pid() {
  local port="$1"
  lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -n 1
}

handle_signal() {
  trap - INT TERM EXIT
  echo ""
  echo "正在停止服务..."
  cleanup_children
  exit 0
}

cleanup_on_exit() {
  local exit_code=$?
  trap - EXIT

  if [[ $exit_code -ne 0 ]]; then
    echo ""
    echo "正在停止服务..."
  fi

  cleanup_children
  exit "$exit_code"
}

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

cleanup_previous_run
trap handle_signal INT TERM
trap cleanup_on_exit EXIT

# 启动后端
echo "[1/2] 启动后端 (port $BACKEND_PORT)..."
cd "$SERVER_DIR"
uv sync --quiet 2>/dev/null
: > "$BACKEND_LOG"
SHRIMPFLOW_RELOAD=0 uv run python main.py >> "$BACKEND_LOG" 2>&1 &
BACKEND_WRAPPER_PID=$!
echo "  Backend wrapper PID: $BACKEND_WRAPPER_PID"

# 等待后端就绪
echo "  等待后端启动..."
wait_for_http_ready "http://localhost:$BACKEND_PORT/api/stats" "后端"
BACKEND_PID="$(resolve_listener_pid "$BACKEND_PORT")"
if [[ -z "$BACKEND_PID" ]]; then
  echo "[ERROR] 后端端口已响应，但无法解析监听进程 PID"
  echo "  最近后端日志:"
  tail -n 40 "$BACKEND_LOG"
  exit 1
fi
echo "  Backend PID: $BACKEND_PID"

# 启动前端
echo "[2/2] 启动前端 (port $FRONTEND_PORT)..."
cd "$FRONTEND_DIR"
: > "$FRONTEND_LOG"
pnpm dev >> "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"
printf "%s\n%s\n%s\n" "$BACKEND_WRAPPER_PID" "$BACKEND_PID" "$FRONTEND_PID" > "$PID_FILE"
echo "  等待前端启动..."
wait_for_http_ready "http://localhost:$FRONTEND_PORT" "前端"

echo ""
echo "=== ShrimpFlow 已启动 ==="
echo "  前端: http://localhost:$FRONTEND_PORT"
echo "  后端: http://localhost:$BACKEND_PORT"
echo "  API 文档: http://localhost:$BACKEND_PORT/docs"
echo "  后端日志: $BACKEND_LOG"
echo "  前端日志: $FRONTEND_LOG"
echo ""
echo "按 Ctrl+C 停止所有服务"

wait

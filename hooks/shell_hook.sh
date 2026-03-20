#!/bin/bash
# ShrimpFlow Shell Hook - 采集终端命令
# 安装方式: source hooks/shell_hook.sh

SHRIMPFLOW_API="${SHRIMPFLOW_API:-http://localhost:7891/api/collect/terminal}"

# zsh preexec hook - 命令执行前记录
shrimpflow_preexec() {
  SHRIMPFLOW_CMD="$1"
  SHRIMPFLOW_START=$(date +%s%3N)
}

# zsh precmd hook - 命令执行后发送
shrimpflow_precmd() {
  local exit_code=$?

  # 跳过空命令
  if [ -z "$SHRIMPFLOW_CMD" ]; then
    return
  fi

  local end_time=$(date +%s%3N)
  local duration=$((end_time - SHRIMPFLOW_START))
  local project=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null)
  local branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  local directory=$(pwd)

  # 后台发送，不阻塞终端
  curl -s -X POST "$SHRIMPFLOW_API" \
    -H "Content-Type: application/json" \
    -d "{
      \"source\": \"terminal\",
      \"action\": \"$(echo "$SHRIMPFLOW_CMD" | sed 's/"/\\"/g')\",
      \"directory\": \"$directory\",
      \"project\": \"${project:-unknown}\",
      \"branch\": \"${branch:-unknown}\",
      \"exit_code\": $exit_code,
      \"duration_ms\": $duration,
      \"semantic\": \"\",
      \"tags\": [\"shell\"]
    }" > /dev/null 2>&1 &

  SHRIMPFLOW_CMD=""
}

# 注册 hooks
if [ -n "$ZSH_VERSION" ]; then
  autoload -Uz add-zsh-hook
  add-zsh-hook preexec shrimpflow_preexec
  add-zsh-hook precmd shrimpflow_precmd
  echo "[ShrimpFlow] Shell hook activated (zsh)"
elif [ -n "$BASH_VERSION" ]; then
  trap 'shrimpflow_preexec "$BASH_COMMAND"' DEBUG
  PROMPT_COMMAND="shrimpflow_precmd;$PROMPT_COMMAND"
  echo "[ShrimpFlow] Shell hook activated (bash)"
fi

#!/bin/bash
# ShrimpFlow Git Hook - post-commit
# 安装方式: cp hooks/git_hook.sh .git/hooks/post-commit && chmod +x .git/hooks/post-commit

SHRIMPFLOW_API="${SHRIMPFLOW_API:-http://localhost:7891/api/collect/git}"

# 获取最新提交信息
COMMIT_MSG=$(git log -1 --pretty=format:"%s")
COMMIT_HASH=$(git log -1 --pretty=format:"%h")
BRANCH=$(git rev-parse --abbrev-ref HEAD)
PROJECT=$(basename "$(git rev-parse --show-toplevel)")
DIRECTORY=$(git rev-parse --show-toplevel)
FILES_CHANGED=$(git diff-tree --no-commit-id --name-only -r HEAD | wc -l | tr -d ' ')

curl -s -X POST "$SHRIMPFLOW_API" \
  -H "Content-Type: application/json" \
  -d "{
    \"source\": \"git\",
    \"action\": \"commit: $COMMIT_MSG ($COMMIT_HASH)\",
    \"directory\": \"$DIRECTORY\",
    \"project\": \"$PROJECT\",
    \"branch\": \"$BRANCH\",
    \"exit_code\": 0,
    \"duration_ms\": 0,
    \"semantic\": \"Git commit with $FILES_CHANGED files changed\",
    \"tags\": [\"git\", \"commit\"]
  }" > /dev/null 2>&1

echo "[ShrimpFlow] Commit recorded: $COMMIT_MSG"

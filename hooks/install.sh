#!/bin/bash
# ShrimpFlow Hooks 安装脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SHELL_HOOK="$SCRIPT_DIR/shell_hook.sh"
GIT_HOOK="$SCRIPT_DIR/git_hook.sh"

echo "=== ShrimpFlow Hooks Installer ==="
echo ""

# 安装 Shell Hook
install_shell_hook() {
  local rc_file=""
  if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
    rc_file="$HOME/.zshrc"
  elif [ -f "$HOME/.bashrc" ]; then
    rc_file="$HOME/.bashrc"
  fi

  if [ -z "$rc_file" ]; then
    echo "[SKIP] No .zshrc or .bashrc found"
    return
  fi

  local hook_line="source \"$SHELL_HOOK\""
  if grep -q "shrimpflow" "$rc_file" 2>/dev/null; then
    echo "[OK] Shell hook already installed in $rc_file"
  else
    echo "" >> "$rc_file"
    echo "# ShrimpFlow Shell Hook" >> "$rc_file"
    echo "$hook_line" >> "$rc_file"
    echo "[OK] Shell hook installed in $rc_file"
  fi
}

# 安装 Git Hook
install_git_hook() {
  local git_dir
  git_dir=$(git rev-parse --git-dir 2>/dev/null)

  if [ -z "$git_dir" ]; then
    echo "[SKIP] Not in a git repository"
    return
  fi

  local hooks_dir="$git_dir/hooks"
  mkdir -p "$hooks_dir"

  if [ -f "$hooks_dir/post-commit" ]; then
    echo "[WARN] post-commit hook already exists, appending..."
    echo "" >> "$hooks_dir/post-commit"
    cat "$GIT_HOOK" >> "$hooks_dir/post-commit"
  else
    cp "$GIT_HOOK" "$hooks_dir/post-commit"
  fi

  chmod +x "$hooks_dir/post-commit"
  echo "[OK] Git post-commit hook installed"
}

install_shell_hook
install_git_hook

echo ""
echo "=== Installation complete ==="
echo "Restart your shell or run: source $SHELL_HOOK"

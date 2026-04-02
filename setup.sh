#!/usr/bin/env bash
set -e

echo ""
echo "  🦐 DevTwin / ShrimpFlow — 一键安装"
echo "  =================================="
echo ""

# 检测 OS
OS="$(uname -s)"
case "$OS" in
  Darwin) PLATFORM="macOS" ;;
  Linux)  PLATFORM="Linux" ;;
  *)      echo "❌ 不支持的系统: $OS"; exit 1 ;;
esac
echo "  系统: $PLATFORM"

# 检测并安装 uv
if command -v uv &>/dev/null; then
  echo "  ✅ uv 已安装: $(uv --version)"
else
  echo "  📦 安装 uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  echo "  ✅ uv 安装完成"
fi

# 检测并安装 Node.js + pnpm
if command -v pnpm &>/dev/null; then
  echo "  ✅ pnpm 已安装: $(pnpm --version)"
else
  if ! command -v node &>/dev/null; then
    echo "  ❌ 未检测到 Node.js，请先安装:"
    if [ "$PLATFORM" = "macOS" ]; then
      echo "     brew install node"
    else
      echo "     curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs"
    fi
    exit 1
  fi
  echo "  📦 安装 pnpm..."
  npm install -g pnpm
  echo "  ✅ pnpm 安装完成"
fi

# 安装前端依赖
echo ""
echo "  📦 安装前端依赖..."
pnpm install

# 安装后端依赖
echo "  📦 安装后端依赖..."
cd server
uv sync
cd ..

# 配置环境变量
if [ ! -f server/.env ]; then
  if [ -f server/.env.example ]; then
    cp server/.env.example server/.env
    echo ""
    echo "  ⚙️  已创建 server/.env（从 .env.example 复制）"
  else
    cat > server/.env << 'ENVEOF'
ANTHROPIC_API_KEY=your-api-key-here
ANTHROPIC_SELECTOR_MODEL=claude-3-5-haiku-latest
ENVEOF
    echo ""
    echo "  ⚙️  已创建 server/.env"
  fi
  echo ""
  echo "  ⚠️  请编辑 server/.env 填入你的 API Key:"
  echo "     ANTHROPIC_API_KEY=sk-ant-..."
  echo ""
  read -p "  现在填入 ANTHROPIC_API_KEY (回车跳过): " api_key
  if [ -n "$api_key" ]; then
    if [ "$PLATFORM" = "macOS" ]; then
      sed -i '' "s|your-api-key-here|$api_key|" server/.env
    else
      sed -i "s|your-api-key-here|$api_key|" server/.env
    fi
    echo "  ✅ API Key 已写入"
  else
    echo "  ⏭️  跳过，稍后请手动编辑 server/.env"
  fi
else
  echo "  ✅ server/.env 已存在"
fi

echo ""
echo "  🎉 安装完成！启动服务:"
echo ""
echo "     bash start.sh"
echo ""
echo "  启动后访问:"
echo "     前端: http://localhost:5173"
echo "     后端: http://localhost:7891"
echo "     API 文档: http://localhost:7891/docs"
echo ""

read -p "  是否现在启动？(Y/n): " start_now
if [ "$start_now" != "n" ] && [ "$start_now" != "N" ]; then
  bash start.sh
fi

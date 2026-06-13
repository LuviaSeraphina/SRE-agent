#!/usr/bin/env bash
# ============================================================
# SRE-agent 快速部署 (非交互模式)
# 适合 CI/CD 流水线、容器初始化
#
# 用法:
#   bash scripts/quick-deploy.sh                    # 默认 Ollama
#   bash scripts/quick-deploy.sh deepseek YOUR_KEY  # 使用 DeepSeek 云端
#   curl ... | bash -s -- deepseek YOUR_KEY         # 一键远程部署
# ============================================================
set -euo pipefail

LLM_PROVIDER="${1:-ollama}"
LLM_API_KEY="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# ---- 颜色 ----
GREEN='\033[0;32m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
log() { echo -e "${BLUE}[SRE-agent]${NC} $*"; }

echo -e "${BOLD}${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║   SRE-agent 快速部署 (非交互模式)    ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════╝${NC}"

# ---- 检测 Python ----
PYTHON_BIN=""
for py in python3.13 python3.11 python3.10 python3; do
    command -v "$py" &>/dev/null && { PYTHON_BIN="$py"; break; }
done
[ -z "$PYTHON_BIN" ] && { echo "❌ Python 3 未安装"; exit 1; }
log "Python: $($PYTHON_BIN --version)"

# ---- 后端 ----
log "安装后端依赖..."
cd "$BACKEND_DIR"
[ ! -d ".venv" ] && $PYTHON_BIN -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
log "✅ 后端就绪"

# ---- LLM 配置 ----
log "配置 LLM: $LLM_PROVIDER"
if [ "$LLM_PROVIDER" = "deepseek" ]; then
    cat > .env << EOF
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
LLM_API_KEY=$LLM_API_KEY
MAX_RISK_LEVEL=restricted
REQUIRE_CONFIRMATION=true
AUDIT_ENABLED=true
DATABASE_URL=sqlite+aiosqlite:///$BACKEND_DIR/data/state_store.db
EOF
else
    cat > .env << EOF
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=qwen3:4b
LLM_API_KEY=
MAX_RISK_LEVEL=restricted
REQUIRE_CONFIRMATION=true
AUDIT_ENABLED=true
DATABASE_URL=sqlite+aiosqlite:///$BACKEND_DIR/data/state_store.db
EOF
fi
log "✅ 配置完成"

# ---- 前端 ----
log "构建前端..."
cd "$FRONTEND_DIR"
[ ! -d "node_modules" ] && npm install --silent
npm run build --silent 2>&1 | tail -2
log "✅ 前端就绪"

# ---- 验证 ----
deactivate 2>/dev/null || true
cd "$BACKEND_DIR" && source .venv/bin/activate

TOOLS=$("$VENV_DIR/bin/python" -c "from app.mcp_plugins.base import registry; print(registry.count)")
log "✅ Tool 注册: $TOOLS 个"
log "✅ 部署完成"
echo ""
echo "  启动后端: cd $BACKEND_DIR && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8001"
echo "  启动前端: cd $FRONTEND_DIR && npm run dev"

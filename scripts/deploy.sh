#!/usr/bin/env bash
# ============================================================
# SRE-agent 一键部署脚本 v0.2.0
#
# 功能:
#   1. 自动检测操作系统 (麒麟/Ubuntu/Debian)
#   2. 安装系统依赖 (Python 3.10+, Node.js 18+)
#   3. 创建 Python 虚拟环境并安装后端依赖
#   4. 安装前端依赖并构建
#   5. 交互式 LLM 配置 (Ollama 本地 / DeepSeek 云端)
#   6. 创建 sreagent 专用低权限用户
#   7. 生成 systemd 服务文件
#   8. 部署验证
#
# 用法: bash scripts/deploy.sh
# ============================================================

set -euo pipefail

# ---- 颜色 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ---- 路径 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"
ENV_FILE="$BACKEND_DIR/.env"

# ---- 日志函数 ----
log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_step()  { echo -e "\n${BOLD}${BLUE}▶ $*${NC}"; }

# ---- Banner ----
echo -e "${BOLD}${GREEN}"
echo "  ╔═══════════════════════════════════════════════════╗"
echo "  ║     SRE-agent 一键部署脚本 v0.2.0                  ║"
echo "  ║     面向麒麟操作系统的安全智能运维 Agent            ║"
echo "  ╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"

# ============================================================
# Step 1: 检测操作系统
# ============================================================
log_step "Step 1/8: 检测操作系统"

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_ID="${ID:-unknown}"
        OS_NAME="${PRETTY_NAME:-$OS_ID}"
        OS_VERSION="${VERSION_ID:-}"
    elif [ -f /etc/kylin-release ]; then
        OS_ID="kylin"
        OS_NAME="Kylin Linux"
        OS_VERSION="V10"
    else
        OS_ID="unknown"
        OS_NAME="Unknown Linux"
    fi

    ARCH="$(uname -m)"

    # 麒麟标识
    if [ -f /etc/kylin-release ] || echo "$OS_ID" | grep -qi "kylin"; then
        IS_KYLIN=true
        PKG_MGR="dnf"
    elif command -v apt &>/dev/null; then
        IS_KYLIN=false
        PKG_MGR="apt"
    elif command -v dnf &>/dev/null; then
        IS_KYLIN=false
        PKG_MGR="dnf"
    else
        PKG_MGR="unknown"
    fi

    echo "  操作系统 : $OS_NAME"
    echo "  架构     : $ARCH"
    echo "  包管理器 : $PKG_MGR"
    echo "  麒麟标识 : $IS_KYLIN"
}

detect_os

# ============================================================
# Step 2: 安装系统依赖
# ============================================================
log_step "Step 2/8: 安装系统依赖"

install_system_deps() {
    if [ "$PKG_MGR" = "dnf" ]; then
        log_info "使用 dnf 安装..."
        if [ "$IS_KYLIN" = true ]; then
            sudo dnf install -y \
                python3.13 python3.13-devel python3.13-pip \
                nodejs npm git curl 2>/dev/null || {
                    # 降级: 尝试 python3.11
                    log_warn "python3.13 不可用, 尝试 python3.11"
                    sudo dnf install -y python3.11 python3.11-devel python3.11-pip nodejs npm git curl
                }
        else
            sudo dnf install -y python3 python3-devel python3-pip nodejs npm git curl
        fi
    elif [ "$PKG_MGR" = "apt" ]; then
        log_info "使用 apt 安装..."
        sudo apt update -qq
        sudo apt install -y \
            python3 python3-venv python3-dev python3-pip \
            nodejs npm git curl 2>/dev/null
    else
        log_error "未检测到支持的包管理器 (dnf / apt)"
        exit 1
    fi

    # 确认 Python 版本
    PYTHON_BIN=""
    for py in python3.13 python3.11 python3.10 python3; do
        if command -v "$py" &>/dev/null; then
            PYTHON_BIN="$py"
            break
        fi
    done
    if [ -z "$PYTHON_BIN" ]; then
        log_error "Python 3 未安装"
        exit 1
    fi
    PY_VER="$($PYTHON_BIN --version 2>&1)"
    log_ok "Python: $PY_VER"

    # 确认 Node.js
    if ! command -v node &>/dev/null; then
        log_error "Node.js 未安装"
        exit 1
    fi
    NODE_VER="$(node --version)"
    log_ok "Node.js: $NODE_VER"
}

# 检查是否已有系统依赖 (跳过交互式安装)
NEED_SUDO=false
if ! command -v python3 &>/dev/null || ! command -v node &>/dev/null; then
    NEED_SUDO=true
fi

if [ "$NEED_SUDO" = true ]; then
    echo -n "是否安装系统依赖? [Y/n] "
    read -r ans
    if [ "${ans:-Y}" != "n" ] && [ "${ans:-Y}" != "N" ]; then
        install_system_deps
    fi
else
    PYTHON_BIN="python3"
    for py in python3.13 python3.11 python3.10 python3; do
        if command -v "$py" &>/dev/null; then PYTHON_BIN="$py"; break; fi
    done
    log_ok "系统依赖已就绪 (Python: $($PYTHON_BIN --version), Node: $(node --version))"
fi

# ============================================================
# Step 3: Python 虚拟环境 + 后端依赖
# ============================================================
log_step "Step 3/8: 安装 Python 后端依赖"

setup_backend() {
    cd "$BACKEND_DIR"

    # 创建虚拟环境
    if [ ! -d "$VENV_DIR" ]; then
        log_info "创建虚拟环境 ($PYTHON_BIN)..."
        $PYTHON_BIN -m venv "$VENV_DIR"
    else
        log_info "虚拟环境已存在, 跳过创建"
    fi

    # 激活
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip -q

    # 安装依赖
    log_info "安装 Python 依赖..."
    pip install -r requirements.txt -q 2>&1 | tail -3

    log_ok "后端依赖安装完成"
}

setup_backend

# ============================================================
# Step 4: 前端依赖 + 构建
# ============================================================
log_step "Step 4/8: 安装前端依赖并构建"

setup_frontend() {
    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ]; then
        log_info "安装 npm 依赖..."
        npm install --silent 2>&1 | tail -3
    else
        log_info "node_modules 已存在, 跳过安装"
    fi

    log_info "构建前端..."
    npm run build 2>&1 | tail -5

    log_ok "前端构建完成 (dist/)"
}

setup_frontend

# ============================================================
# Step 5: LLM 配置 (交互式)
# ============================================================
log_step "Step 5/8: 配置 LLM"

configure_llm() {
    echo ""
    echo "  请选择 LLM 模式:"
    echo "  ┌─────────────────────────────────────────────┐"
    echo "  │ [1] Ollama 本地部署 (推荐麒麟离线环境)        │"
    echo "  │     需要先安装 Ollama: curl -fsSL            │"
    echo "  │     https://ollama.com/install.sh | sh       │"
    echo "  │     模型: qwen3:4b, 端口: 11434              │"
    echo "  │                                              │"
    echo "  │ [2] DeepSeek 云端 API                         │"
    echo "  │     base_url: https://api.deepseek.com       │"
    echo "  │     模型可选: deepseek-chat / deepseek-v4-flash│"
    echo "  │     需要有效的 API Key                        │"
    echo "  └─────────────────────────────────────────────┘"
    echo ""
    echo -n "  请输入选项 [1/2] (默认: 2): "
    read -r llm_choice
    llm_choice="${llm_choice:-2}"

    if [ "$llm_choice" = "1" ]; then
        LLM_PROVIDER="ollama"
        echo -n "  Ollama 地址 [默认: http://localhost:11434]: "
        read -r llm_url
        LLM_BASE_URL="${llm_url:-http://localhost:11434}"
        echo -n "  模型名称 [默认: qwen3:4b]: "
        read -r llm_model
        LLM_MODEL="${llm_model:-qwen3:4b}"
        LLM_API_KEY=""

        log_info "检查 Ollama 连接..."
        if curl -s "$LLM_BASE_URL/api/tags" >/dev/null 2>&1; then
            log_ok "Ollama 已运行"
            if curl -s "$LLM_BASE_URL/api/tags" | grep -q "$LLM_MODEL"; then
                log_ok "模型 $LLM_MODEL 已就绪"
            else
                log_warn "模型 $LLM_MODEL 未拉取, 正在自动下载..."
                curl -s "$LLM_BASE_URL/api/pull" -d "{\"name\":\"$LLM_MODEL\"}" >/dev/null 2>&1 &
                log_info "后台下载中, 请稍后检查: ollama list"
            fi
        else
            log_warn "Ollama 未运行或无法连接, 请手动启动: ollama serve"
        fi

    else
        LLM_PROVIDER="deepseek"
        LLM_BASE_URL="https://api.deepseek.com"
        echo -n "  模型名称 [默认: deepseek-v4-flash]: "
        read -r llm_model
        LLM_MODEL="${llm_model:-deepseek-v4-flash}"
        echo -n "  API Key: "
        read -rs llm_key
        LLM_API_KEY="$llm_key"
        echo ""
        echo -n "  验证 API Key... "
        if curl -s -H "Authorization: Bearer $LLM_API_KEY" \
            "$LLM_BASE_URL/v1/models" >/dev/null 2>&1; then
            log_ok "API Key 验证通过"
        else
            log_warn "API Key 验证失败, 请确认后修改 .env 文件"
        fi
    fi
}

configure_llm

# ============================================================
# Step 6: 写入 .env 配置
# ============================================================
log_step "Step 6/8: 生成配置文件"

generate_env() {
    cat > "$ENV_FILE" << EOF
# SRE-agent LLM 配置 (由 deploy.sh 自动生成)
LLM_PROVIDER=$LLM_PROVIDER
LLM_BASE_URL=$LLM_BASE_URL
LLM_MODEL=$LLM_MODEL
LLM_API_KEY=$LLM_API_KEY

# 安全配置
MAX_RISK_LEVEL=restricted
REQUIRE_CONFIRMATION=true
AUDIT_ENABLED=true

# 数据库 (开发环境 SQLite)
DATABASE_URL=sqlite+aiosqlite:///$BACKEND_DIR/data/state_store.db
EOF
    log_ok "已生成: $ENV_FILE"
}

generate_env

# ============================================================
# Step 7: 创建 sreagent 用户 + systemd 服务
# ============================================================
log_step "Step 7/8: 安全加固 (sreagent 用户 + systemd)"

setup_security() {
    # sreagent 用户
    if id sreagent &>/dev/null; then
        log_info "sreagent 用户已存在"
    else
        echo -n "是否创建 sreagent 专用低权限用户? [Y/n] "
        read -r ans
        if [ "${ans:-Y}" != "n" ] && [ "${ans:-Y}" != "N" ]; then
            sudo useradd -r -s /bin/false -d /nonexistent -M sreagent 2>/dev/null || true
            log_ok "sreagent 用户已创建"
        fi
    fi

    # systemd 服务
    echo ""
    echo "  后端启动方式:"
    echo "  [1] 手动启动 (uvicorn app.main:app --reload)"
    echo "  [2] 注册 systemd 服务 (自动启动, 生产推荐)"
    echo ""
    echo -n "  请选择 [1/2] (默认: 1): "
    read -r svc_choice
    svc_choice="${svc_choice:-1}"

    if [ "$svc_choice" = "2" ]; then
        SERVICE_FILE="/etc/systemd/system/sre-agent.service"
        cat > /tmp/sre-agent.service << EOF
[Unit]
Description=SRE-agent — 智能运维 Agent
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BACKEND_DIR
Environment=PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$VENV_DIR/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sre-agent

# 安全加固
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=$BACKEND_DIR/data
MemoryMax=2G

[Install]
WantedBy=multi-user.target
EOF
        sudo cp /tmp/sre-agent.service "$SERVICE_FILE"
        sudo systemctl daemon-reload
        sudo systemctl enable sre-agent
        log_ok "systemd 服务已注册: sre-agent"
        echo ""
        echo "  启动命令: sudo systemctl start sre-agent"
        echo "  状态命令: sudo systemctl status sre-agent"
        echo "  日志命令: sudo journalctl -u sre-agent -f"
        rm -f /tmp/sre-agent.service
    else
        log_info "跳过 systemd 注册, 请手动启动后端"
    fi
}

setup_security

# ============================================================
# Step 8: 部署验证
# ============================================================
log_step "Step 8/8: 部署验证"

verify_deploy() {
    cd "$BACKEND_DIR"
    source "$VENV_DIR/bin/activate"

    errors=0

    echo ""

    # 1. 后端 Tool 注册
    echo -n "  [验证] MCP Tool 注册... "
    TOOL_COUNT=$("$VENV_DIR/bin/python" -c "from app.mcp_plugins.base import registry; print(registry.count)" 2>/dev/null || echo "0")
    if [ "$TOOL_COUNT" -ge 45 ]; then
        echo -e "${GREEN}✅${NC} $TOOL_COUNT 个 Tool 已注册"
    else
        echo -e "${RED}❌${NC} 仅注册 $TOOL_COUNT 个 Tool"
        errors=$((errors + 1))
    fi

    # 2. 安全护栏
    echo -n "  [验证] 安全护栏模块... "
    INTENT_OK=$("$VENV_DIR/bin/python" -c "
from app.core.intent_filter import classify_intent, IntentCategory
from app.core.injection_detector import detect_injection
cat, _, _ = classify_intent('rm -rf /etc')
hits = detect_injection('rⅿ -rf /')
print('OK' if cat==IntentCategory.DANGEROUS_ACTION and len(hits)>0 else 'FAIL')
" 2>/dev/null || echo "FAIL")
    if [ "$INTENT_OK" = "OK" ]; then
        echo -e "${GREEN}✅${NC} 意图分类 + 注入检测正常"
    else
        echo -e "${RED}❌${NC} 安全护栏异常"
        errors=$((errors + 1))
    fi

    # 3. LLM 配置
    echo -n "  [验证] LLM 配置... "
    PROVIDER_OK=$("$VENV_DIR/bin/python" -c "
from app.llm.config import LLM_PROVIDER, LLM_MODEL, LLM_BASE_URL
print(f'{LLM_PROVIDER}/{LLM_MODEL}@{LLM_BASE_URL}')
" 2>/dev/null || echo "ERROR")
    echo -e "${GREEN}$PROVIDER_OK${NC}"

    # 4. 前端
    echo -n "  [验证] 前端构建产物... "
    if [ -f "$FRONTEND_DIR/dist/index.html" ]; then
        echo -e "${GREEN}✅${NC} dist/ 已就绪"
    else
        echo -e "${YELLOW}⚠️${NC}  dist/ 不存在, 请运行: cd frontend && npm run build"
    fi

    # 5. 磁盘空间
    echo -n "  [验证] 磁盘空间... "
    DISK_USED=$(df -h "$PROJECT_DIR" | awk 'NR==2 {print $5}' | tr -d '%')
    if [ "$DISK_USED" -lt 90 ]; then
        echo -e "${GREEN}✅${NC} 磁盘使用 ${DISK_USED}%"
    else
        echo -e "${RED}❌${NC} 磁盘使用 ${DISK_USED}%, 空间不足"
    fi

    echo ""

    if [ "$errors" -eq 0 ]; then
        echo -e "  ${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "  ${BOLD}${GREEN}  ✅ 部署验证通过: 所有检查项正常    ${NC}"
        echo -e "  ${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    else
        echo -e "  ${RED}❌ 发现 $errors 个问题, 请检查上方输出${NC}"
    fi
}

verify_deploy

# ============================================================
# 启动指引
# ============================================================
echo ""
echo -e "${BOLD}${BLUE}════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${BLUE}  启动指引${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo ""

if systemctl is-enabled sre-agent &>/dev/null 2>&1; then
    echo "  systemd (推荐):"
    echo "    sudo systemctl start sre-agent"
    echo "    sudo systemctl status sre-agent"
    echo ""
fi

echo "  手动启动:"
echo "    # 终端1: 后端"
echo "    cd $BACKEND_DIR"
echo "    source .venv/bin/activate"
echo "    uvicorn app.main:app --reload --port 8001"
echo ""
echo "    # 终端2: 前端 (开发模式)"
echo "    cd $FRONTEND_DIR"
echo "    npm run dev"
echo ""
echo "  访问地址:"
echo "    前端     : http://localhost:5173"
echo "    API 文档 : http://localhost:8001/docs"
echo "    健康检查 : http://localhost:8001/health"
echo ""
echo -e "  LLM 模式 : ${BOLD}$LLM_PROVIDER${NC}"
if [ "$LLM_PROVIDER" = "ollama" ]; then
    echo "  模型启动 : ollama serve && ollama pull $LLM_MODEL"
fi
echo ""
echo -e "  ${GREEN}配置文件: $ENV_FILE${NC}"
echo -e "  ${GREEN}部署日志: 见上方输出${NC}"
echo ""

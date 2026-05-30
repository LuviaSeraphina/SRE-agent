# SRE-agent 项目指南

## 项目定位
面向麒麟操作系统（Kylin OS）的智能运维 Agent，基于 MCP 协议构建，通过 LLM 实现安全、受控的系统管理。**安全第一：AI 绝不直接接触 Shell，所有操作必须经过 MCP 工具层。**

## 技术栈
- **后端**: Python 3.13 + FastAPI + MCP (Anthropic SDK)
- **前端**: Vue 3 + Vite + TypeScript + Pinia
- **模型**: DeepSeek / Qwen3
- **数据库**: SQLite (开发) / PostgreSQL (生产)

## 目录结构约定

```
backend/app/
├── api/            # REST 接口层（对话、看板、审计）
├── core/           # 安全核心（意图过滤、平台检测）
├── llm/            # LLM 适配层
├── mcp_plugins/    # MCP 运维插件（原子操作）
└── models/         # 数据模型
frontend/src/
├── views/          # 页面视图（Dashboard/Chat/AuditLog）
├── components/     # 组件（按 dashboard/common 分组）
├── stores/         # Pinia 状态管理
├── api/            # 前端 API 客户端
└── router/         # 路由配置
```

## 编码规范

### Python
- 所有 MCP 插件继承 `mcp_plugins/base.py`（Phase 2 实现注册中心后）
- 插件返回值使用 `_common.make_response()` 统一格式：`{tool, timestamp, risk_level, data, summary}`
- 异常必须通过 `_common.error_response()` 返回，**禁止**让 Tool 因未捕获异常而崩溃
- 每个插件必须声明 `risk_level`：`read_only` / `ops_action` / `dangerous`
- **禁止**在插件中直接使用 `os.system()` 或 `subprocess.run()` 拼接用户输入
- 所有命令执行通过 `_common.run_command()` 且参数必须是固定列表（非字符串拼接）
- `intent_filter.py` 是第一道安全防线，修改时需同步更新测试

### TypeScript/Vue
- Pinia stores 按功能拆分（chat / system / audit）
- API 调用统一通过 `src/api/client.ts`，不直接使用 fetch/axios
- 组件命名：`{功能}{类型}` 如 `CpuMemoryPanel.vue`、`StatusBadge.vue`

## 构建与测试

```bash
# 后端
cd backend && pip install -r requirements.txt
cd backend && pytest tests/ -v

# 前端
cd frontend && npm install
cd frontend && npm run dev        # 开发服务器
cd frontend && npm run build      # 生产构建
```

## 关键约定

- **安全护栏**: 任何涉及系统变更的操作，必须先确认 `intent_filter.py` 已审查通过
- **MCP 协议**: Tool 参数必须通过 `inputSchema` JSON Schema 校验
- **日志规范**: 高危操作记录到审计日志，标记 `risk_level`
- **禁止模式**: `rm -rf`、`chmod 777`、`iptables -F` 等破坏性命令不得作为 MCP Tool 暴露

# SRE-agent — 面向麒麟操作系统的安全智能运维 Agent

> 第十五届中国软件杯大赛 A 组赛题 | 出题企业：麒麟软件有限公司

---

## 项目简介

基于 MCP 协议构建的智能运维 Agent，作为自然语言与 Linux 操作系统交互的安全桥梁。大模型通过调用封装好的 MCP Tool 感知系统状态、执行运维任务——**AI 永远不直接接触 Shell**。

### 核心亮点

| 亮点 | 说明 |
|------|------|
| 🔒 三层安全护栏 | 意图过滤 → 注入检测 → 最小权限代理，全链路防护 |
| 🔧 21 个 MCP Tool | 进程/网络/磁盘/内存/安全/系统，6 大类全覆盖 |
| 🖥️ 麒麟 OS 适配 | 自动检测 dnf/nftables/龙芯架构，兼容通用 Linux |
| 🧠 LLM 本地部署 | Ollama + Qwen3，纯 CPU 可运行 |
| 🎨 Vue 3 前端 | 对话/仪表盘/审计日志三页面，SSE 流式输出 |

---

## 架构

```
用户 (Web UI) ──→ FastAPI ──→ registry.call() ──→ MCP Tool 执行
                      │               │
                 ┌────┴────┐    ┌─────┴──────┐
                 │ 安全护栏 │    │ 21 Tools   │
                 │ intent   │    │ process    │
                 │ injection│    │ disk       │
                 │ permission│   │ network    │
                 └─────────┘    │ memory     │
                                │ security ⭐│
                                │ system     │
                                └───────────┘
                      │
                 LLM (Ollama / DeepSeek / Qwen3)
```

---

## 快速启动

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

# 前端
cd frontend
npm install
npm run dev

# LLM (可选)
ollama serve && ollama pull qwen3:4b
```

| 服务 | 地址 | 用途 |
|------|------|------|
| 后端 API | `http://localhost:8001/health` | MCP Tool 调用 + 安全护栏 |
| Swagger | `http://localhost:8001/docs` | API 文档 |
| 前端 | `http://localhost:5173` | 对话/仪表盘/审计 |

---

## 安全护栏体系

```
用户输入
  → ① intent_filter.classify_intent()     四层意图分类
  → ② injection_detector.detect_injection() 注入检测
  → ③ injection_detector.validate_llm_output() LLM 输出校验
  → ④ permission_agent.check_permission()   risk_level 权限预检
  → ⑤ _common.run_command()                命令白名单拦截
  → ⑥ registry.call()                      统一执行入口
```

| 文件 | 职责 |
|------|------|
| `core/intent_filter.py` | 意图分类 (JAILBREAK/DANGEROUS/OPS/SAFE) |
| `core/injection_detector.py` | 注入检测 + LLM 输出二次校验 |
| `core/permission_agent.py` | 最小权限代理 + 系统保护名单 |
| `mcp_plugins/_common.py` | 命令白名单 + 高危参数拦截 |
| `mcp_plugins/base.py` | 注册中心 call() 接入权限预检 |

---

## MCP 插件 (21 Tools)

| 插件 | Tool | 说明 |
|------|------|------|
| **process** | `process_inspect` | 进程列表，按状态/CPU/内存排序 |
| **disk** | `disk_inspect` | 磁盘空间，指定挂载点 |
| **network** | `network_listening_ports` | 监听端口审计 |
| | `network_connections_summary` | TCP 状态 (CLOSE_WAIT 告警) |
| | `network_interface_stats` | 网卡流量/丢包/错误 |
| **memory** | `memory_info` | 物理内存画像 |
| | `swap_info` | Swap 使用率 |
| | `memory_oom_history` | OOM Killer 历史 |
| **security** ⭐ | `security_auth_failures` | SSH/su/sudo 多源认证失败 |
| | `security_active_sessions` | 活跃会话 + SSH 连接 |
| | `security_suid_scan` | SUID/SGID 后门扫描 |
| | `security_crontab_audit` | crontab 持久化检测 |
| | `security_kernel_modules` | 内核模块审计 |
| | `security_pending_updates` | 安全更新检测 (dnf/apt) |
| | `security_user_audit` | 空密码/UID=0/NOPASSWD |
| | `security_sysctl_audit` | 12 项内核安全参数基线 |
| | `user_list` | 用户与组查询 |
| **system** | `system_info` | 系统概览 + 麒麟平台检测 |
| | `system_load` | 负载 + 过载判断 |
| | `system_failed_services` | 失败 systemd 服务 |
| | `system_boot_params` | 内核启动参数安全审计 |

---

## 项目结构

```
SRE-agent/
├── backend/
│   ├── app/
│   │   ├── core/                     # 安全护栏核心引擎
│   │   │   ├── intent_filter.py      # 意图风险过滤器
│   │   │   ├── injection_detector.py # Prompt 注入检测
│   │   │   ├── permission_agent.py   # 最小权限执行代理
│   │   │   └── platform_detect.py    # 麒麟 OS 平台检测
│   │   ├── mcp_plugins/             # MCP 插件 (6 大类 21 Tools)
│   │   │   ├── base.py              # 注册中心 + 风险预检
│   │   │   ├── _common.py           # 共享工具 + 命令白名单
│   │   │   ├── process_plugin.py    # 进程感知
│   │   │   ├── disk_plugin.py       # 磁盘感知
│   │   │   ├── network_plugin.py    # 网络感知
│   │   │   ├── memory_plugin.py     # 内存 + OOM 感知
│   │   │   ├── security_plugin.py   # 安全态势 (9 Tools)
│   │   │   └── system_plugin.py     # 系统健康感知
│   │   ├── api/                     # REST API
│   │   ├── llm/                     # LLM 集成
│   │   └── models/                  # 数据模型
│   └── tests/
│       └── test_security.py         # 渗透测试用例
├── frontend/                        # Vue 3 + Element Plus
│   └── src/
│       ├── views/                   # ChatView/DashboardView/AuditLogView
│       ├── components/              # chat/dashboard/audit/common
│       ├── api/                     # SSE 流式/仪表盘/审计 API
│       ├── stores/                  # Pinia (chat/system/audit)
│       └── router/                  # Vue Router
├── docs/                            # 比赛文档
└── scripts/                         # 部署脚本
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.13 + FastAPI |
| MCP | 自研 Plugin 系统 + MCPTool Registry |
| 前端 | Vue 3 + Element Plus + ECharts + Pinia |
| LLM | Qwen3 (Ollama) / DeepSeek |
| 安全 | 3 层护栏 + 命令白名单 + 高危参数拦截 |
| 数据库 | SQLite |
| 部署 | 麒麟 V11 / LoongArch / 通用 Linux |

---

## License

MIT

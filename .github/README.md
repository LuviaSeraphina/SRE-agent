# .github/ — SRE-agent Copilot 定制化使用指南

## 目录结构

```
.github/
├── copilot-instructions.md              # [全局] 项目编码规范，每次对话自动生效
├── instructions/
│   └── sre-mcp-plugin.instructions.md    # [按文件] 编辑 MCP 插件时自动注入
├── agents/
│   └── sre-security-reviewer.agent.md    # [按需] 安全审查专用子 agent
├── skills/
│   └── sre-postmortem/                   # [按需] 事后分析工作流
│       ├── SKILL.md                      #   工作流定义
│       └── templates/postmortem.md       #   报告模板
└── hooks/
    ├── pre-commit-safety.json            # [自动] PreToolUse 安全护栏配置
    └── scripts/
        └── safety-check.sh               #   安全检查脚本
```

---

## 1. `copilot-instructions.md` — 全局编码规范

### 作用
每次 Copilot Chat 对话**自动加载**，让 AI 始终了解项目结构、技术栈和编码约定。

### 如何使用
**无需手动操作**，创建后自动生效。Copilot 在回答任何问题时都会参考这个文件。

### 内容概要
- 项目定位：麒麟 OS 智能运维 Agent
- 技术栈：Python 3.13 + FastAPI + Vue 3
- 目录结构约定
- Python/TypeScript 编码规范
- 构建与测试命令
- 安全护栏（禁止直接 shell、禁止 rm -rf 等）

### 修改方式
直接编辑 `.github/copilot-instructions.md`，保存后下一轮对话即生效。

---

## 2. `instructions/sre-mcp-plugin.instructions.md` — MCP 插件开发规范

### 作用
当你**编辑 `backend/app/mcp_plugins/` 目录下的 .py 文件时**，自动注入到对话上下文中。

### 触发条件
- **自动触发**：打开或编辑 `backend/app/mcp_plugins/**/*.py` 文件时
- **手动附加**：在 Chat 中点击 `Add Context` → `Instructions` → 选择该文件

### 内容概要
- Schema 定义模板（name + inputSchema + risk_level）
- Handler 函数规范（make_response + error_response）
- 禁止模式（拼接用户输入到命令、不捕获异常）
- 新增插件 Checklist（7 步）

### 适用场景
- 新写一个 MCP 插件（如 memory_plugin.py）
- 修改现有插件的 handler 逻辑
- 审查插件是否符合规范

---

## 3. `agents/sre-security-reviewer.agent.md` — 安全审查 Agent

### 作用
一个**只读权限**的专用子 agent，专门审查代码中的安全风险。

### 触发方式

| 方式 | 操作 |
|------|------|
| **自动委托** | 主 agent 检测到安全相关任务时自动调用 |
| **手动选择** | Chat 输入框左侧 Agent 选择器 → 选择 "sre-security-reviewer" |
| **关键词触发** | 对话中提到 "审查安全" "安全检查" "注入风险" "安全审计" |

### 审查范围
1. MCP 插件注入风险 — `run_command()` 是否拼接用户输入
2. 正则表达式安全 — ReDoS、绕过风险
3. intent_filter.py — 意图分类是否完备
4. risk_level 一致性 — 声明与实际操作是否匹配

### 输出格式
分级报告：🔴 严重 → ⚠️ 警告 → ✅ 通过

### 约束
- 只能 `read` + `search`，不能修改代码
- 不执行任何命令或测试

---

## 4. `skills/sre-postmortem/` — 事后分析 Skill

### 作用
按照无指责文化（blameless）生成结构化的故障复盘报告。

### 触发方式

| 方式 | 操作 |
|------|------|
| **斜杠命令** | 在 Chat 输入 `/` → 选择 "sre-postmortem" |
| **关键词触发** | 提到 "事后分析" "故障复盘" "postmortem" "5 Whys" "根因分析" |

### 使用示例

```
/sre-postmortem 昨天下午 /metrics 端点 503，持续 8 分钟
```

### 执行流程
1. 收集基本信息（时间窗口、影响范围）
2. 从 MCP 插件数据构建事件时间线
3. 对照 SLI/SLO 计算错误预算消耗
4. 5 Whys 根因分析
5. 生成改进措施（预防/检测/缓解）
6. 输出符合模板格式的 Markdown 报告

### 关联文件
- `templates/postmortem.md` — 报告模板
- `/home/liliana0521/SRE-STUDY/docs/SLI_SLO.md` — 错误预算参考

---

## 5. `hooks/pre-commit-safety.json` — 安全护栏 Hook

### 作用
在 Copilot **每次执行终端命令前**自动运行安全检查，拦截危险操作。

### 触发条件
**自动触发**，无需手动操作。当 Copilot 准备执行 shell 命令时自动运行 `safety-check.sh`。

### 拦截规则

| 危险操作 | 动作 | 示例 |
|----------|------|------|
| `rm -rf /` 等关键路径 | 🚫 直接拦截 | `rm -rf /etc` |
| `chmod 777` | 🚫 直接拦截 | `chmod 777 /var/www` |
| `iptables -F` | 🚫 直接拦截 | 清空防火墙规则 |
| `dd` 写入块设备 | 🚫 直接拦截 | `dd if=... of=/dev/sda` |
| `os.system()` / `subprocess.run(shell=True)` | 🚫 直接拦截 | 绕过 MCP 层 |
| `mkfs.*` | ⚠️ 弹窗确认 | 格式化磁盘 |

### 修改方式
- 添加新规则：编辑 `hooks/scripts/safety-check.sh`，按现有模式追加 grep 检查
- 调整行为：改 `deny` → `ask`（拦截改为确认），或 `deny` → `allow`（放行）

---

## 六种原语对比

| 原语 | 文件 | 触发时机 | 适合场景 |
|------|------|----------|----------|
| **Instructions** (全局) | `copilot-instructions.md` | 每次对话自动 | 项目级编码规范 |
| **Instructions** (按文件) | `*.instructions.md` | 编辑匹配文件时 | 特定模块开发规范 |
| **Agent** | `*.agent.md` | 手动选择 / 自动委托 | 专用角色（安全审查等） |
| **Skill** | `SKILL.md` | `/` 命令 / 关键词 | 多步骤工作流 |
| **Prompt** | `*.prompt.md` | `/` 命令 | 单次生成任务 |
| **Hook** | `*.json` | 工具调用前后自动 | 强制执行的安全策略 |

---

## 添加新定制文件

### 添加新的 Instructions（按文件类型）

1. 在 `.github/instructions/` 下创建 `xxx.instructions.md`
2. 添加 frontmatter：
```yaml
---
description: "Use when: {触发关键词}"
applyTo: "{glob 匹配模式}"
---
```
3. 编写规范内容

### 添加新的 Agent

1. 在 `.github/agents/` 下创建 `xxx.agent.md`
2. 添加 frontmatter：
```yaml
---
description: "{描述，含 Use when: 关键词}"
tools: [read, search]    # 限制可用工具
---
```
3. 定义角色、约束、输出格式

### 添加新的 Skill

1. 创建 `.github/skills/<name>/` 目录
2. 创建 `SKILL.md`（name 必须与目录名一致）
3. 可选：添加 `templates/`、`scripts/` 子目录

### 添加新的 Hook

1. 在 `.github/hooks/` 下创建 `xxx.json`
2. 在 `hooks/scripts/` 下创建对应的检查脚本
3. 设置脚本可执行权限：`chmod +x .github/hooks/scripts/xxx.sh`

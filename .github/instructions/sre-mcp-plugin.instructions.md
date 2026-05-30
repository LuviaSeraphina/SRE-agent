---
description: "Use when: creating or modifying MCP plugins in backend/app/mcp_plugins/. Covers tool definition, input schema, handler implementation, and security patterns."
applyTo: "backend/app/mcp_plugins/**/*.py"
---

# MCP 插件开发规范

## 文件结构

每个插件文件必须包含：
1. **Schema 定义** — `{name}_schema` dict，含 `name`、`description`、`inputSchema`
2. **Handler 函数** — `{name}_handler()` 实现具体逻辑
3. **`__init__.py` 注册** — 新增插件后同步更新

## Schema 模板

```python
disk_inspect_schema = {
    "name": "disk_inspect",
    "description": "获取磁盘信息,可定义具体路径",
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "default": "/", "description": "挂载点路径"}
        }
    },
    "risk_level": "read_only"   # 必须声明
}
```

## Handler 规范

### 必须遵守
- 所有 Handler 通过 `_common.make_response()` 返回结果
- 所有异常通过 `_common.error_response()` 捕获
- `risk_level` 必须与实际操作匹配：
  - `read_only` — 纯查询（psutil / ss -tlnp / journalctl --no-pager）
  - `ops_action` — 有副作用的运维操作
  - `dangerous` — 可能破坏系统的操作（需额外审批）

### 禁止模式

```python
# ❌ 禁止: 拼接用户输入到命令
_run_command(["grep", user_input, "/var/log/messages"])

# ✅ 正确: 固定参数，用 Python 做过滤
output = _run_command(["journalctl", "--no-pager", "-t", "sshd", "--since", "1h ago"])
matches = [line for line in output.split("\n") if user_filter in line]
```

```python
# ❌ 禁止: 让异常向上传播
def disk_inspect_handler(path="/"):
    disk_info = psutil.disk_usage(path)  # 若 path 不存在，NoSuchProcess 会崩溃

# ✅ 正确: 捕获并返回 error_response
def disk_inspect_handler(path="/"):
    try:
        disk_info = psutil.disk_usage(path)
        return _make_response(...)
    except Exception as e:
        return _error_response("disk_inspect_handler", e)
```

## 新增插件 Checklist

1. [ ] 创建 `xxx_plugin.py`，定义 schema + handler
2. [ ] 在 `mcp_plugins/__init__.py` 中注册新 tool
3. [ ] `risk_level` 声明正确
4. [ ] 所有 handler 路径都有 try/except
5. [ ] 不拼接用户输入到 shell 命令
6. [ ] 运行 `pytest tests/ -v` 通过

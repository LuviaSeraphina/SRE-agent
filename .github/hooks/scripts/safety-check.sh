#!/bin/bash
# SRE-agent 安全护栏 Hook — PreToolUse
# 在 Copilot 执行任何工具前检查，拦截危险操作
# 读取 stdin 的 JSON，匹配危险模式，返回 permission decision

set -euo pipefail

# 读取 Hook 传入的 JSON
INPUT=$(cat)

# 提取 tool_name 和 command（如果存在）
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")
TOOL_INPUT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('tool_input',{})))" 2>/dev/null || echo "{}")

# 只检查 execute 类型的工具调用
if [ "$TOOL_NAME" != "execute" ] && [ "$TOOL_NAME" != "run_in_terminal" ]; then
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'
    exit 0
fi

# 提取命令字符串
COMMAND=$(echo "$TOOL_INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    cmd = d.get('command', '') or d.get('cmd', '') or ''
    if isinstance(cmd, list):
        cmd = ' '.join(str(x) for x in cmd)
    print(cmd)
except:
    print('')
" 2>/dev/null || echo "")

# 无命令则放行
if [ -z "$COMMAND" ]; then
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'
    exit 0
fi

# ============================================
# 危险模式检查
# ============================================

# 模式 1: 递归强制删除根目录或关键路径
if echo "$COMMAND" | grep -qE '\brm\s+-rf\s+/(\s|$)' || \
   echo "$COMMAND" | grep -qE '\brm\s+-rf\s+/etc(\s|$)' || \
   echo "$COMMAND" | grep -qE '\brm\s+-rf\s+/var(\s|$)' || \
   echo "$COMMAND" | grep -qE '\brm\s+-rf\s+/home(\s|$)'; then
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"危险操作: 禁止递归强制删除关键目录 (rm -rf /)"}}'
    exit 0
fi

# 模式 2: chmod 777
if echo "$COMMAND" | grep -qE '\bchmod\s+777\b'; then
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"危险操作: 禁止 chmod 777（过度放宽权限）"}}'
    exit 0
fi

# 模式 3: iptables -F（清空防火墙规则）
if echo "$COMMAND" | grep -qE '\biptables\s+-F\b'; then
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"危险操作: 禁止 iptables -F（清空防火墙规则）"}}'
    exit 0
fi

# 模式 4: 直接写磁盘 (dd) 到块设备
if echo "$COMMAND" | grep -qE '\bdd\s+if=.*\s+of=/dev/[a-z]+'; then
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"危险操作: 禁止 dd 直接写入块设备"}}'
    exit 0
fi

# 模式 5: 绕过 MCP 层直接调用 shell
if echo "$COMMAND" | grep -qE '\bos\.system\(' || \
   echo "$COMMAND" | grep -qE '\bsubprocess\.run\(.*shell\s*=\s*True'; then
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"违反安全原则: 禁止绕过 MCP 层直接使用 os.system() 或 subprocess.run(shell=True)"}}'
    exit 0
fi

# 模式 6: 格式化/挂载危险操作 (mkfs, mount 敏感目录)
if echo "$COMMAND" | grep -qE '\bmkfs\.'; then
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"需要确认: mkfs 格式化操作"}}'
    exit 0
fi

# 所有检查通过，放行
echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'
exit 0

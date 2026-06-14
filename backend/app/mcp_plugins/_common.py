"""
MCP 插件共享工具 — 所有插件复用
"""
import logging
import os
import re
import subprocess
from datetime import datetime

""" 
方法: make_response(), 统一构建 MCP Tool 返回结构
"""
def make_response(tool, data, summary, risk_level="read_only"):
    return {
        "tool": tool,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "risk_level": risk_level,
        "data": data,
        "summary": summary,
    }
""" 
方法: error_response(), 异常时返回统一错误结构, 保证所有 Tool 不会因未捕获异常而崩溃
"""
def error_response(tool, error):
    return {
        "tool": tool,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "risk_level": "error",
        "data": {},
        "summary": {"error": str(error)},
    }

# 允许执行的命令白名单 (只有这些命令可通过 run_command 执行)
_ALLOWED_COMMANDS={
    "ss","ip","who","find","lsmod","systemctl",
    "journalctl","dmesg","cat","crontab","sysctl",
    "docker","podman","which","dnf","yum","apt",
    "iptables","nft","getenforce","aa-status","dig","getent",
}

# 高危参数模式 — 分三类匹配, 避免子串误伤 (如 rm 匹配 format)
#   词边界: alphabetic 模式使用 \b 边界, 只匹配独立单词
#   精确:   flag 模式匹配完整参数
#   子串:   操作符匹配任意位置
_DANGEROUS_WORD={"rm","mkfs","dd","shutdown","reboot","poweroff","halt","chmod","chown"}
_DANGEROUS_FLAG={"-rf","-r"}
_DANGEROUS_SUBSTR={">",">>","&&"}

#方法: 在 run_command 前校验命令安全性
def _is_safe_command(cmd):
    #命令本身不在白名单
    if not cmd:
        return False, "空命令"
    base=cmd[0]
    if base not in _ALLOWED_COMMANDS:
        return False,f"命令 '{base}' 不在白名单内"

    #参数中检测高危模式
    for arg in cmd[1:]:
        #词边界匹配 (防子串误伤: format/perform/confirm/-perm)
        for pattern in _DANGEROUS_WORD:
            if re.search(r'\b' + re.escape(pattern) + r'\b', arg):
                return False,f"参数 '{arg[:50]}' 包含高危模式 '{pattern}'"
        #精确匹配 flag
        for pattern in _DANGEROUS_FLAG:
            if arg==pattern:
                return False,f"参数 '{arg[:50]}' 包含高危模式 '{pattern}'"
        #子串匹配 shell 操作符
        for pattern in _DANGEROUS_SUBSTR:
            if pattern in arg:
                return False,f"参数 '{arg[:50]}' 包含高危模式 '{pattern}'"

    return True, ""

_logger=logging.getLogger("sre_agent.mcp")

"""
方法: run_command(), 安全执行固定参数命令

成功时返回 stdout 字符串, 正常无输出返回 ""。
执行失败时返回 None 并记录 stderr, 以便上层显式上报。
"""
def run_command(cmd, timeout=10):
    #安全校验
    safe,reason=_is_safe_command(cmd)
    if not safe:
       _logger.warning(f"命令拦截: {' '.join(cmd[:3])} — {reason}")
       return None

    try:
        result=subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        stdout=result.stdout.strip()
        stderr=(result.stderr or "").strip()
        if result.returncode!=0 and not stdout:
            _logger.warning(f"命令执行失败: {' '.join(cmd)} (rc={result.returncode}){f' stderr={stderr}' if stderr else ''}")
            return None
        if result.returncode!=0 and stderr:
            _logger.warning(f"命令返回非 0: {' '.join(cmd)} (rc={result.returncode}){f' stderr={stderr}' if stderr else ''}")
        return stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        _logger.warning(f"命令执行异常: {' '.join(cmd)} — {e}")
        return None

"""
方法: journalctl_available(), 检测 journalctl 是否可用
"""
def journalctl_available():
    return os.path.exists("/usr/bin/journalctl") or os.path.exists("/bin/journalctl")

"""
方法: read_log_file(), 安全读取日志文件最后 max_lines 行
"""
def read_log_file(path, max_lines=2000):
    if not os.path.exists(path) or not os.access(path, os.R_OK):
        return []
    try:
        with open(path, "r", errors="ignore") as f:
            lines=f.readlines()
            return [line.strip() for line in lines[-max_lines:]]
    except (PermissionError, OSError):
        return []
        
"""
方法: alert_if(), 告警句式生产辅助
"""
#方法: 告警句式辅助
def alert_if(condition, template, *args):
    return template.format(*args) if condition else ""
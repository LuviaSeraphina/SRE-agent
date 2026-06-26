"""
MCP 插件共享工具 — 所有插件复用
"""
import logging
import os
import re
import subprocess
import time
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


"""
方法: sanitize_response(), 响应脱敏 — 自动移除工具返回数据中的敏感字段

设计原则:
- summary 字段完全保留 (已经是摘要, 无线索)
- data 字段按白名单过滤: 未在 keep 列表中的字段被删除
- 不在脱敏规则中的 tool 原样返回 (不误删)
"""
# 脱敏规则: tool_name → data 中允许保留的字段 (白名单)
_SANITIZE_RULES = {
    # ── 用户/权限类 ──
    "user_list": {
        "keep_data": ["users"],  # users 列表中的每项过滤
        "keep_user_fields": ["name", "is_system"],  # 删 uid/gid/home/shell
        "keep_groups": True, "keep_group_fields": ["name", "gid"],  # groups 保留 name+gid, 删 members
    },
    "security_user_audit": {
        "keep_data": ["issues_count", "issues"],
        "keep_issue_fields": ["type", "severity"],  # 删 user/detail
        "redact_count": True,  # issues 仅保留统计, 不列具体项
    },
    "security_user_privilege": {
        "keep_data": ["username", "sudo_access", "home_permission", "source"],
        "redact_username": True,  # username 替换为 "***"
    },
    # ── 会话/认证类 ──
    "security_auth_failures": {
        "keep_data": ["total_failures", "by_type_summary", "sources_count"],
        "keep_detail_fields": [],  # 不保留 failed_ips / failed_users 明细
    },
    "security_active_sessions": {
        "keep_data": ["session_count", "ssh_connection_count"],
        # 不保留 sessions[].user/from_ip/pid 和 ssh_connections[].remote
    },
    # ── 进程类 ──
    "process_detail": {
        "keep_process_fields": ["pid", "name", "status", "cpu_percent", "memory_percent", "num_threads", "create_time"],
        # 删 exe / cwd / username / num_fds / memory_info_rss_mb
    },
    "process_detail_handler": {
        "keep_process_fields": ["pid", "name", "status", "cpu_percent", "memory_percent", "num_threads", "create_time"],
    },
    # ── 网络类 ──
    "network_listening_ports": {
        "keep_data": ["port_count", "ports"],
        "keep_port_fields": ["port", "proto"],  # 删 bind/process/pid
    },
    "network_interface_stats": {
        "keep_data": ["interface_count", "interfaces"],
        "keep_iface_fields": ["name", "state", "rx_bytes", "tx_bytes", "rx_errors", "tx_errors", "rx_dropped", "tx_dropped"],
        # 删 mac / ipv4 / ipv6 / driver
    },
    "network_dns_check": {
        "keep_data": ["domain", "dns_server", "count", "source"],
        # 删 resolved_ips (具体 IP 列表)
    },
    # ── 文件/磁盘类 ──
    "disk_mount_audit": {
        "keep_data": ["mounts", "mount_count", "suspicious"],
        "keep_mount_fields": ["mountpoint", "fstype", "security_flags"],
        # 删 device / opts
    },
    "disk_large_files": {
        "keep_data": ["file_count", "scan_path"],
        # 删 files[].path (完整路径)
    },
    "security_suid_scan": {
        "keep_data": ["total_files", "suspicious_count", "suspicious_files"],
        "keep_suid_fields": ["permissions", "suspicious"],
        # 删 files[].path / files[].owner
    },
    # ── 定时任务/启动类 ──
    "security_crontab_audit": {
        "keep_data": ["total_entries", "suspicious_count", "suspicious_entries"],
        "keep_cron_fields": ["user", "suspicious", "matched_keywords"],
        # 删 entries[].entry (完整命令)
    },
    "system_boot_params": {
        "keep_data": ["security_checks", "missing_security_params", "raw_preview"],
        # 删 raw (完整 cmdline)
    },
    # ── 日志类 ──
    "system_journal_query": {
        "keep_data": ["total", "filter", "entries"],
        "keep_journal_fields": ["timestamp", "service", "priority"],
        # 删 entries[].hostname / message / pid
    },
    "system_journal_tail": {
        "keep_data": ["priority", "lines_requested", "entries"],
        "keep_journal_fields": ["timestamp", "service", "priority"],
    },
    # ── 容器类 ──
    "container_inspect": {
        "keep_data": ["id", "name", "image", "env_count", "privileged"],
        # 删 capabilities / mounts
    },
    "container_list": {
        "keep_data": ["containers", "count", "runtime"],
        "keep_container_fields": ["id", "name", "image", "status"],
        # 删 ports
    },
    # ── 系统信息 ──
    "system_info": {
        "keep_data": ["os", "distro", "kernel", "arch", "boot_time", "cpu_cores_logical", "cpu_cores_physical", "pkg_manager", "firewall", "is_kylin", "display_name"],
        # 删 hostname
    },
}

def sanitize_response(tool_name, response):
    """根据工具名对响应数据脱敏, 返回清理后的 response dict"""
    if tool_name is None:
        return response
    rules = _SANITIZE_RULES.get(tool_name)
    if rules is None:
        return response  # 无规则, 原样返回

    data = response.get("data", {})
    if not isinstance(data, dict):
        return response

    cleaned = {}

    # 1. 白名单过滤 data 顶层字段
    keep_data = rules.get("keep_data", [])
    if keep_data:
        for key in keep_data:
            if key in data:
                cleaned[key] = data[key]
    else:
        cleaned = dict(data)  # 无顶层白名单, 保留全部

    # 2. 对 users 列表中的每项过滤
    if "keep_user_fields" in rules and "users" in cleaned and isinstance(cleaned.get("users"), list):
        keepf = set(rules["keep_user_fields"])
        cleaned["users"] = [{k: v for k, v in u.items() if k in keepf} for u in cleaned["users"]]

    # 3. 对 groups 列表过滤
    if "keep_group_fields" in rules and "groups" in cleaned and isinstance(cleaned.get("groups"), list):
        keepf = set(rules["keep_group_fields"])
        cleaned["groups"] = [{k: v for k, v in g.items() if k in keepf} for g in cleaned["groups"]]

    # 4. issues 仅保留计数
    if rules.get("redact_count") and "issues" in cleaned is not None:
        cleaned["issues"] = f"[{len(cleaned['issues'])} 项, 已脱敏]"

    # 5. username 脱敏
    if rules.get("redact_username"):
        if "username" in cleaned:
            cleaned["username"] = "***"

    # 6. process 对象过滤
    if "keep_process_fields" in rules and "process" in cleaned and isinstance(cleaned.get("process"), dict):
        keepf = set(rules["keep_process_fields"])
        cleaned["process"] = {k: v for k, v in cleaned["process"].items() if k in keepf}

    # 7. ports 列表中每项过滤
    if "keep_port_fields" in rules and "ports" in cleaned and isinstance(cleaned.get("ports"), list):
        keepf = set(rules["keep_port_fields"])
        cleaned["ports"] = [{k: v for k, v in p.items() if k in keepf} for p in cleaned["ports"]]

    # 8. interfaces 列表过滤
    if "keep_iface_fields" in rules and "interfaces" in cleaned and isinstance(cleaned.get("interfaces"), list):
        keepf = set(rules["keep_iface_fields"])
        cleaned["interfaces"] = [{k: v for k, v in iface.items() if k in keepf} for iface in cleaned["interfaces"]]

    # 9. mounts 列表过滤
    if "keep_mount_fields" in rules and "mounts" in cleaned and isinstance(cleaned.get("mounts"), list):
        keepf = set(rules["keep_mount_fields"])
        cleaned["mounts"] = [{k: v for k, v in m.items() if k in keepf} for m in cleaned["mounts"]]

    # 10. suspicious_files / files 列表过滤
    if "keep_suid_fields" in rules and "suspicious_files" in cleaned and isinstance(cleaned.get("suspicious_files"), list):
        keepf = set(rules["keep_suid_fields"])
        cleaned["suspicious_files"] = [{k: v for k, v in f.items() if k in keepf} for f in cleaned["suspicious_files"]]

    # 11. crontab entries 过滤
    if "keep_cron_fields" in rules and "suspicious_entries" in cleaned and isinstance(cleaned.get("suspicious_entries"), list):
        keepf = set(rules["keep_cron_fields"])
        cleaned["suspicious_entries"] = [{k: v for k, v in e.items() if k in keepf} for e in cleaned["suspicious_entries"]]

    # 12. journal entries 过滤
    if "keep_journal_fields" in rules and "entries" in cleaned and isinstance(cleaned.get("entries"), list):
        keepf = set(rules["keep_journal_fields"])
        cleaned["entries"] = [{k: v for k, v in e.items() if k in keepf} for e in cleaned["entries"]]

    # 13. containers 列表过滤
    if "keep_container_fields" in rules and "containers" in cleaned and isinstance(cleaned.get("containers"), list):
        keepf = set(rules["keep_container_fields"])
        cleaned["containers"] = [{k: v for k, v in c.items() if k in keepf} for c in cleaned["containers"]]

    response["data"] = cleaned
    return response

# 允许执行的命令白名单 (只有这些命令可通过 run_command 执行)
_ALLOWED_COMMANDS={
    "ss","ip","who","find","lsmod","systemctl",
    "journalctl","dmesg","cat","crontab","sysctl",
    "docker","podman","which","dnf","yum","apt",
    "iptables","nft","getenforce","aa-status","dig","getent",
    "dmidecode","groups",
}

# 高危参数模式 — 分三类匹配, 避免子串误伤 (如 rm 匹配 format)
#   词边界: alphabetic 模式使用 \b 边界, 只匹配独立单词
#   精确:   flag 模式匹配完整参数
#   子串:   操作符匹配任意位置
_DANGEROUS_WORD={"rm","mkfs","dd","shutdown","reboot","poweroff","halt","chmod","chown"}
_DANGEROUS_FLAG={"-rf","-r"}
_DANGEROUS_SUBSTR={">",">>","&&",";","|","`","$(","${"}

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

_logger=logging.getLogger("xikiy_aiops.mcp")

"""
方法: run_command(), 安全执行固定参数命令

v2: 返回结构化 dict {stdout, stderr, exit_code, duration_ms}
    而非原始字符串, 以便上层采集真实执行数据用于异常回溯。

成功时 stdout 为命令输出, stderr 可能为空或有 warning。
执行失败时 stdout 为空字符串, stderr 包含错误信息。
"""
def run_command(cmd, timeout=10):
    #安全校验
    safe,reason=_is_safe_command(cmd)
    if not safe:
        _logger.warning(f"命令拦截: {' '.join(cmd[:3])} — {reason}")
        return {"stdout":"","stderr":reason,"exit_code":-1,"duration_ms":0,"blocked":True}

    start=time.monotonic()
    try:
        result=subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        elapsed_ms=int((time.monotonic() - start) * 1000)
        stdout=result.stdout.strip()
        stderr=(result.stderr or "").strip()
        exit_code=result.returncode

        if exit_code!=0 and not stdout:
            _logger.warning(f"命令执行失败: {' '.join(cmd)} (rc={exit_code}){f' stderr={stderr}' if stderr else ''}")
        elif exit_code!=0 and stderr:
            _logger.warning(f"命令返回非 0: {' '.join(cmd)} (rc={exit_code}){f' stderr={stderr}' if stderr else ''}")

        return {
            "stdout":stdout,
            "stderr":stderr,
            "exit_code":exit_code,
            "duration_ms":elapsed_ms,
            "blocked":False,
        }
    except subprocess.TimeoutExpired:
        elapsed_ms=int((time.monotonic() - start) * 1000)
        _logger.warning(f"命令超时: {' '.join(cmd)} (>{timeout}s)")
        return {"stdout":"","stderr":f"命令超时 (>{timeout}s)","exit_code":-1,"duration_ms":elapsed_ms,"blocked":False}
    except (FileNotFoundError, OSError) as e:
        elapsed_ms=int((time.monotonic() - start) * 1000)
        _logger.warning(f"命令执行异常: {' '.join(cmd)} — {e}")
        return {"stdout":"","stderr":str(e),"exit_code":-1,"duration_ms":elapsed_ms,"blocked":False}

"""
方法: journalctl_available(), 检测 journalctl 是否可用
"""
def journalctl_available():
    return os.path.exists("/usr/bin/journalctl") or os.path.exists("/bin/journalctl")

"""
方法: _cmd_ok(), 检查 run_command() 返回的 dict 是否表示命令成功执行

插件层统一使用此函数判断, 替代旧版 `if result is None` 模式。
- blocked → False
- exit_code≠0 且 stdout 为空 → False  
- 其他情况 → True (含 exit_code==0 无输出, exit_code≠0 但有 stdout)
"""
def _cmd_ok(result):
    if result["blocked"]:
        return False
    if result["exit_code"]!=0 and not result["stdout"]:
        return False
    return True

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

# ── KYSDK 麒麟原生 SDK 支持 ──────────────────────────────
#KYSDK 是麒麟操作系统的原生 Python SDK, 提供系统信息/硬件/安全/网络等 API,
#替代 shell 命令采集, 零注入风险, 精度更高。非麒麟环境自动降级为 shell 方案。

#模块级惰性导入标记: True=可用, False=不可用, None=未检测
_KYSDK_AVAILABLE=None

"""
方法: _kysdk_available(), 检测 KYSDK Python SDK 是否可导入

一次检测, 结果缓存于模块变量 _KYSDK_AVAILABLE。
非麒麟系统返回 False, 调用方应回落 shell 方案。
"""
def _kysdk_available():
    global _KYSDK_AVAILABLE
    if _KYSDK_AVAILABLE is not None:
        return _KYSDK_AVAILABLE
    try:
        import kysdk
        _KYSDK_AVAILABLE=True
    except ImportError:
        _KYSDK_AVAILABLE=False
    return _KYSDK_AVAILABLE

"""
方法: _kysdk_import(module_name), 安全按需导入 KYSDK 子模块

成功返回模块对象, 失败返回 None (调用方自行处理降级)。
用法: sdk=_kysdk_import("SystemInfo"); if sdk: sdk.get_cpu_usage()
"""
def _kysdk_import(name):
    if not _kysdk_available():
        return None
    try:
        mod=__import__("kysdk", fromlist=[name])
        return getattr(mod, name, None)
    except (ImportError, AttributeError):
        return None

"""
方法: _sdk_call(), 安全调用 KYSDK 对象方法, 失败返回 None

与 platform_detect._safe_call 合并, 统一入口避免重复实现。
用法: _sdk_call(hw, "get_cpu_arch") or "unknown"
"""
def _sdk_call(obj, method_name, *args):
    try:
        method=getattr(obj, method_name, None)
        if method is None:
            return None
        return method(*args)
    except Exception:
        return None

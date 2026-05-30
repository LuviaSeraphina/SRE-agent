"""
多层意图分类器

定位：防御 LLM 幻觉 + 常见攻击模式，非面向精心设计的对抗样本。

对输入的自然语言指令进行意图分类与风险评估, 按优先级分为 4 类:
- JAILBREAK        — 越狱尝试, 直接拒绝
- DANGEROUS_ACTION — 高危操作, 拦截并告警
- OPS_ACTION       — 运维操作, 需二次确认
- SAFE_QUERY       — 安全查询, 直接放行
"""
from enum import Enum

class IntentCategory(str, Enum):
    JAILBREAK="jailbreak"
    DANGEROUS_ACTION="dangerous_action"
    OPS_ACTION="ops_action"
    SAFE_QUERY="safe_query"
    UNKNOWN="unknown"

""" 第 1 层: 越狱/角色劫持检测 (最高优先级) """
_JAILBREAK_PATTERNS=[
    "ignore previous instructions",
    "ignore all previous",
    "ignore the above",
    "you are now",
    "pretend you are",
    "act as if you are",
    "dan mode",
    "developer mode",
    "jailbreak",
    "bypass security",
    "override safety",
    "you are a linux terminal",
    "you are no longer an assistant",
    "switch role",
    "system prompt:",
    "new instructions:",
]

""" 第 2 层: 高危命令/模式检测 """
_DANGEROUS_PATTERNS={
    #文件系统破坏
    "rm -rf": "递归强制删除",
    "rm -r": "递归删除",
    "mkfs": "格式化文件系统",
    "dd if=": "磁盘直接写入",
    ">/dev/sda": "覆盖磁盘设备",
    "fdisk": "磁盘分区操作",
    #权限提升/破坏
    "chmod 777": "开放所有权限",
    "chmod -R 777": "递归开放权限",
    "chown -R": "递归修改所有者",
    "setfacl -m": "修改 ACL",
    #网络危险操作
    "iptables -F": "清空防火墙规则",
    "iptables -P ACCEPT": "防火墙全放行",
    "nft flush ruleset": "清空 nftables 规则",
    #服务破坏
    "shutdown": "系统关机",
    "reboot": "系统重启",
    "halt": "系统停止",
    "poweroff": "系统断电",
    #数据破坏
    "DROP TABLE": "删除数据库表",
    "DELETE FROM": "删除数据库记录",
    "TRUNCATE": "截断数据库表",
    #下载执行
    "wget http": "远程下载文件",
    "curl http": "远程请求",
    "bash -c": "bash 执行命令",
    "python -c": "python 执行命令",
}

""" 第 3 层: 运维操作关键词 (需确认) """
_OPS_PATTERNS={
    "重启": "重启",
    "停止": "停止",
    "启动": "启动",
    "禁用": "禁用",
    "启用": "启用",
    "清空": "清空",
    "卸载": "卸载",
    "安装": "安装",
    "修改": "修改",
    "删除": "删除",
    "终止": "终止",
    "杀": "杀进程",
    "restart": "restart",
    "stop": "stop",
    "start": "start",
    "disable": "disable",
    "enable": "enable",
    "remove": "remove",
    "uninstall": "uninstall",
    "kill": "kill",
    "clean": "clean",
}

""" 第 4 层: 命令注入与特殊字符检测 """
_INJECTION_PATTERNS={
    ";": "命令分隔符",
    "&&": "命令链接符",
    "||": "条件链接符",
    "|": "管道符",
    "$(": "命令替换",
    "`": "反引号执行",
    "${{": "变量注入",
    "> /": "输出重定向到系统路径",
}

"""
方法: classify_intent(), 对用户输入进行多层意图分类, 按优先级返回最高风险分类

"""
def classify_intent(user_input):
    lower=user_input.lower()
    hits=[]

    #第 1 层: 越狱检测
    for pattern in _JAILBREAK_PATTERNS:
        if pattern in lower:
            hits.append("JAILBREAK: {}".format(pattern))
    if hits:
        return IntentCategory.JAILBREAK, hits

    #第 2 层: 高危命令检测
    for pattern, description in _DANGEROUS_PATTERNS.items():
        if pattern.lower() in lower:
            hits.append("DANGEROUS: {} ({})".format(pattern, description))
    if hits:
        return IntentCategory.DANGEROUS_ACTION, hits

    #第 3 层: 注入特殊字符检测
    for pattern, description in _INJECTION_PATTERNS.items():
        if pattern in user_input:  # 原始输入, 不 lower (保持精确匹配)
            hits.append("INJECTION: {} ({})".format(pattern, description))
    if hits:
        return IntentCategory.DANGEROUS_ACTION, hits

    #第 4 层: 运维操作关键词
    for pattern, description in _OPS_PATTERNS.items():
        if pattern in lower:
            hits.append("OPS: {} ({})".format(pattern, description))
    if hits:
        return IntentCategory.OPS_ACTION, hits

    #默认: 安全查询
    return IntentCategory.SAFE_QUERY, []


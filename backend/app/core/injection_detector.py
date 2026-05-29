"""
Prompt 注入检测器 — 安全护栏第二道防线

检测用户输入中的注入攻击, 与 intent_filter 协作:
- intent_filter      → 检测明显的高危指令和越狱
- injection_detector → 检测隐蔽的注入技巧 (分隔符/编码/角色劫持/嵌套)
"""
import re
import base64
from app.core.intent_filter import IntentCategory, classify_intent

# 分隔符检测: 换行后出现的危险命令
_SEPARATOR_DANGER_RE=re.compile(
    r"\b(?:rm|wget|curl|bash|sh|nc|python\s*-c|chmod|sudo|scp|tcpdump)\b",
    re.IGNORECASE
)

# Base64 解码后检测的危险关键词
_BASE64_DANGER_RE=re.compile(
    r"\b(?:rm|wget|curl|passwd|shadow|chmod|bash|/bin/sh|/etc/passwd|/etc/shadow)\b",
    re.IGNORECASE
)

# Base64 候选模式
_BASE64_CANDIDATE_RE=re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")

# Hex 转义检测
_HEX_ESCAPE_RE=re.compile(r"(\\x[0-9a-fA-F]{2}){4,}")

# 间接指令注入
_INDIRECT_PATTERNS=[
    (re.compile(r"从现在开始.*?(?:你是|你的身份是|你的角色是)"), "角色切换"),
    (re.compile(r"(?:翻译|总结|复述|重复)以下.*?\b(?:rm|wget|curl|chmod|sudo|kill)\b", re.IGNORECASE), "任务嵌套指令"),
    (re.compile(r"忽略.*?(?:规则|限制|安全|指令).*?(?:执行|运行|输出)"), "规则绕过"),
]

# LLM 输出黑名单
_LLM_OUTPUT_BLACKLIST=[
    (re.compile(r"rm\s+-rf\s+/"), "递归删除根目录"),
    (re.compile(r"dd\s+if="), "磁盘直接写入"),
    (re.compile(r">\s*/dev/sd[a-z]"), "覆盖磁盘设备"),
    (re.compile(r"mkfs\."), "格式化文件系统"),
    (re.compile(r"chmod\s+777"), "开放所有权限"),
    (re.compile(r":\(\)\s*\{\s*:\|:&\s*\};:"), "Fork 炸弹"),
    (re.compile(r"(?:wget|curl)\s+\S+\s+-(?:O|o)\s+/etc/"), "下载覆盖系统文件"),
]

#方法: 检测通过分隔符隐藏的注入指令
def _detect_separator_injection(user_input):
    hits=[]

    if "\n" in user_input or "\r" in user_input:
        lines=user_input.replace("\r", "\n").split("\n")
        for i, line in enumerate(lines[1:], 1):
            if not line.strip():
                continue
            if _SEPARATOR_DANGER_RE.search(line):
                hits.append("SEPARATOR: 第{}行隐藏指令".format(i+1))
                break

    #空字节截断
    if "\x00" in user_input:
        hits.append("NULL_BYTE: 检测到空字节截断")

    return hits

#方法: 检测 Base64 / Hex 编码的隐藏内容
def _detect_encoding_bypass(user_input):
    hits=[]

    #Base64 编码检测: 只解码前 5 个候选, 避免大量无效解码
    candidates=re.findall(_BASE64_CANDIDATE_RE, user_input)[:5]
    for candidate in candidates:
        try:
            decoded=base64.b64decode(candidate).decode("utf-8", errors="ignore")
            if _BASE64_DANGER_RE.search(decoded):
                hits.append("BASE64: 解码后含危险内容: {}".format(decoded[:50]))
                break
        except Exception:
            pass

    #Hex 编码检测
    if _HEX_ESCAPE_RE.search(user_input):
        hits.append("HEX_ESCAPE: 检测到连续十六进制转义序列")

    return hits

#方法: 检测通过"翻译/总结/复述"等任务进行的间接指令注入
def _detect_indirect_injection(user_input):
    hits=[]
    for pattern, desc in _INDIRECT_PATTERNS:
        if pattern.search(user_input):
            hits.append("INDIRECT: {}".format(desc))
    return hits

#方法: 校验 LLM 生成的文字中是否意外包含危险命令
def validate_llm_output(llm_output):
    hits=[]
    for pattern, description in _LLM_OUTPUT_BLACKLIST:
        if pattern.search(llm_output):
            hits.append("LLM_OUTPUT: {} — 匹配: {}".format(description, pattern.pattern[:40]))
    return hits

"""
方法: detect_injection(), 综合四层注入检测, 返回命中的注入类型列表

"""
def detect_injection(user_input):
    all_hits=[]

    #第 1 层: 分隔符注入
    all_hits.extend(_detect_separator_injection(user_input))

    #第 2 层: 编码绕过
    all_hits.extend(_detect_encoding_bypass(user_input))

    #第 3 层: 间接指令注入
    all_hits.extend(_detect_indirect_injection(user_input))

    return all_hits

"""
方法: is_safe(), 综合 intent_filter + injection_detector 的安全判定

"""
def is_safe(user_input, intent_cat=None):
    #先查注入
    injection_hits=detect_injection(user_input)
    if injection_hits:
        return False, injection_hits

    #再查意图 (如果已由 intent_filter 分类过则直接复用)
    if intent_cat is not None and intent_cat in (IntentCategory.JAILBREAK, IntentCategory.DANGEROUS_ACTION):
        return False, [intent_cat.value]

    return True, []


"""
方法: safe_pipeline(), 完整安全流水线: 意图→注入→执行→LLM输出校验

"""
def safe_pipeline(user_input, llm_output=None):
    #第一道: 意图分类
    intent_cat, intent_hits=classify_intent(user_input)
    if intent_cat in (IntentCategory.JAILBREAK, IntentCategory.DANGEROUS_ACTION):
        return False, "意图拦截: {}".format(intent_hits)

    #第二道: 注入检测
    injection_hits=detect_injection(user_input)
    if injection_hits:
        return False, "注入拦截: {}".format(injection_hits)

    #第三道: LLM 输出校验 (如果有输出)
    if llm_output:
        output_hits=validate_llm_output(llm_output)
        if output_hits:
            return False, "LLM输出拦截: {}".format(output_hits)

    return True, ""

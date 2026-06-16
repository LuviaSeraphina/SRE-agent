"""
共享因果链构建 — 供 chat.py (持久化) 和 audit.py (回溯) 共用

避免因果链构建逻辑分散两处, 统一维护。
"""
import re


"""
方法: build_causal_chain(), 从 5 阶段数据构建因果链

Args:
    stage_input: dict — 阶段 1 数据
    stage_perception: dict — 阶段 2 数据
    stage_reasoning: dict — 阶段 3 数据
    stage_validation: dict — 阶段 4 数据
    stage_execution: dict — 阶段 5 数据
    with_guidance: bool — 是否生成异常回溯指引

Returns:
    dict — {input_to_perception, perception_to_reasoning, reasoning_to_validation,
            validation_to_execution, traceback_guidance?}
"""
def build_causal_chain(stage_input, stage_perception, stage_reasoning,stage_validation, stage_execution, with_guidance=True):
    tools_called=stage_perception.get("tools_called",[])
    rules_hit=stage_validation.get("rules_hit",[])
    is_anomaly=stage_execution.get("is_anomaly",False)
    anomaly_type=stage_execution.get("anomaly_type","none")
    raw_input=(stage_input.get("raw_input","") or "")[:60]

    chain={
        "input_to_perception":{
            "description":"用户指令 '{}' → 驱动 {} 个工具感知环境".format(
                raw_input, len(tools_called)),
            "triggered_tools":tools_called,
        },
        "perception_to_reasoning":{
            "description":"{} 个工具返回的系统状态数据 → LLM 分析推理".format(
                len(stage_reasoning.get("tool_calls_planned",[]))),
            "perception_used":list(tools_called),
            "llm_output_preview":(stage_reasoning.get("llm_raw_output","") or "")[:200],
        },
        "reasoning_to_validation":{
            "description":"LLM 推理结果 → 安全校验命中 {} 条规则".format(len(rules_hit)),
            "rules_hit":rules_hit,
            "decision":stage_validation.get("decision","allowed"),
            "risk_score":stage_validation.get("risk_score",0),
        },
        "validation_to_execution":{
            "description":"{} → 最终执行{}".format(
                "安全校验通过" if stage_validation.get("decision")=="allowed" else "安全校验拦截",
                "成功" if not is_anomaly else "异常(类型: {})".format(anomaly_type)),
            "all_tools_result":stage_execution.get("tool_executions",[]),
            "is_anomaly":is_anomaly,
            "anomaly_type":anomaly_type,
        },
    }

    if with_guidance and is_anomaly:
        chain["traceback_guidance"]=generate_traceback_guidance(
            anomaly_type, rules_hit, stage_reasoning)

    return chain


"""
方法: generate_traceback_guidance(), 异常回溯指引 — 告诉用户如何定位根因
"""
def generate_traceback_guidance(anomaly_type, rules_hit, stage_reasoning):
    guidance={
        "title":"异常回溯指引",
        "anomaly_type":anomaly_type,
    }

    if anomaly_type=="jailbreak_blocked":
        guidance["root_cause_stage"]="阶段 4 (安全校验)"
        guidance["root_cause"]="用户输入被意图分类器识别为越狱尝试"
        guidance["trace_path"]="阶段 4 ← 阶段 1 (接收指令): 输入内容触发了 Layer 1 越狱检测规则"
        guidance["suggestion"]="检查用户输入是否包含角色劫持或绕过安全护栏的意图"
    elif anomaly_type=="injection_blocked":
        guidance["root_cause_stage"]="阶段 4 (安全校验)"
        guidance["root_cause"]="用户输入被注入检测器识别为注入攻击"
        guidance["trace_path"]="阶段 4 ← 阶段 1 (接收指令): 输入内容触发了注入检测规则 (分隔符/编码/同形字/零宽字符等)"
        guidance["suggestion"]="检查用户输入中是否包含命令分隔符、编码内容或混淆字符"
    elif anomaly_type=="dangerous_blocked":
        guidance["root_cause_stage"]="阶段 4 (安全校验)"
        guidance["root_cause"]="用户输入包含高危操作命令"
        guidance["trace_path"]="阶段 4 ← 阶段 1 (接收指令): 输入内容触发了 Layer 2 高危命令检测规则"
        guidance["suggestion"]="检查输入中是否包含 rm/mkfs/chmod 777/shutdown 等危险命令"
    elif anomaly_type=="tool_error":
        guidance["root_cause_stage"]="阶段 5 (执行结果)"
        guidance["root_cause"]="工具执行返回了错误状态"
        guidance["trace_path"]="阶段 5 ← 阶段 3 (推理决策): LLM 选择了正确的工具, 但底层命令执行失败"
        guidance["suggestion"]="检查阶段 2 的感知环境 — 目标资源是否存在、权限是否足够、命令白名单是否覆盖"
    elif anomaly_type=="security_blocked":
        guidance["root_cause_stage"]="阶段 4 (安全校验)"
        guidance["root_cause"]="安全护栏拦截了操作"
        guidance["trace_path"]="阶段 4 ← 阶段 3 (推理决策): LLM 推理产生的工具调用触发了安全规则"
        guidance["suggestion"]="检查触发的安全规则: {}".format(
            "; ".join(rules_hit) if rules_hit else "未知规则")
        guidance["llm_reasoning_preview"]=(stage_reasoning.get("llm_raw_output","") or "")[:200]

    return guidance


"""
方法: classify_anomaly(), 根据事件流和工具执行结果分类异常类型
"""
def classify_anomaly(events, tool_executions):
    for evt in events:
        msg=evt.get("data",{}).get("message","")
        if "越狱" in msg:
            return "jailbreak_blocked"
        if "注入攻击" in msg:
            return "injection_blocked"
        if "高危操作" in msg:
            return "dangerous_blocked"
    if any(te.get("is_anomaly",False) for te in tool_executions):
        return "tool_error"
    if any(evt.get("event")=="error" for evt in events):
        return "security_blocked"
    return "none"


"""
方法: fmt_summary(), 将工具返回的 summary dict 格式化为可读字符串
"""
def fmt_summary(summary):
    if not summary:
        return ""
    parts=[]
    for k,v in summary.items():
        if k in ("error","alert_reason"):
            continue
        if isinstance(v, bool):
            parts.append(f"{k}={v}")
        elif isinstance(v, (int,float)):
            parts.append(f"{k}={v}")
        else:
            parts.append(str(v)[:80])
    return "; ".join(parts[:3])

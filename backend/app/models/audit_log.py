"""
审计日志模型 — 5 阶段闭环记录

阶段:
- 1. input      — 接收指令 (原始输入 + 时间戳 + 用户)
- 2. perception — 感知环境 (工具调用 + 系统快照摘要)
- 3. reasoning  — 推理决策 (LLM 原始输出 + 计划工具调用)
- 4. validation — 安全校验 (命中规则 + 风险评分 + 决策)
- 5. execution  — 执行结果 (实际操作 + 退出码 + 输出 + 耗时)

v2: 新增 is_anomaly / anomaly_type 列, 替代 JSON 文本搜索, 支持索引加速

对应前端类型: AuditLog, StageInput, StagePerception, StageReasoning, StageValidation, StageExecution
"""
from sqlalchemy import Column, String, DateTime, Boolean, func
from sqlalchemy.types import JSON
from app.models.base import Base
from app.models._utils import _new_uuid, _utcnow

class AuditLog(Base):
    __tablename__="audit_logs"

    #主键
    id=Column(String(36), primary_key=True, default=_new_uuid)

    #索引字段
    session_id=Column(String(36), nullable=False, index=True)
    user=Column(String(128), nullable=False, default="anonymous", index=True)
    risk_level=Column(String(32), nullable=False, index=True)  #read_only / restricted / dangerous

    is_anomaly=Column(Boolean, nullable=False, default=False, index=True)
    anomaly_type=Column(String(32), nullable=False, default="none", index=True)
    #取值: none / security_blocked / tool_error / jailbreak_blocked / injection_blocked / dangerous_blocked

    #审计时间 (对话结束时间)
    timestamp=Column(DateTime, nullable=False, default=_utcnow)

    #---- 五阶段 (JSON) ----

    #阶段 1: 接收指令
    stage_input=Column(JSON, nullable=False)
    #{"raw_input": "...", "timestamp": "ISO8601", "user": "..."}

    #阶段 2: 感知环境
    stage_perception=Column(JSON, nullable=True)
    #{"tools_called": ["disk_inspect"], "snapshot_summary": "..."}

    #阶段 3: 推理决策
    stage_reasoning=Column(JSON, nullable=True)
    #{"llm_model": "deepseek-v4-flash", "llm_raw_output": "...", "tool_calls_planned": [...]}

    #阶段 4: 安全校验
    stage_validation=Column(JSON, nullable=True)
    #{"rules_hit": ["rm_rf_detected"], "risk_score": 85, "decision": "blocked", "reason": "..."}

    #阶段 5: 执行结果
    stage_execution=Column(JSON, nullable=True)
    #{"action_taken": "...", "exit_code": 0, "stdout": "...", "stderr": "...", "duration_ms": 120,
    # "tool_executions": [...], "causal_chain": {...}}

    #元数据
    created_at=Column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<AuditLog {self.id[:8]}... risk={self.risk_level} anomaly={self.is_anomaly}>"

"""
XikiyAIOps 多 Agent 协作模块

四Agent架构:
  Orchestrator  — 调度中心: 意图分析 → 路由 → 聚合 → 总结
  PerceptionAgent — 系统感知 + 安全审计 (只读工具)
  ExecutionAgent — 写操作 (危险/受限工具)
  SecurityAgent  — 输入审查 + 工具审批 + 事后审计 (纯逻辑)

用法:
    from app.agents import Orchestrator
    orch = Orchestrator()
    async for event in orch.run(user_input, history, session_id):
        yield event
"""
from .orchestrator import Orchestrator
from .security import SecurityAgent
from .perception import PerceptionAgent
from .execution import ExecutionAgent

__all__=["Orchestrator","SecurityAgent","PerceptionAgent","ExecutionAgent"]

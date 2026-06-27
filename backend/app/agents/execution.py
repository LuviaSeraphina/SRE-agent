"""
ExecutionAgent — 写操作 (危险/受限工具)
"""
from .base import BaseAgent, EXECUTION_TOOLS
from .prompts import EXECUTION_PROMPT


class ExecutionAgent(BaseAgent):
    agent_name="execution"
    system_prompt=EXECUTION_PROMPT
    allowed_tools=EXECUTION_TOOLS

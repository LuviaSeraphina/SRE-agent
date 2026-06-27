"""
PerceptionAgent — 系统感知 + 安全审计 (只读工具)
"""
from .base import BaseAgent, PERCEPTION_TOOLS
from .prompts import PERCEPTION_PROMPT


class PerceptionAgent(BaseAgent):
    agent_name="perception"
    system_prompt=PERCEPTION_PROMPT
    allowed_tools=PERCEPTION_TOOLS

# API 路由模块

# 对话 API — SSE 流式对话 + 历史查询
from app.api.chat import router as chat_router  # noqa: F401

# 审计 API — 审计日志查询
from app.api.audit import router as audit_router  # noqa: F401

# 仪表盘 API — 待设计
# from app.api.dashboard import router as dashboard_router

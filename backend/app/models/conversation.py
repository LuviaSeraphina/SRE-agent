"""
对话模型 — 会话 + 消息

Conversation: 一次完整对话 (session)
Message:     单条消息 (user / assistant / system / tool)

对应前端类型: ChatMessage, ToolCall
"""
from typing import List
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.types import JSON
from app.models.base import Base
from app.models._utils import _new_uuid, _now


class Conversation(Base):
    __tablename__="conversations"

    id=Column(String(36), primary_key=True, default=_new_uuid)
    session_id=Column(String(36), nullable=False, unique=True, index=True)
    title=Column(String(256), nullable=True)  #首条用户消息截断

    created_at=Column(DateTime, server_default=func.now())
    updated_at=Column(DateTime, server_default=func.now(), onupdate=func.now())

    #关联
    messages: Mapped[List["Message"]]=relationship(
        "Message", back_populates="conversation", order_by="Message.timestamp"
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.session_id[:8]}...>"


class Message(Base):
    __tablename__="messages"

    id=Column(String(36), primary_key=True, default=_new_uuid)
    conversation_id=Column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role=Column(String(16), nullable=False)  #user / assistant / system / tool
    content=Column(Text, nullable=False, default="")

    #tool_calls — 仅 assistant 消息可能有
    #格式: [{"id":"...", "tool_name":"...", "arguments":{...}, "status":"...", ...}]
    tool_calls=Column(JSON, nullable=True)

    timestamp=Column(DateTime, nullable=False, default=_now)
    created_at=Column(DateTime, server_default=func.now())

    #关联
    conversation: Mapped["Conversation"]=relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message {self.id[:8]}... {self.role}>"

"""
审计写入 — 将对话数据持久化到 DB

用法:
    from app.services.audit_writer import save_conversation, save_audit_log
    await save_conversation(db, session_id, messages, title)
    await save_audit_log(db, session_id, user, risk_level, stages)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Conversation, Message, AuditLog
from datetime import datetime, timezone


"""
方法: save_conversation(), 保存/更新对话会话 + 全部消息

messages: [{"role":"user","content":"..."}, {"role":"assistant","content":"...","tool_calls":[...]}, ...]
"""
async def save_conversation(
    db: AsyncSession,
    session_id: str,
    messages: list,
    title: str="",
):
    #查找或创建 Conversation
    result=await db.execute(select(Conversation).where(Conversation.session_id==session_id))
    conv=result.scalar_one_or_none()

    if conv is None:
        conv=Conversation(session_id=session_id, title=title[:256] if title else "")
        db.add(conv)
        await db.flush()
    else:
        conv.title=title[:256] if title else conv.title  # type: ignore[assignment]  # SQLAlchemy Column descriptor

    #追加消息 (去重: 同 id 不重复写)
    for msg in messages:
        msg_id=msg.get("id", "")
        if msg_id:
            existing=await db.execute(select(Message).where(Message.id==msg_id))
            if existing.scalar_one_or_none():
                continue
        db.add(Message(
            id=msg_id or None,
            conversation_id=conv.id,
            role=msg.get("role", "user"),
            content=msg.get("content", ""),
            tool_calls=msg.get("tool_calls"),
            timestamp=datetime.now(timezone.utc),
        ))

    await db.commit()


"""
方法: save_audit_log(), 写入五阶段审计日志

stages: 5 元素列表或字典 [stage_input, stage_perception, stage_reasoning, stage_validation, stage_execution]
"""
async def save_audit_log(
    db: AsyncSession,
    session_id: str,
    user: str,
    risk_level: str,
    stages: list,
):
    audit=AuditLog(
        session_id=session_id,
        user=user,
        risk_level=risk_level,
        stage_input=stages[0] if len(stages)>0 else {},
        stage_perception=stages[1] if len(stages)>1 else None,
        stage_reasoning=stages[2] if len(stages)>2 else None,
        stage_validation=stages[3] if len(stages)>3 else None,
        stage_execution=stages[4] if len(stages)>4 else None,
    )
    db.add(audit)
    await db.commit()

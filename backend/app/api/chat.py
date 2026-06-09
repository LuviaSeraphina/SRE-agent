"""
对话 API — SSE 流式对话 + 历史查询

POST /api/chat/send              — SSE 流式对话 (自动持久化)
POST /api/chat/confirm           — 危险操作确认回调
GET  /api/chat/history           — 会话列表
GET  /api/chat/history/{id}      — 会话消息详情

事件格式: event: <type>\ndata: <json>\n\n
"""
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db, async_session
from app.llm.adapter import chat_stream
from app.models import Conversation
from app.services.audit_writer import save_conversation, save_audit_log
from datetime import datetime, timezone
import json
import logging

router=APIRouter()


@router.post("/send")
async def chat_send(request: Request):
    body=await request.json()
    user_input=body.get("message", "")
    session_id=body.get("session_id", "")
    history=body.get("history", None)

    #收集流事件用于事后写入审计日志
    collected_events=[]

    async def sse_generator():
        collector=[]
        #阶段 1: 接收指令
        stage_input_event={"raw_input": user_input, "timestamp": datetime.now(timezone.utc).isoformat(), "user": "anonymous"}

        async for event in chat_stream(user_input, history):
            if await request.is_disconnected():
                break

            collected_events.append(event)
            event_type=event.get("event", "")

            #收集工具调用信息
            if event_type=="tool_call":
                collector.append(event.get("data", {}).get("tool_name", ""))

            yield "event: {}\ndata: {}\n\n".format(
                event["event"],
                json.dumps(event["data"], ensure_ascii=False),
            )

        #流结束后持久化
        if session_id and collected_events:
            await _persist_chat(session_id, user_input, collected_events, collector, stage_input_event)

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/confirm")
async def chat_confirm(request: Request):
    """危险操作确认回调

    Phase 2 计划: 通过 asyncio.Event + session_id 映射实现暂停-恢复机制。
    当前阶段: 危险操作的 security_check 事件已发送到前端展示,
    但后端暂不支持"确认后继续执行"的完整流程。
    前端应展示确认对话框, 收到确认后调用本端点记录审计日志。
    """
    body=await request.json()
    confirmed=body.get("confirmed", False)
    if not confirmed:
        return {"success": False, "message": "操作已取消"}
    # Phase 2: 通过 asyncio.Event 恢复 chat_stream 中暂停的 tool 执行
    return {"success": True, "message": "确认已收到 (Phase 2 将实现完整确认流程)"}


@router.get("/history")
async def chat_history(
    page: int=Query(1, ge=1),
    size: int=Query(20, ge=1, le=50),
    db: AsyncSession=Depends(get_db),
):
    """会话历史列表 (按更新时间倒序)"""
    q=select(Conversation).order_by(Conversation.updated_at.desc()).offset((page - 1) * size).limit(size)
    result=await db.execute(q)
    items=result.scalars().all()
    return {
        "code": 0,
        "data": {
            "items": [{
                "id": c.id,
                "session_id": c.session_id,
                "title": c.title or "",
                "created_at": c.created_at.isoformat() if c.created_at else "",     # type: ignore[union-attr]
                "updated_at": c.updated_at.isoformat() if c.updated_at else "",     # type: ignore[union-attr]
            } for c in items],
            "page": page,
            "page_size": size,
        },
        "message": "ok",
    }


@router.get("/history/{session_id}")
async def chat_history_detail(
    session_id: str,
    db: AsyncSession=Depends(get_db),
):
    """查询指定会话的全部消息"""
    result=await db.execute(select(Conversation).where(Conversation.session_id==session_id))
    conv=result.scalar_one_or_none()
    if conv is None:
        return {"code": 4004, "data": None, "message": "会话不存在"}

    #eager loaded via relationship
    messages=[{
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "tool_calls": m.tool_calls,
        "timestamp": m.timestamp.isoformat() if m.timestamp else "",    # type: ignore[union-attr]
    } for m in conv.messages]

    return {"code": 0, "data": {"session_id": session_id, "messages": messages}, "message": "ok"}


"""
方法: _persist_chat(), 流结束后异步写入 Conversation + Message + AuditLog

在 SSE 生成器结束后调用, 使用独立数据库会话 (不阻塞 HTTP 响应)
"""
async def _persist_chat(session_id, user_input, events, tools_called, stage_input_event):
    try:
        async with async_session() as db:
            #拆解事件, 构建消息列表
            messages=[]
            assistant_content=""
            tool_calls_collected=[]
            security_rules=[]  #收集安全拦截信息

            for evt in events:
                etype=evt.get("event", "")
                edata=evt.get("data", {})

                if etype=="token":
                    assistant_content += edata.get("text", "")

                elif etype=="tool_call":
                    tool_calls_collected.append({
                        "id": edata.get("tool_name", ""),
                        "tool_name": edata.get("tool_name", ""),
                        "arguments": edata.get("arguments", {}),
                        "status": "running",
                        "risk_level": edata.get("risk_level", ""),
                    })

                elif etype=="tool_result":
                    #更新最近匹配的 tool_call 状态
                    for tc in tool_calls_collected:
                        if tc["tool_name"]==edata.get("tool_name", ""):
                            tc["status"]=edata.get("status", "done")
                            tc["result"]=edata.get("result")
                            break

                elif etype=="security_check":
                    #采集安全护栏拦截详情
                    security_rules.append({
                        "tool_name": edata.get("tool_name", ""),
                        "summary": edata.get("summary", ""),
                        "risk_level": edata.get("risk_level", ""),
                    })

                elif etype=="error":
                    assistant_content += f"\n\n❌ {edata.get('message', '')}"

            #构建消息记录
            title=user_input[:100] if user_input else ""

            #user 消息
            messages.append({"role": "user", "content": user_input})

            #assistant 消息 (含 tool_calls)
            if assistant_content or tool_calls_collected:
                messages.append({
                    "role": "assistant",
                    "content": assistant_content,
                    "tool_calls": tool_calls_collected if tool_calls_collected else None,
                })

            #写入对话
            await save_conversation(db, session_id, messages, title)

            #写入审计日志 (五阶段)
            risk_level=_derive_risk_level(events)

            #阶段 2: 感知摘要 (工具调用摘要)
            perception_summary=", ".join(tools_called) if tools_called else "无工具调用"
            stage_perception={"tools_called": tools_called, "snapshot_summary": perception_summary}

            #阶段 3: 推理 (LLM 输出摘要)
            stage_reasoning={
                "llm_model": "",
                "llm_raw_output": assistant_content[:500] if assistant_content else "",
                "tool_calls_planned": tools_called,
            }

            #阶段 4: 安全校验 (来自 security_check 事件)
            has_error=any(e.get("event")=="error" for e in events)
            if security_rules:
                stage_validation={
                    "rules_hit": [r["summary"] for r in security_rules],
                    "risk_score": 100 if has_error else 50,
                    "decision": "blocked" if has_error else "confirmed",
                    "reason": "; ".join(r["summary"] for r in security_rules),
                }
            else:
                stage_validation={
                    "rules_hit": [],
                    "risk_score": 0,
                    "decision": "blocked" if has_error else "allowed",
                    "reason": "有安全拦截" if has_error else "安全检查通过",
                }

            #阶段 5: 执行结果
            stage_execution={
                "action_taken": "对话完成" if not has_error else "被拦截",
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "duration_ms": 0,
            }

            stages=[stage_input_event, stage_perception, stage_reasoning, stage_validation, stage_execution]
            await save_audit_log(db, session_id, "anonymous", risk_level, stages)

    except Exception:
        #持久化失败不应影响 HTTP 响应 (已返回)
        logging.getLogger("sre_agent.chat").exception("持久化对话失败")


"""
方法: _derive_risk_level(), 从事件流推断风险等级
"""
def _derive_risk_level(events):
    for evt in events:
        data=evt.get("data", {})
        rl=data.get("risk_level", "")
        if rl in ("dangerous", "restricted"):
            return rl
        if evt.get("event")=="error":
            return "dangerous"
    return "read_only"

"""
审计日志 API — 查询 + 详情 + 异常回溯 + 会话关联

端点:
    GET /api/audit/list              — 分页 + 筛选查询 (含异常标记筛选)
    GET /api/audit/{id}              — 单条审计详情
    GET /api/audit/{id}/traceback    — 异常回溯: 因果链 + 根因分析
    GET /api/audit/session/{sid}     — 会话关联: 同 session 全部审计记录

v2: 异常筛选使用独立列 is_anomaly / anomaly_type, 支持索引加速
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, String as SA_String
from app.db import get_db
from app.models import AuditLog
from app.services.causal_chain import build_causal_chain

router=APIRouter()


@router.get("/list")
async def audit_list(
    page: int=Query(1, ge=1),
    size: int=Query(20, ge=1, le=100),
    risk_level: str=Query(""),
    keyword: str=Query(""),
    anomaly: str=Query(""),
    db: AsyncSession=Depends(get_db),
):
    """分页查询审计日志, 支持按风险等级、关键词和异常标记筛选"""
    #构建查询
    q=select(AuditLog)
    count_q=select(func.count(AuditLog.id))

    if risk_level:
        q=q.where(AuditLog.risk_level==risk_level)
        count_q=count_q.where(AuditLog.risk_level==risk_level)

    if keyword:
        #关键词匹配: 用户名 或 原始输入 (JSON 文本, 兼容旧版 SQLite)
        kw_filter=AuditLog.user.ilike(f"%{keyword}%")
        kw_filter=kw_filter | AuditLog.stage_input.cast(SA_String).ilike(f"%{keyword}%")
        q=q.where(kw_filter)
        count_q=count_q.where(kw_filter)

    if anomaly=="true":
        #v2: 使用独立列筛选, 支持索引
        q=q.where(AuditLog.is_anomaly==True)
        count_q=count_q.where(AuditLog.is_anomaly==True)

    #按时间倒序
    q=q.order_by(AuditLog.timestamp.desc())

    #分页
    offset=(page - 1) * size
    q=q.offset(offset).limit(size)

    #执行
    total_result=await db.execute(count_q)
    total=total_result.scalar() or 0

    items_result=await db.execute(q)
    items=items_result.scalars().all()

    #构建响应 (Stage 数据已在 JSON 列中, 直接返回)
    return {
        "code": 0,
        "data": {
            "items": [_serialize_audit(item) for item in items],
            "total": total,
            "page": page,
            "page_size": size,
        },
        "message": "ok",
    }


@router.get("/session/{session_id}")
async def audit_session_logs(
    session_id: str,
    db: AsyncSession=Depends(get_db),
):
    """查询同一会话的全部审计记录, 用于会话级异常回溯"""
    result=await db.execute(
        select(AuditLog)
        .where(AuditLog.session_id==session_id)
        .order_by(AuditLog.timestamp.asc())
    )
    items=result.scalars().all()
    if not items:
        return {"code": 4004, "data": None, "message": "该会话无审计记录"}

    serialized=[_serialize_audit(item) for item in items]
    #统计会话级别的异常汇总 (v2: 从顶层字段读取, 由 _serialize_audit 从模型列取值)
    anomaly_count=sum(1 for s in serialized if s["is_anomaly"] is True)
    return {
        "code": 0,
        "data": {
            "session_id": session_id,
            "total_ops": len(serialized),
            "anomaly_count": anomaly_count,
            "items": serialized,
        },
        "message": "ok",
    }


@router.get("/{audit_id}")
async def audit_detail(
    audit_id: str,
    db: AsyncSession=Depends(get_db),
):
    """查询单条审计日志完整详情"""
    result=await db.execute(select(AuditLog).where(AuditLog.id==audit_id))
    item=result.scalar_one_or_none()
    if item is None:
        return {"code": 4004, "data": None, "message": "审计记录不存在"}

    return {"code": 0, "data": _serialize_audit(item), "message": "ok"}


@router.get("/{audit_id}/traceback")
async def audit_traceback(
    audit_id: str,
    db: AsyncSession=Depends(get_db),
):
    """
    异常回溯 — 返回 5 阶段因果链 + 根因分析 + 关联会话记录

    这是"推理链路溯源"的核心 API:
    1. 提取 5 阶段完整数据
    2. 构建因果链 (causal_chain): 展示数据在各阶段间的流转关系
    3. 生成回溯指引 (traceback_guidance): 告诉用户根因在哪个阶段、如何排查
    4. 关联同会话的其他操作 (related_ops): 提供更广阔的上下文
    """
    result=await db.execute(select(AuditLog).where(AuditLog.id==audit_id))
    item=result.scalar_one_or_none()
    if item is None:
        return {"code": 4004, "data": None, "message": "审计记录不存在"}

    serialized=_serialize_audit(item)

    #提取因果链 (如果持久化时已构建则直接返回, 否则当场构建)
    causal_chain=serialized["stages"][4].get("causal_chain")
    if not causal_chain:
        #兼容旧数据: 当场构建因果链
        causal_chain=_build_causal_chain_on_demand(serialized)

    #提取异常类型和回溯指引 (v2: 从 _serialize_audit 输出的顶层字段读取, 来源为模型列)
    anomaly_type=serialized.get("anomaly_type","none")
    is_anomaly=serialized.get("is_anomaly",False)

    traceback_guidance=None
    if causal_chain and isinstance(causal_chain, dict):
        traceback_guidance=causal_chain.get("traceback_guidance")

    #查询关联会话记录 (同 session_id 的其他操作)
    related_result=await db.execute(
        select(AuditLog)
        .where(
            AuditLog.session_id==item.session_id,
            AuditLog.id!=audit_id,
        )
        .order_by(AuditLog.timestamp.asc())
        .limit(20)
    )
    related_items=related_result.scalars().all()
    related_ops=[
        {
            "id":r.id,
            "timestamp":r.timestamp.isoformat() if r.timestamp else "",
            "risk_level":r.risk_level,
            "input_preview":(r.stage_input or {}).get("raw_input","")[:80] if r.stage_input else "",
            "is_anomaly":r.is_anomaly,
            "anomaly_type":r.anomaly_type,
        }
        for r in related_items
    ]

    return {
        "code": 0,
        "data": {
            "audit_log": serialized,
            "is_anomaly": is_anomaly,
            "anomaly_type": anomaly_type,
            "causal_chain": causal_chain,          #阶段间因果链路
            "traceback_guidance": traceback_guidance,  #异常回溯指引
            "related_ops": related_ops,             #同会话关联操作
            "related_ops_count": len(related_ops),
        },
        "message": "ok",
    }


"""
方法: _serialize_audit(), 将 ORM 对象转为前端期望的 AuditLog 格式

v2: is_anomaly / anomaly_type 从独立列读取 (而非 JSON), 保证与 DB 索引一致
"""
def _serialize_audit(item: AuditLog) -> dict:
    stage_exec=item.stage_execution or {}
    return {
        "id": item.id,
        "timestamp": item.timestamp.isoformat() if item.timestamp else "",
        "user": item.user,
        "session_id": item.session_id,
        "risk_level": item.risk_level,
        #v2: 从独立列读取异常标记 (而非 JSON), 保证与 DB 索引一致
        "is_anomaly": item.is_anomaly,
        "anomaly_type": item.anomaly_type,
        "stages": [
            item.stage_input or {},
            item.stage_perception or {},
            item.stage_reasoning or {},
            item.stage_validation or {},
            stage_exec,
        ],
    }


"""
方法: _build_causal_chain_on_demand(), 兼容旧数据 — 当场从 5 阶段数据构建因果链

v2: 使用共享模块 build_causal_chain(), 与 chat.py 逻辑一致, 并生成 traceback_guidance
"""
def _build_causal_chain_on_demand(serialized):
    stages=serialized["stages"]
    s1,s2,s3,s4,s5=stages[0],stages[1],stages[2],stages[3],stages[4]
    return build_causal_chain(s1, s2, s3, s4, s5, with_guidance=True)

"""
审计日志 API — 查询 + 详情

端点:
    GET /api/audit/list     — 分页 + 筛选查询
    GET /api/audit/{id}     — 单条审计详情

返回格式: {code:0, data:{items, total, page, page_size}, message:"ok"}
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, String as SA_String
from app.db import get_db
from app.models import AuditLog

router=APIRouter()


@router.get("/list")
async def audit_list(
    page: int=Query(1, ge=1),
    size: int=Query(20, ge=1, le=100),
    risk_level: str=Query(""),
    keyword: str=Query(""),
    db: AsyncSession=Depends(get_db),
):
    """分页查询审计日志, 支持按风险等级和关键词筛选"""
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


"""
方法: _serialize_audit(), 将 ORM 对象转为前端期望的 AuditLog 格式
"""
def _serialize_audit(item: AuditLog) -> dict:
    return {
        "id": item.id,
        "timestamp": item.timestamp.isoformat() if item.timestamp else "",
        "user": item.user,
        "session_id": item.session_id,
        "risk_level": item.risk_level,
        "stages": [
            item.stage_input or {},
            item.stage_perception or {},
            item.stage_reasoning or {},
            item.stage_validation or {},
            item.stage_execution or {},
        ],
    }

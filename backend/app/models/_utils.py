"""
模型共享工具 — UUID 生成 + UTC 时间

避免在各模型文件中重复定义相同的辅助函数。
"""
from datetime import datetime
import uuid


"""
方法: _new_uuid(), 生成 UUID4 字符串 (36 字符, 如 'a1b2c3d4-...')
"""
def _new_uuid() -> str:
    return str(uuid.uuid4())


"""
方法: _now(), 返回本地当前时间
"""
def _now() -> datetime:
    return datetime.now()

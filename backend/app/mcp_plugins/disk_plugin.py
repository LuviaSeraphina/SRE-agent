"""
MCP 磁盘巡检工具

功能：
- 获取指定路径的磁盘使用情况
- 返回总容量、已用、剩余(GB)及使用率(%)
- 默认检查根分区，可指定任意挂载点路径(如 /var/log)

底层调用 psutil.disk_usage()，纯只读操作，无副作用。

用于 MCP Agent 进行磁盘空间预警、容量规划等场景。

"""
import os
import psutil
from app.mcp_plugins._common import make_response as _make_response, error_response as _error_response


disk_inspect_schema={
    "name": "disk_inspect",
    "description": "获取磁盘信息,可定义具体路径",
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {"type": "string","default": "/","description": "要检查的挂载点路径，例如 '/' 或 '/var/log'"}
        }
    }
}

"""
方法: disk_inspect_handler(), 获取磁盘信息

"""
def disk_inspect_handler(path="/"):
    try:
        GB=1024**3
        disk_info=psutil.disk_usage(path)
        return _make_response("disk_inspect_handler",
            data={
                "total_gb": round(disk_info.total / GB, 2),
                "used_gb": round(disk_info.used / GB, 2),
                "free_gb": round(disk_info.free / GB, 2),
                "usage_percent": disk_info.percent,
            },
            summary={
                "path": path,
                "usage_percent": disk_info.percent,
                "alert": disk_info.percent > 90,
            },
        )
    except Exception as e:
        return _error_response("disk_inspect_handler", e)


"""
方法: disk_inode_handler(), 获取 inode 使用率 — 生产故障高频根因 (inode 耗尽但磁盘有空间)

"""
def disk_inode_handler(path="/"):
    try:
        stat=os.statvfs(path)
        total_inodes=stat.f_files
        free_inodes=stat.f_ffree
        used_inodes=total_inodes - free_inodes
        usage_percent=round(used_inodes / total_inodes * 100, 1) if total_inodes > 0 else 0
        return _make_response("disk_inode_handler",
            data={
                "path": path,
                "total_inodes": total_inodes,
                "used_inodes": used_inodes,
                "free_inodes": free_inodes,
                "usage_percent": usage_percent,
            },
            summary={
                "usage_percent": usage_percent,
                "alert": usage_percent > 80,
                "alert_reason": "inode 使用率 {}% > 80%, 可能导致无法创建新文件".format(usage_percent) if usage_percent > 80 else "",
            },
        )
    except Exception as e:
        return _error_response("disk_inode_handler", e)


"""
方法: disk_io_handler(), 磁盘 I/O 统计 — 读/写次数、吞吐量

"""
def disk_io_handler():
    try:
        io=psutil.disk_io_counters()
        if not io:
            return _make_response("disk_io_handler", data={}, summary={"error": "无法获取磁盘 I/O"})
        return _make_response("disk_io_handler",
            data={
                "read_count": io.read_count,
                "write_count": io.write_count,
                "read_bytes_mb": round(io.read_bytes / 1048576, 1),
                "write_bytes_mb": round(io.write_bytes / 1048576, 1),
                "read_time_ms": io.read_time,
                "write_time_ms": io.write_time,
            },
            summary={
                "total_io": io.read_count + io.write_count,
                "read_mb": round(io.read_bytes / 1048576, 1),
                "write_mb": round(io.write_bytes / 1048576, 1),
            },
        )
    except Exception as e:
        return _error_response("disk_io_handler", e)
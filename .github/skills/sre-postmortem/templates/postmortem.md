# 故障复盘报告

> 基于 SRE-agent MCP 运维数据生成

## 基本信息
- 故障时间: YYYY-MM-DD HH:MM ~ HH:MM
- 影响范围: （哪些服务/SLI 受影响）
- 发现方式: （告警 / 用户反馈 / 巡检 / MCP 安全插件）
- 处理人: 
- 关联 MCP Tool: （涉及的 disk_inspect / process_inspect / security_auth_failures 等）

## SLI/SLO 影响

| SLI | SLO | 实际可用性 | 错误预算消耗 | 状态 |
|-----|-----|-----------|-------------|------|
| | | | | 🟢 正常 / 🟡 警告 / 🔴 超标 |

## 时间线（UTC）

| 时间 | 来源 | 事件 |
|------|------|------|
| | MCP / 告警 / 人工 | |

## MCP 审计摘要

- security_auth_failures: （故障期间是否有异常登录）
- process_inspect: （异常进程）
- disk_inspect: （磁盘告警）
- network_listening_ports: （端口异常）

## 根因分析（5 Whys）

1. 
2. 
3. 
4. 
5. 

## 改进措施

| 措施 | 类型 | 关联模块 | 期限 |
|------|------|----------|------|
|  | 预防 | | |
|  | 检测 | | |
|  | 缓解 | | |

## 经验教训

- 

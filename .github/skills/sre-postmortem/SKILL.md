---
name: sre-postmortem
description: 'Use when: 事后分析, 故障复盘, 事故回顾, postmortem, incident review, 根因分析, 5 Whys, RCA, 生成复盘报告. Generates structured postmortem reports following blameless culture, integrating MCP plugin audit data and SLI/SLO error budget analysis.'
argument-hint: '故障简述...'
user-invocable: true
---

# SRE 事后分析（Postmortem）

基于 SRE-agent 项目的 MCP 运维数据，生成规范的无指责事后分析报告。

## 何时使用
- 生产故障发生后，需要结构化复盘
- 告警触发后需要分析根因和改进措施
- 定期回顾 SLI/SLO 达标情况
- 新人培训，用真实案例教学

## 数据来源

分析时优先参考以下项目文件：

| 数据 | 路径 | 用途 |
|------|------|------|
| 事后分析模板 | [postmortem.md](./templates/postmortem.md) | 报告结构 |
| SLI/SLO 定义 | `/home/liliana0521/SRE-STUDY/docs/SLI_SLO.md` | 计算错误预算消耗 |
| 异常检测报告 | `/home/liliana0521/SRE-STUDY/logs/anomaly_report.md` | 交叉验证根因 |
| MCP 安全审计 | `backend/app/mcp_plugins/security_plugin.py` | 安全事件关联 |

## 执行流程

### Step 1: 收集基本信息
向用户确认：
- 故障时间窗口（开始 ~ 结束）
- 发现方式（告警 / 用户反馈 / 巡检）
- 影响范围（哪些 SLI 受影响）

### Step 2: 构建时间线
从以下来源提取事件序列：
- MCP 插件 `security_plugin.py` 的 `security_auth_failures()` — 是否有异常登录
- MCP 插件 `process_plugin.py` 的 `process_inspect_handler()` — 进程异常
- MCP 插件 `disk_plugin.py` 的 `disk_inspect_handler()` — 磁盘告警
- `alert_rules.yml` 对应的 Prometheus 告警
- 人工补充的操作步骤

### Step 3: SLI/SLO 影响评估
- 对照 SLI_SLO.md 计算实际消耗的错误预算
- 评估是否需要调整 SLO 阈值
- 如果错误预算耗尽，标记为 🔴 严重

### Step 4: 5 Whys 根因分析
从系统层面追问，**禁止归因于个人**：
1. 直接原因是什么？
2. 为什么该原因会发生？
3. 为什么没有被预防？
4. 为什么没有被检测到？
5. 为什么流程允许它发生？

### Step 5: 生成改进措施
按类型分类：
| 类型 | 说明 | 示例 |
|------|------|------|
| **预防** | 防止同类故障再发生 | MCP 插件添加参数校验 |
| **检测** | 更快发现故障 | 在 intent_filter.py 增加异常模式 |
| **缓解** | 减少影响 | 添加自动回滚 / 降级策略 |

### Step 6: 输出报告
使用 [postmortem.md](./templates/postmortem.md) 模板格式输出完整报告。

## 约束
- 遵循无指责文化（blameless），只分析系统问题
- 每个改进措施必须指定类型（预防/检测/缓解）
- 如果无法确定根因，明确标记为"待验证"而非猜测

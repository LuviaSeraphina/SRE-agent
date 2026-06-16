// ============================================================
// 审计日志 API — 分页查询 + 详情 + 异常回溯 + 会话关联
// 对齐后端 app/api/audit.py v2
// ============================================================

import { apiGet } from './client'
import type { ApiResponse, AuditLog, PaginatedData, TracebackResponse, SessionAuditSummary } from '../types'

export interface AuditListParams {
  page?: number
  size?: number
  risk_level?: string
  keyword?: string
  anomaly?: boolean
}

/**
 * GET /api/audit/list — 分页 + 筛选查询
 * @param signal 可选的 AbortSignal，用于取消请求
 */
export function fetchAuditLogs(
  params: AuditListParams = {},
  signal?: AbortSignal,
): Promise<ApiResponse<PaginatedData<AuditLog>>> {
  const query: Record<string, string> = {}
  if (params.page) query.page = String(params.page)
  if (params.size) query.size = String(params.size)
  if (params.risk_level) query.risk_level = params.risk_level
  if (params.keyword) query.keyword = params.keyword
  if (params.anomaly) query.anomaly = 'true'
  return apiGet('/audit/list', query, undefined, signal)
}

/**
 * GET /api/audit/{id} — 单条审计日志详情
 */
export function fetchAuditDetail(
  id: string,
): Promise<ApiResponse<AuditLog>> {
  return apiGet(`/audit/${id}`)
}

/**
 * GET /api/audit/{id}/traceback — 异常回溯: 因果链 + 根因分析 + 关联操作
 */
export function fetchTraceback(
  id: string,
): Promise<ApiResponse<TracebackResponse>> {
  return apiGet(`/audit/${id}/traceback`)
}

/**
 * GET /api/audit/session/{sessionId} — 会话级关联: 同 session 全部审计记录
 */
export function fetchSessionAuditLogs(
  sessionId: string,
): Promise<ApiResponse<SessionAuditSummary>> {
  return apiGet(`/audit/session/${sessionId}`)
}

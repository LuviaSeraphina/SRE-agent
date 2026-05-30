export const BASE_URL = '/api'

const DEFAULT_TIMEOUT = 15_000 // 15 秒

/** 带超时和分类错误信息的 fetch 封装 */
async function fetchWithTimeout(url: string, options: RequestInit = {}, timeout = DEFAULT_TIMEOUT): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)
  try {
    const res = await fetch(url, { ...options, signal: controller.signal })
    return res
  } finally {
    clearTimeout(timer)
  }
}

/** 根据 HTTP 状态码生成友好错误信息 */
function httpErrorMessage(status: number): string {
  switch (status) {
    case 400: return '请求参数有误'
    case 403: return '没有权限执行此操作'
    case 404: return '请求的资源不存在'
    case 500: return '服务器内部错误，请稍后重试'
    case 502: return '网关错误'
    case 503: return '服务暂不可用'
    default:  return `请求失败 (${status})`
  }
}

/**
 * GET 请求封装
 * @param path   API 路径，如 '/dashboard/summary'
 * @param params 可选的 query 参数
 */
export async function apiGet<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(BASE_URL + path, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))
  }
  const res = await fetchWithTimeout(url.toString())
  if (!res.ok) {
    throw new Error(httpErrorMessage(res.status))
  }
  return res.json()
}

/**
 * POST 请求封装
 * @param path API 路径
 * @param body JSON 请求体
 */
export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetchWithTimeout(BASE_URL + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    throw new Error(httpErrorMessage(res.status))
  }
  return res.json()
}

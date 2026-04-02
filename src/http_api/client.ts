import snapshotData from './_snapshot.json'

const BASE_URL = '/api'

type ApiResponse<T> = {
  data: T | null
  error: string | null
}

const parseBody = <T>(text: string): T | null => {
  if (!text) return null

  try {
    return JSON.parse(text) as T
  } catch {
    return null
  }
}

const getErrorMessage = (status: number, statusText: string, body: unknown, fallbackText: string) => {
  if (body && typeof body === 'object') {
    if ('detail' in body && typeof body.detail === 'string') return body.detail
    if ('message' in body && typeof body.message === 'string') return body.message
    if ('error' in body && typeof body.error === 'string') return body.error
  }

  return fallbackText || `${status} ${statusText}`.trim()
}

// 从快照中查找匹配的数据（去掉 query string 匹配）
const _snapshot = snapshotData as Record<string, unknown>
const findSnapshot = <T>(url: string): T | null => {
  const cleanUrl = url.split('?')[0]
  if (_snapshot[cleanUrl] !== undefined) return _snapshot[cleanUrl] as T
  if (_snapshot[url] !== undefined) return _snapshot[url] as T
  return null
}

const request = async <T>(url: string, options: RequestInit = {}): Promise<ApiResponse<T>> => {
  try {
    const headers = new Headers(options.headers)
    if (options.body !== undefined && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }

    const res = await fetch(`${BASE_URL}${url}`, {
      ...options,
      headers,
    })

    const text = await res.text()
    const parsedBody = parseBody<T>(text)

    if (!res.ok) {
      // API 失败时尝试快照 fallback
      const snap = findSnapshot<T>(url)
      if (snap) return { data: snap, error: null }
      return {
        data: null,
        error: getErrorMessage(res.status, res.statusText, parsedBody, text),
      }
    }

    return { data: parsedBody, error: null }
  } catch (error) {
    // 网络不可达时用快照 fallback（GitHub Pages 场景）
    const snap = findSnapshot<T>(url)
    if (snap) return { data: snap, error: null }
    return {
      data: null,
      error: error instanceof Error ? error.message : 'Network request failed',
    }
  }
}

export const buildApiUrl = (url: string) => `${BASE_URL}${url}`

export const get = <T>(url: string) => request<T>(url)

export const post = <T>(url: string, body: unknown) =>
  request<T>(url, { method: 'POST', body: JSON.stringify(body) })

export const put = <T>(url: string, body: unknown) =>
  request<T>(url, { method: 'PUT', body: JSON.stringify(body) })

export const del = <T>(url: string) =>
  request<T>(url, { method: 'DELETE' })

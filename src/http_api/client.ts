const BASE_URL = '/api'

type ApiResponse<T> = {
  data: T | null
  error: string | null
}

const request = async <T>(url: string, options?: RequestInit): Promise<ApiResponse<T>> => {
  const res = await fetch(`${BASE_URL}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) return { data: null, error: `${res.status} ${res.statusText}` }
  const data = await res.json()
  return { data, error: null }
}

export const get = <T>(url: string) => request<T>(url)

export const post = <T>(url: string, body: unknown) =>
  request<T>(url, { method: 'POST', body: JSON.stringify(body) })

export const put = <T>(url: string, body: unknown) =>
  request<T>(url, { method: 'PUT', body: JSON.stringify(body) })

export const del = <T>(url: string) =>
  request<T>(url, { method: 'DELETE' })

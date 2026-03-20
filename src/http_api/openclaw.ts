import type { OpenClawSession, OpenClawDocument } from '@/types'

import { get, post } from './client'

export const getSessionsApi = (category?: string) => {
  const qs = category ? `?category=${category}` : ''
  return get<OpenClawSession[]>(`/openclaw/sessions${qs}`)
}

export const getSessionApi = (id: number) => get<OpenClawSession>(`/openclaw/sessions/${id}`)

export const getDocumentsApi = () => get<OpenClawDocument[]>('/openclaw/documents')

export const analyzeSessionApi = (id: number) =>
  post<{
    profile_id: number
    profile_name: string
    matched_patterns: { id: number; slug: string; name: string; confidence: number; matched_terms: string[]; body_preview: string }[]
    summary: string
    status: string
    injected_pattern_slugs: string[]
  }>(`/openclaw/sessions/${id}/analyze`, {})

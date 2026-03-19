import type { OpenClawSession, OpenClawDocument } from '@/types'

import { get } from './client'

export const getSessionsApi = (category?: string) => {
  const qs = category ? `?category=${category}` : ''
  return get<OpenClawSession[]>(`/openclaw/sessions${qs}`)
}

export const getSessionApi = (id: number) => get<OpenClawSession>(`/openclaw/sessions/${id}`)

export const getDocumentsApi = () => get<OpenClawDocument[]>('/openclaw/documents')

import type { DevEvent } from '@/types'

import { buildApiUrl, get } from './client'

export const getEventsApi = (params?: {
  source?: string
  project?: string
  search?: string
  time_range?: string
  limit?: number
  include_seed?: boolean
}) => {
  const query = new URLSearchParams()
  if (params?.source) query.set('source', params.source)
  if (params?.project) query.set('project', params.project)
  if (params?.search) query.set('search', params.search)
  if (params?.time_range) query.set('time_range', params.time_range)
  if (params?.limit !== undefined) query.set('limit', String(params.limit))
  if (params?.include_seed !== undefined) query.set('include_seed', String(params.include_seed))
  const qs = query.toString()
  return get<DevEvent[]>(`/events${qs ? `?${qs}` : ''}`)
}

export const getEventsStreamUrl = () => buildApiUrl('/events/stream')

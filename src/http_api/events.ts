import type { DevEvent } from '@/types'

import { get } from './client'

export const getEventsApi = (params?: { source?: string; project?: string; search?: string; time_range?: string }) => {
  const query = new URLSearchParams()
  if (params?.source) query.set('source', params.source)
  if (params?.project) query.set('project', params.project)
  if (params?.search) query.set('search', params.search)
  if (params?.time_range) query.set('time_range', params.time_range)
  const qs = query.toString()
  return get<DevEvent[]>(`/events${qs ? `?${qs}` : ''}`)
}

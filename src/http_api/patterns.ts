import type { BehaviorPattern, TeamWorkflow } from '@/types'

import { get } from './client'

export const getPatternsApi = (params?: { category?: string; status?: string }) => {
  const query = new URLSearchParams()
  if (params?.category) query.set('category', params.category)
  if (params?.status) query.set('status', params.status)
  const qs = query.toString()
  return get<BehaviorPattern[]>(`/patterns${qs ? `?${qs}` : ''}`)
}

export const getPatternApi = (id: number) => get<BehaviorPattern>(`/patterns/${id}`)

export const getWorkflowsApi = () => get<TeamWorkflow[]>('/workflows')

export const getWorkflowApi = (id: number) => get<TeamWorkflow>(`/workflows/${id}`)

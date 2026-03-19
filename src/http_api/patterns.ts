import type { BehaviorPattern, TeamWorkflow } from '@/types'

import { get, post, put, del } from './client'

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

export const createPatternApi = (data: Partial<BehaviorPattern>) =>
  post<BehaviorPattern>('/patterns', data)

export const updatePatternApi = (id: number, data: Partial<BehaviorPattern>) =>
  put<BehaviorPattern>(`/patterns/${id}`, data)

export const deletePatternApi = (id: number) => del<void>(`/patterns/${id}`)

export const exportPatternsApi = (ids: number[]) =>
  get<BehaviorPattern[]>(`/patterns/export?ids=${ids.join(',')}`)

export const importPatternsApi = (data: { patterns: Partial<BehaviorPattern>[] }) =>
  post<{ count: number }>('/patterns/import', data)

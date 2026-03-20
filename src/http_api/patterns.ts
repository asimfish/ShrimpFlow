import type { BehaviorPattern, TeamWorkflow, PatternInsight, PatternTrigger } from '@/types'

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

export type ClawProfileExchangePattern = {
  slug: string
  frontmatter: {
    name: string
    confidence: 'low' | 'medium' | 'high' | 'very_high'
    confidence_score: number
    category: string
    trigger?: string | PatternTrigger | null
    evidence?: number
    source?: string
    learned_from?: PatternInsight[]
  }
  body: string
  evolution: { date: string; score: number; note: string }[]
}

export type ClawProfileExchangeWorkflow = {
  slug: string
  frontmatter: {
    name: string
    steps: TeamWorkflow['steps']
  }
  body: string
}

export type ClawProfileExchange = {
  schema: string
  profile: {
    name: string
    display: string
    description?: string
    author?: string
    tags?: string[]
    license?: string
    trust?: string
    injection?: { mode?: string; budget?: number }
  }
  patterns: ClawProfileExchangePattern[]
  workflows: ClawProfileExchangeWorkflow[]
  exported_at: number
}

export const exportPatternsApi = (ids: number[]) =>
  get<ClawProfileExchange>(`/patterns/export?ids=${ids.join(',')}`)

export const importPatternsApi = (data: {
  profile?: ClawProfileExchange['profile']
  patterns: Partial<BehaviorPattern>[] | ClawProfileExchangePattern[]
  workflows?: ClawProfileExchangeWorkflow[]
}) =>
  post<{ imported: number; workflows: number }>('/patterns/import', data)

// 模式确认/拒绝
export const confirmPatternApi = (id: number) =>
  post<{ id: number; status: string }>(`/patterns/${id}/confirm`, {})

export const rejectPatternApi = (id: number) =>
  post<{ id: number; status: string }>(`/patterns/${id}/reject`, {})

export const getPendingPatternsApi = () =>
  get<BehaviorPattern[]>('/patterns/pending')

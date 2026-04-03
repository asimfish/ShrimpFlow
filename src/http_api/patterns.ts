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

export const createWorkflowApi = (data: {
  name: string
  description: string
  patterns: number[]
  target_team: string
  steps?: TeamWorkflow['steps']
}) => post<TeamWorkflow>('/workflows', data)

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

export const rejectPatternApi = (id: number, reason = '') =>
  post<{ id: number; status: string }>(`/patterns/${id}/reject`, { reason })

export const getPendingPatternsApi = () =>
  get<BehaviorPattern[]>('/patterns/pending')

export const minePatternsApi = () =>
  post<{ patterns: { name: string; description: string; confidence: number; category: string; skill_alignment_score: number }[]; count: number }>('/patterns/mine', {})

// Phase 3: 模式关系
export type PatternRelationItem = {
  id: number
  other_pattern_id: number
  other_pattern_name: string
  relation_type: string
  weight: number
  direction: 'incoming' | 'outgoing'
  evidence: string
}

export const getPatternRelationsApi = (id: number) =>
  get<PatternRelationItem[]>(`/patterns/${id}/relations`)

export const discoverRelationsApi = () =>
  post<{ total: number; similar: number; temporal: number; confirmation: number; co_occurrence: number }>('/patterns/discover-relations', {})

// Phase 4: 扩散激活召回
export type RecallResult = {
  query: string
  seeds: { pattern_id: number; name: string; category: string; confidence: number }[]
  activated: {
    pattern_id: number
    name: string
    category: string
    confidence: number
    lifecycle_state: string
    heat_score: number
    activation: number
    hop: number
    path: string[]
  }[]
  total: number
}

export const recallPatternsApi = (query: string, maxHops = 2) =>
  get<RecallResult>(`/patterns/recall?query=${encodeURIComponent(query)}&max_hops=${maxHops}`)

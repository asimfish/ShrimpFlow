import { get, post } from './client'

export type TastePendingPattern = {
  id: number
  name: string
  category: string
  confidence: number
  source: string
  taste_action: 'confirm' | 'collect_more' | 'defer'
  priority_score: number
  taste_reasons: string[]
}

export type TasteProfile = {
  id: number
  created_at: number
  updated_at: number
  preferred_categories: Record<string, number>
  preferred_confidence_threshold: number
  preferred_sources: string[]
  decision_history_count: number
  taste_summary: string | null
  top_pending: TastePendingPattern[]
}

export type AutoConfirmResult = {
  confirmed: number
  deferred: number
  collect_more: number
  confirmed_ids: number[]
}

export const getAgentTasteApi = () => get<TasteProfile>('/agent-taste')

export const relearnAgentTasteApi = () => post<TasteProfile>('/agent-taste/relearn', {})

export const autoConfirmPatternsApi = () => post<AutoConfirmResult>('/agent-taste/auto-confirm', {})

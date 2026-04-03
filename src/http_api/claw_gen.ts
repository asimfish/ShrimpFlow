import { get, post } from './client'

export type CotProfile = {
  session_count: number
  avg_reasoning_depth: number
  step_thinking_rate: number
  analyze_first_rate: number
  tradeoff_rate: number
  verify_rate: number
  total_corrections: number
  total_confirms: number
  top_categories: string[]
  correction_excerpts: string[]
  // V1: 5 taste dimensions
  rigor?: number
  elegance?: number
  novelty?: number
  simplicity?: number
  reproducibility?: number
}

export type AlignmentScore = {
  score: number
  grade: 'A' | 'B' | 'C' | 'D' | 'F'
  confirmed: number
  total: number
  well_supported: number
  top_categories: string[]
}

export type ClawGenResult = {
  cot_skills: { id: number; name: string; confidence: number }[]
  workflow_patterns: { id: number; name: string; confidence: number }[]
  total_generated: number
  timestamp: number
}

export const generateClawsApi = () => post<ClawGenResult>('/claw/generate', {})

export const getCotProfileApi = (lookbackHours = 168) =>
  get<CotProfile>(`/claw/cot-profile?lookback_hours=${lookbackHours}`)

export const getTasteDimensionsApi = (lookbackHours = 336) =>
  get<Record<string, number>>(`/claw/taste-dimensions?lookback_hours=${lookbackHours}`)

export const getAlignmentScoreApi = () =>
  get<AlignmentScore>('/claw/alignment-score')

export const exportMarkdownApi = (ids?: number[]) => {
  const q = ids && ids.length ? `?ids=${ids.join(',')}` : ''
  return get<{ markdown: string; char_count: number }>(`/claw/export-markdown${q}`)
}

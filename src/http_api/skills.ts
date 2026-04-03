import type { LearningPlan, Skill, SkillRecommendation, SkillWorkflow, SkillWorkflowItem } from '@/types'

import { get, post } from './client'

export type { SkillWorkflowItem }

type MinedWorkflowResponseRow = {
  id: number
  name: string
  sequence: string[]
  frequency: number
  success_rate: number
  source: string
  created_at: number
}

export const getSkillsApi = () => get<Skill[]>('/skills')

export const generateLearningPlanApi = (goal: string) =>
  post<LearningPlan>('/skills/learning-plan', { goal })

export const getSkillWorkflowsApi = () => get<SkillWorkflow[]>('/skills/workflows')

export const getMinedWorkflowsApi = async () => {
  const result = await get<MinedWorkflowResponseRow[]>('/skills/workflows/mined')
  if (result.error || !result.data) return { data: null, error: result.error }

  const data: SkillWorkflowItem[] = result.data.map(row => ({
    id: row.id,
    name: row.name,
    skill_sequence: row.sequence,
    frequency: row.frequency,
    success_rate: row.success_rate,
    source: row.source,
    created_at: row.created_at,
  }))

  return { data, error: null }
}

export const getSkillRecommendationsApi = () => get<SkillRecommendation[]>('/skills/recommendations')

export const trackSkillApi = (name: string, invocation_type: string) =>
  post<{ status: string }>('/skills/track', { name, invocation_type })

import type {
  LearningPlan,
  Skill,
  SkillDiscoveryReport,
  SkillRecommendation,
  SkillWorkflow,
  SkillWorkflowItem,
  WorkflowStepDetail,
} from '@/types'

import { get, post, put } from './client'

export type { SkillWorkflowItem }

type MinedWorkflowResponseRow = {
  id: number
  name: string
  sequence: string[]
  frequency: number
  success_rate: number
  source: string
  created_at: number
  updated_at?: number
  description?: string | null
  trigger?: string | null
  steps?: WorkflowStepDetail[]
  status?: string
  context_tags?: string[]
  confirmed_by?: string | null
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
    updated_at: row.updated_at,
    description: row.description,
    trigger: row.trigger,
    steps: row.steps ?? [],
    status: (row.status as SkillWorkflowItem['status']) ?? 'draft',
    context_tags: row.context_tags ?? [],
    confirmed_by: row.confirmed_by,
  }))

  return { data, error: null }
}

export const getSkillRecommendationsApi = () => get<SkillRecommendation[]>('/skills/recommendations')

export const getSkillDiscoveryApi = () => get<SkillDiscoveryReport>('/skills/discovery')

export const trackSkillApi = (
  name: string,
  invocation_type: string,
  options?: { session_id?: number; trigger_source?: string; outcome?: string },
) =>
  post<{ status: string }>('/skills/track', { name, invocation_type, ...options })

export const recommendationFeedbackApi = (skill_name: string, action: 'useful' | 'dismiss') =>
  post<{ status: string }>('/skills/recommendations/feedback', { skill_name, action })

export const updateWorkflowStatusApi = (workflowId: number, status: 'draft' | 'confirmed' | 'archived') =>
  put<{ id: number; status: string }>(`/skills/workflows/${workflowId}/status`, { status })

export const summarizeWorkflowsApi = () =>
  post<{ summarized: number; workflows: SkillWorkflowItem[] }>('/skills/workflows/summarize', {})

export const summarizeWorkflowApi = (workflowId: number) =>
  post<SkillWorkflowItem>(`/skills/workflows/${workflowId}/summarize`, {})

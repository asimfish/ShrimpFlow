import type { LearningPlan, Skill } from '@/types'

import { get, post } from './client'

export const getSkillsApi = () => get<Skill[]>('/skills')

export const generateLearningPlanApi = (goal: string) =>
  post<LearningPlan>('/skills/learning-plan', { goal })

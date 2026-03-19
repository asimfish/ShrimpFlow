import type { Skill } from '@/types'

import { get } from './client'

export const getSkillsApi = () => get<Skill[]>('/skills')

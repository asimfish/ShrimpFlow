import type { StatsOverview } from '@/types'

import { get } from './client'

export const getStatsApi = () => get<StatsOverview>('/stats')

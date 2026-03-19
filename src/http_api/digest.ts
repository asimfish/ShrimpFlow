import type { DailySummary } from '@/types'

import { get } from './client'

export const getDigestsApi = () => get<DailySummary[]>('/digest')

export const getDigestApi = (date: string) => get<DailySummary>(`/digest/${date}`)

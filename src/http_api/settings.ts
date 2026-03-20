import type { AISettings, AIProviderStrategy, ScheduleConfig } from '@/types'

import { get, post } from './client'

export const getScheduleApi = () => get<ScheduleConfig>('/settings/schedule')

export const updateScheduleApi = (data: { enabled?: boolean; interval_hours?: number }) =>
  post<ScheduleConfig>('/settings/schedule', data)

export const getAISettingsApi = () => get<AISettings>('/settings/ai')

export const updateAISettingsApi = (data: {
  selected_provider?: string
  provider_strategy?: AIProviderStrategy
  default_model?: string
  selector_model?: string
}) => post<AISettings>('/settings/ai', data)

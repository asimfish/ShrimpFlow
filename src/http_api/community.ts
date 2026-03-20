import type { ClawProfile, SharedClawProfile, SharedProfile, SharedPatternPack } from '@/types'
import type { ClawProfileExchangeWorkflow } from './patterns'

import { get, post } from './client'

export const getProfilesApi = () => get<SharedProfile[]>('/community/profiles')

export const getPacksApi = (category?: string) => {
  const qs = category ? `?category=${category}` : ''
  return get<SharedPatternPack[]>(`/community/packs${qs}`)
}

export const getPackApi = (id: number) => get<SharedPatternPack>(`/community/packs/${id}`)

export const createPackApi = (data: {
  name: string
  description: string
  category: string
  patterns: object[]
  tags: string[]
}) => post<SharedPatternPack>('/community/packs', data)

export const getSharedClawProfilesApi = () => get<SharedClawProfile[]>('/community/claw-profiles')
export const getSharedClawProfileApi = (id: number) => get<SharedClawProfile>(`/community/claw-profiles/${id}`)
export const starSharedClawProfileApi = (id: number) => post<{ stars: number }>(`/community/claw-profiles/${id}/star`, {})
export const downloadSharedClawProfileApi = (id: number) => post<SharedClawProfile>(`/community/claw-profiles/${id}/download`, {})

export const createSharedClawProfileApi = (data: {
  name: string
  display: string
  description: string
  profile: Partial<ClawProfile>
  patterns: object[]
  workflows: ClawProfileExchangeWorkflow[]
  tags: string[]
}) => post<SharedClawProfile>('/community/claw-profiles', data)

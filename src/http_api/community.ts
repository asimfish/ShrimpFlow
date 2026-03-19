import type { SharedProfile, SharedPatternPack } from '@/types'

import { get } from './client'

export const getProfilesApi = () => get<SharedProfile[]>('/community/profiles')

export const getPacksApi = (category?: string) => {
  const qs = category ? `?category=${category}` : ''
  return get<SharedPatternPack[]>(`/community/packs${qs}`)
}

export const getPackApi = (id: number) => get<SharedPatternPack>(`/community/packs/${id}`)

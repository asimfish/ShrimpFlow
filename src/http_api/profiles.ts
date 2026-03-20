import type { ClawProfile } from '@/types'

import { get, post, put } from './client'

export const getProfilesApi = () => get<ClawProfile[]>('/profiles')

export const getActiveProfileApi = () => get<ClawProfile>('/profiles/active')

export const activateProfileApi = (id: number) => post<ClawProfile>(`/profiles/${id}/activate`, {})

export const updateProfileApi = (id: number, body: Partial<ClawProfile>) =>
  put<ClawProfile>(`/profiles/${id}`, body)

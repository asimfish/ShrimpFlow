import { get } from './client'

type SearchResult = {
  events: { id: number; action: string; source: string; project: string }[]
  patterns: { id: number; name: string; category: string; confidence: number }[]
  sessions: { id: number; title: string; category: string }[]
  packs: { id: number; name: string; category: string }[]
}

export const searchApi = (q: string) => get<SearchResult>(`/search?q=${encodeURIComponent(q)}`)

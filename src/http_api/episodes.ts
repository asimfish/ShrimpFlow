import { get } from './client'

import type { Episode, EpisodeStats, ArchetypeSummary, FeatureGraphStats, EvidenceEntry, EvidenceLedgerStats } from '@/types'

export const getEpisodesApi = (limit = 50, offset = 0, project = '') =>
  get<Episode[]>(`/episodes?limit=${limit}&offset=${offset}&project=${project}`)

export const getEpisodeApi = (id: number) =>
  get<Episode>(`/episodes/${id}`)

export const getEpisodeStatsApi = () =>
  get<EpisodeStats>('/episodes/stats')

// Feature Graph
export const getArchetypesApi = () =>
  get<ArchetypeSummary[]>('/feature-graph/archetypes')

export const getFeatureGraphStatsApi = () =>
  get<FeatureGraphStats>('/feature-graph/stats')

// Evidence Ledger
export const getPatternLedgerApi = (patternId: number, limit = 50) =>
  get<EvidenceEntry[]>(`/evidence-ledger/${patternId}?limit=${limit}`)

export const getEvidenceLedgerStatsApi = () =>
  get<EvidenceLedgerStats>('/evidence-ledger-stats')

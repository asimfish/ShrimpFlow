import type { MemoryHealth, StatsOverview } from '@/types'

import { get, post } from './client'

export const getStatsApi = () => get<StatsOverview>('/stats')

export const getMemoryHealthApi = () => get<MemoryHealth>('/memory/health')

export const triggerDecayApi = () => post<Record<string, number>>('/memory/decay', {})

export const triggerConsolidationApi = () => post<Record<string, unknown>>('/memory/consolidate', {})

export type FullCycleReport = {
  elapsed_seconds: number
  health_before: MemoryHealth
  health_after: MemoryHealth
  health_diff: Record<string, { before: string | number; after: string | number; change: string }>
  lifecycle_diff: Record<string, { before: number; after: number; change: string }>
  decay: { total_patterns: number; decayed: number; lifecycle_changes: number }
  consolidation: {
    prune: { pruned: number; pruned_ids: number[] }
    merge: { merged: number; pairs: { winner: number; loser: number; similarity: number }[] }
    mature: { matured: number; matured_ids: number[] }
  }
  relations: { total: number; similar: number; temporal: number; confirmation: number; co_occurrence: number }
  compression: { patterns_processed: number; total_compressed: number }
  bottlenecks: { metric: string; value: string | number; desc: string }[]
  issues: string[]
}

export const runFullCycleApi = () => post<FullCycleReport>('/memory/full-cycle', {})

export type FlywheelPoint = {
  date: string
  total: number
  confirmed: number
  avg_confidence: number
}

export const getFlywheelTrendApi = () => get<{ points: FlywheelPoint[] }>('/stats/flywheel-trend')

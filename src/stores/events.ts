import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import type { DevEvent } from '@/types'
import { mockEvents } from '@/mock/data'

export const useEventsStore = defineStore('events', () => {
  const events = ref<DevEvent[]>(mockEvents)
  const sourceFilter = ref<string>('')
  const projectFilter = ref<string>('')
  const searchQuery = ref('')
  const timeRange = ref<'today' | 'week' | 'month' | 'all'>('all')

  const filteredEvents = computed(() =>
    events.value.filter(e => {
      if (sourceFilter.value && e.source !== sourceFilter.value) return false
      if (projectFilter.value && e.project !== projectFilter.value) return false
      if (searchQuery.value && !e.action.toLowerCase().includes(searchQuery.value.toLowerCase())) return false
      // 时间范围过滤
      if (timeRange.value !== 'all') {
        const now = Math.floor(Date.now() / 1000)
        const DAY = 86400
        const cutoff = timeRange.value === 'today' ? now - DAY
          : timeRange.value === 'week' ? now - 7 * DAY
          : now - 30 * DAY
        if (e.timestamp < cutoff) return false
      }
      return true
    })
  )

  const projects = computed(() => [...new Set(events.value.map(e => e.project))])

  const eventsByDate = computed(() => {
    const map = new Map<string, DevEvent[]>()
    for (const e of events.value) {
      const d = new Date(e.timestamp * 1000)
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(e)
    }
    return map
  })

  return { events, filteredEvents, sourceFilter, projectFilter, searchQuery, timeRange, projects, eventsByDate }
})

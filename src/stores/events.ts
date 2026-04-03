import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import type { DevEvent, EventSource as DevEventSource } from '@/types'
import { getEventsApi, getEventsStreamUrl } from '@/http_api/events'

type RealtimeStatus = 'idle' | 'connecting' | 'connected' | 'disconnected'

const LIVE_EVENT_LIMIT = 4
const RECENT_SYNC_LIMIT = 200
const RECENT_SYNC_INTERVAL_MS = 30000
const RECONNECT_DELAY_MS = 3000

const sortEventsDesc = (items: DevEvent[]) =>
  [...items].sort((a, b) => b.timestamp - a.timestamp || b.id - a.id)

const uniqueEvents = (items: DevEvent[]) => {
  const seen = new Map<number, DevEvent>()
  for (const item of items) {
    seen.set(item.id, item)
  }
  return sortEventsDesc([...seen.values()])
}

const normalizeEvent = (payload: unknown): DevEvent | null => {
  if (!payload || typeof payload !== 'object') return null

  const raw = payload as Partial<DevEvent> & { type?: string }
  if (raw.type === 'heartbeat' || typeof raw.id !== 'number') return null
  if (typeof raw.timestamp !== 'number' || typeof raw.action !== 'string' || typeof raw.source !== 'string') return null

  return {
    id: raw.id,
    timestamp: raw.timestamp,
    source: raw.source as DevEventSource,
    action: raw.action,
    directory: typeof raw.directory === 'string' ? raw.directory : '',
    project: typeof raw.project === 'string' ? raw.project : '',
    branch: typeof raw.branch === 'string' ? raw.branch : '',
    exit_code: typeof raw.exit_code === 'number' ? raw.exit_code : 0,
    duration_ms: typeof raw.duration_ms === 'number' ? raw.duration_ms : 0,
    semantic: typeof raw.semantic === 'string' ? raw.semantic : '',
    tags: Array.isArray(raw.tags) ? raw.tags.filter((tag): tag is string => typeof tag === 'string') : [],
    openclaw_session_id: typeof raw.openclaw_session_id === 'number' ? raw.openclaw_session_id : undefined,
  }
}

export const useEventsStore = defineStore('events', () => {
  const events = ref<DevEvent[]>([])
  const liveEvents = ref<DevEvent[]>([])
  const sourceFilter = ref<string>('')
  const projectFilter = ref<string>('')
  const searchQuery = ref('')
  const timeRange = ref<'today' | 'week' | 'month' | 'all'>('all')
  const loading = ref(false)
  const error = ref<string | null>(null)
  const loaded = ref(false)
  const realtimeStatus = ref<RealtimeStatus>('idle')
  const realtimeError = ref<string | null>(null)
  const lastRealtimeEventAt = ref(0)

  let stream: globalThis.EventSource | null = null
  let realtimeStarted = false
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let recentSyncTimer: ReturnType<typeof setTimeout> | null = null
  let periodicSyncTimer: ReturnType<typeof setInterval> | null = null
  let recentSyncInFlight = false
  let fetchPromise: Promise<{ data: DevEvent[] | null; error: string | null }> | null = null

  const mergeEvents = (incoming: DevEvent[]) => {
    if (!incoming.length) return 0

    const existingIds = new Set(events.value.map(event => event.id))
    const addedEvents = incoming.filter(event => !existingIds.has(event.id))
    events.value = uniqueEvents([...events.value, ...incoming])
    return addedEvents.length
  }

  const pushLiveEvent = (event: DevEvent) => {
    liveEvents.value = uniqueEvents([event, ...liveEvents.value]).slice(0, LIVE_EVENT_LIMIT)
  }

  const fetchEvents = async (force = false) => {
    if (!force && fetchPromise) return fetchPromise
    if (!force && loaded.value) return { data: events.value, error: null }

    loading.value = true
    error.value = null
    fetchPromise = (async () => {
      try {
        const result = await getEventsApi()
        if (result.data) {
          events.value = uniqueEvents(result.data)
          loaded.value = true
          if (!liveEvents.value.length) {
            liveEvents.value = events.value.slice(0, LIVE_EVENT_LIMIT)
          }
        } else if (result.error) {
          error.value = result.error
          console.error(result.error)
        }
        return result
      } catch (e) {
        console.error(e)
        const msg = e instanceof Error ? e.message : '事件加载失败'
        error.value = msg
        return { data: null, error: msg }
      }
    })()

    try {
      return await fetchPromise
    } finally {
      fetchPromise = null
      loading.value = false
    }
  }

  const syncRecentEvents = async () => {
    if (recentSyncInFlight) return

    recentSyncInFlight = true
    try {
      const { data, error: syncErr } = await getEventsApi({ limit: RECENT_SYNC_LIMIT })
      if (syncErr) {
        error.value = syncErr
        console.error(syncErr)
      }
      if (data) {
        loaded.value = true
        const addedCount = mergeEvents(data)
        liveEvents.value = uniqueEvents([...data, ...liveEvents.value]).slice(0, LIVE_EVENT_LIMIT)
        if (addedCount > 0) {
          lastRealtimeEventAt.value = Date.now()
        }
        if (!liveEvents.value.length) {
          liveEvents.value = uniqueEvents(data).slice(0, LIVE_EVENT_LIMIT)
        }
      }
    } catch (e) {
      console.error(e)
      error.value = e instanceof Error ? e.message : '近期事件同步失败'
    }
    recentSyncInFlight = false
  }

  const scheduleRecentSync = (delayMs = 1200) => {
    if (recentSyncTimer) clearTimeout(recentSyncTimer)
    recentSyncTimer = setTimeout(() => {
      recentSyncTimer = null
      void syncRecentEvents()
    }, delayMs)
  }

  const handleIncomingEvent = (event: DevEvent) => {
    const addedCount = mergeEvents([event])
    pushLiveEvent(event)
    if (addedCount > 0) {
      lastRealtimeEventAt.value = Date.now()
      scheduleRecentSync()
    }
  }

  const closeStream = () => {
    if (!stream) return
    stream.onopen = null
    stream.onmessage = null
    stream.onerror = null
    stream.close()
    stream = null
  }

  const scheduleReconnect = () => {
    if (!realtimeStarted || reconnectTimer) return
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connectStream()
    }, RECONNECT_DELAY_MS)
  }

  const connectStream = () => {
    if (!realtimeStarted || typeof window === 'undefined') return

    closeStream()
    realtimeStatus.value = 'connecting'
    realtimeError.value = null

    const nextStream = new window.EventSource(getEventsStreamUrl())
    stream = nextStream

    nextStream.onopen = () => {
      realtimeStatus.value = 'connected'
      realtimeError.value = null
    }

    nextStream.onmessage = message => {
      let payload: unknown

      try {
        payload = JSON.parse(message.data)
      } catch {
        scheduleRecentSync(0)
        return
      }

      if (payload && typeof payload === 'object' && 'type' in payload && payload.type === 'heartbeat') {
        return
      }

      // 模式待确认推送
      if (payload && typeof payload === 'object' && 'type' in payload && payload.type === 'pattern_pending') {
        const detail = (payload as Record<string, unknown>).pattern
        window.dispatchEvent(new CustomEvent('pattern-pending', { detail }))
        return
      }

      const event = normalizeEvent(payload)
      if (event) {
        handleIncomingEvent(event)
        return
      }

      scheduleRecentSync(0)
    }

    nextStream.onerror = () => {
      realtimeStatus.value = 'disconnected'
      realtimeError.value = '实时事件流连接中断，正在重连'
      closeStream()
      scheduleReconnect()
    }
  }

  const startRealtime = () => {
    if (realtimeStarted) return

    realtimeStarted = true
    void syncRecentEvents()
    connectStream()
    periodicSyncTimer = setInterval(() => {
      void syncRecentEvents()
    }, RECENT_SYNC_INTERVAL_MS)
  }

  const stopRealtime = () => {
    realtimeStarted = false
    closeStream()
    realtimeStatus.value = 'idle'
    realtimeError.value = null

    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }

    if (recentSyncTimer) {
      clearTimeout(recentSyncTimer)
      recentSyncTimer = null
    }

    if (periodicSyncTimer) {
      clearInterval(periodicSyncTimer)
      periodicSyncTimer = null
    }
  }

  const ensureLoaded = () => fetchEvents(false)

  const filteredEvents = computed(() =>
    events.value.filter(event => {
      if (sourceFilter.value && event.source !== sourceFilter.value) return false
      if (projectFilter.value && event.project !== projectFilter.value) return false
      if (searchQuery.value && !event.action.toLowerCase().includes(searchQuery.value.toLowerCase())) return false
      if (timeRange.value !== 'all') {
        const now = Math.floor(Date.now() / 1000)
        const DAY = 86400
        const cutoff = timeRange.value === 'today'
          ? now - DAY
          : timeRange.value === 'week'
            ? now - 7 * DAY
            : now - 30 * DAY
        if (event.timestamp < cutoff) return false
      }
      return true
    }),
  )

  const projects = computed(() => [...new Set(events.value.map(event => event.project))])

  const eventsByDate = computed(() => {
    const map = new Map<string, DevEvent[]>()
    for (const event of events.value) {
      const d = new Date(event.timestamp * 1000)
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(event)
    }
    return map
  })

  return {
    events,
    liveEvents,
    filteredEvents,
    sourceFilter,
    projectFilter,
    searchQuery,
    timeRange,
    projects,
    eventsByDate,
    loading,
    error,
    loaded,
    realtimeStatus,
    realtimeError,
    lastRealtimeEventAt,
    fetchEvents,
    ensureLoaded,
    startRealtime,
    stopRealtime,
    syncRecentEvents,
  }
})

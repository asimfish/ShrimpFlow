import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import type { OpenClawSession, OpenClawDocument } from '@/types'
import { analyzeSessionApi, getSessionsApi, getDocumentsApi } from '@/http_api/openclaw'

export const useOpenClawStore = defineStore('openclaw', () => {
  const sessions = ref<OpenClawSession[]>([])
  const documents = ref<OpenClawDocument[]>([])
  const selectedSessionId = ref<number | null>(null)
  const activeTab = ref<'sessions' | 'documents'>('sessions')
  const categoryFilter = ref('')
  const originFilter = ref<'all' | OpenClawSession['origin']>('all')
  const documentOriginFilter = ref<'all' | OpenClawDocument['origin']>('all')
  const documentTypeFilter = ref<'all' | OpenClawDocument['type']>('all')
  const loading = ref(false)
  const analyzing = ref(false)
  const sessionsLoaded = ref(false)
  const documentsLoaded = ref(false)
  let sessionsPromise: Promise<{ data: OpenClawSession[] | null; error: string | null }> | null = null
  let documentsPromise: Promise<{ data: OpenClawDocument[] | null; error: string | null }> | null = null

  const fetchSessions = async (force = false) => {
    if (!force && sessionsPromise) return sessionsPromise
    if (!force && sessionsLoaded.value) return { data: sessions.value, error: null }

    loading.value = true
    sessionsPromise = (async () => {
      const result = await getSessionsApi()
      if (result.data) {
        sessions.value = result.data
        sessionsLoaded.value = true
      }
      return result
    })()

    try {
      return await sessionsPromise
    } finally {
      sessionsPromise = null
      loading.value = false
    }
  }

  const fetchDocuments = async (force = false) => {
    if (!force && documentsPromise) return documentsPromise
    if (!force && documentsLoaded.value) return { data: documents.value, error: null }

    documentsPromise = (async () => {
      const result = await getDocumentsApi()
      if (result.data) {
        documents.value = result.data
        documentsLoaded.value = true
      }
      return result
    })()

    try {
      return await documentsPromise
    } finally {
      documentsPromise = null
    }
  }

  const selectedSession = computed(() =>
    sessions.value.find(s => s.id === selectedSessionId.value) ?? null
  )

  const filteredSessions = computed(() => {
    return sessions.value.filter(session => {
      if (categoryFilter.value && session.category !== categoryFilter.value) return false
      if (originFilter.value !== 'all' && session.origin !== originFilter.value) return false
      return true
    })
  })

  const filteredDocuments = computed(() =>
    documents.value.filter(doc => {
      if (documentOriginFilter.value !== 'all' && doc.origin !== documentOriginFilter.value) return false
      if (documentTypeFilter.value !== 'all' && doc.type !== documentTypeFilter.value) return false
      return true
    }),
  )

  const recentSessions = computed(() =>
    [...sessions.value].sort((a, b) => b.created_at - a.created_at).slice(0, 3)
  )

  const selectSession = (id: number) => {
    selectedSessionId.value = id
    activeTab.value = 'sessions'
  }

  const analyzeSelectedSession = async () => {
    if (!selectedSessionId.value) return null
    analyzing.value = true
    try {
      const result = await analyzeSessionApi(selectedSessionId.value)
      if (result.data) {
        await fetchSessions(true)
      }
      return result
    } finally {
      analyzing.value = false
    }
  }

  const ensureSessionsLoaded = () => fetchSessions(false)
  const ensureDocumentsLoaded = () => fetchDocuments(false)

  return {
    sessions,
    documents,
    selectedSessionId,
    selectedSession,
    activeTab,
    categoryFilter,
    originFilter,
    documentOriginFilter,
    documentTypeFilter,
    filteredSessions,
    filteredDocuments,
    recentSessions,
    selectSession,
    loading,
    analyzing,
    sessionsLoaded,
    documentsLoaded,
    fetchSessions,
    fetchDocuments,
    ensureSessionsLoaded,
    ensureDocumentsLoaded,
    analyzeSelectedSession,
  }
})

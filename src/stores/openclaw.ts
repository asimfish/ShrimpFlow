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
  const loading = ref(false)
  const analyzing = ref(false)

  const fetchSessions = async () => {
    loading.value = true
    const { data } = await getSessionsApi()
    if (data) sessions.value = data
    loading.value = false
  }

  const fetchDocuments = async () => {
    const { data } = await getDocumentsApi()
    if (data) documents.value = data
  }

  const selectedSession = computed(() =>
    sessions.value.find(s => s.id === selectedSessionId.value) ?? null
  )

  const filteredSessions = computed(() => {
    if (!categoryFilter.value) return sessions.value
    return sessions.value.filter(s => s.category === categoryFilter.value)
  })

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
        await fetchSessions()
      }
      return result
    } finally {
      analyzing.value = false
    }
  }

  return { sessions, documents, selectedSessionId, selectedSession, activeTab, categoryFilter, filteredSessions, recentSessions, selectSession, loading, analyzing, fetchSessions, fetchDocuments, analyzeSelectedSession }
})

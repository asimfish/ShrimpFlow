import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import type { OpenClawSession, OpenClawDocument } from '@/types'
import { mockSessions, mockDocuments } from '@/mock/data'

export const useOpenClawStore = defineStore('openclaw', () => {
  const sessions = ref<OpenClawSession[]>(mockSessions)
  const documents = ref<OpenClawDocument[]>(mockDocuments)
  const selectedSessionId = ref<number | null>(null)
  const activeTab = ref<'sessions' | 'documents'>('sessions')
  const categoryFilter = ref('')

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

  return { sessions, documents, selectedSessionId, selectedSession, activeTab, categoryFilter, filteredSessions, recentSessions, selectSession }
})

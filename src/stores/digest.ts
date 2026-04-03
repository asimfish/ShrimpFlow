import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { DailySummary } from '@/types'
import { getDigestsApi } from '@/http_api/digest'

export const useDigestStore = defineStore('digest', () => {
  const summaries = ref<DailySummary[]>([])
  const selectedDate = ref('')
  const loading = ref(false)
  const error = ref<string | null>(null)
  const loaded = ref(false)
  let fetchPromise: Promise<{ data: DailySummary[] | null; error: string | null }> | null = null

  const fetchSummaries = async (force = false) => {
    if (!force && fetchPromise) return fetchPromise
    if (!force && loaded.value) return { data: summaries.value, error: null }

    loading.value = true
    error.value = null
    fetchPromise = (async () => {
      try {
        const result = await getDigestsApi()
        if (result.data) {
          summaries.value = result.data
          loaded.value = true
        } else if (result.error) {
          error.value = result.error
          console.error(result.error)
        }
        return result
      } catch (e) {
        console.error(e)
        const msg = e instanceof Error ? e.message : '摘要加载失败'
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

  const getSummary = (date: string) => summaries.value.find(s => s.date === date)

  const ensureLoaded = () => fetchSummaries(false)

  return { summaries, selectedDate, getSummary, loading, error, loaded, fetchSummaries, ensureLoaded }
})

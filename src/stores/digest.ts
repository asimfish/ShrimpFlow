import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { DailySummary } from '@/types'
import { getDigestsApi } from '@/http_api/digest'

export const useDigestStore = defineStore('digest', () => {
  const summaries = ref<DailySummary[]>([])
  const selectedDate = ref('')
  const loading = ref(false)

  const fetchSummaries = async () => {
    loading.value = true
    const { data } = await getDigestsApi()
    if (data) summaries.value = data
    loading.value = false
  }

  const getSummary = (date: string) => summaries.value.find(s => s.date === date)

  return { summaries, selectedDate, getSummary, loading, fetchSummaries }
})

import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { DailySummary } from '@/types'
import { mockSummaries } from '@/mock/data'

export const useDigestStore = defineStore('digest', () => {
  const summaries = ref<DailySummary[]>(mockSummaries)
  const selectedDate = ref('')

  const getSummary = (date: string) => summaries.value.find(s => s.date === date)

  return { summaries, selectedDate, getSummary }
})

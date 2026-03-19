import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { BehaviorPattern, TeamWorkflow } from '@/types'
import * as patternsApi from '@/http_api/patterns'

export const usePatternsStore = defineStore('patterns', () => {
  const patterns = ref<BehaviorPattern[]>([])
  const workflows = ref<TeamWorkflow[]>([])
  const loading = ref(false)

  const fetchPatterns = async (params?: { category?: string; status?: string }) => {
    loading.value = true
    const { data } = await patternsApi.getPatternsApi(params)
    if (data) patterns.value = data
    loading.value = false
  }

  const fetchWorkflows = async () => {
    loading.value = true
    const { data } = await patternsApi.getWorkflowsApi()
    if (data) workflows.value = data
    loading.value = false
  }

  const createPattern = async (patternData: Partial<BehaviorPattern>) => {
    const { data } = await patternsApi.createPatternApi(patternData)
    if (data) patterns.value = [...patterns.value, data]
    return data
  }

  const updatePattern = async (id: number, patternData: Partial<BehaviorPattern>) => {
    const { data } = await patternsApi.updatePatternApi(id, patternData)
    if (data) patterns.value = patterns.value.map(p => p.id === id ? data : p)
    return data
  }

  const deletePattern = async (id: number) => {
    const { error } = await patternsApi.deletePatternApi(id)
    if (!error) patterns.value = patterns.value.filter(p => p.id !== id)
    return !error
  }

  return { patterns, workflows, loading, fetchPatterns, fetchWorkflows, createPattern, updatePattern, deletePattern }
})

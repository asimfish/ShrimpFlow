import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { BehaviorPattern, TeamWorkflow } from '@/types'
import * as patternsApi from '@/http_api/patterns'

export const usePatternsStore = defineStore('patterns', () => {
  const patterns = ref<BehaviorPattern[]>([])
  const workflows = ref<TeamWorkflow[]>([])
  const loading = ref(false)
  const patternsError = ref<string | null>(null)
  const workflowsError = ref<string | null>(null)

  const fetchPatterns = async (params?: { category?: string; status?: string }) => {
    loading.value = true
    patternsError.value = null

    try {
      const result = await patternsApi.getPatternsApi(params)
      if (result.data) patterns.value = result.data
      else patternsError.value = result.error ?? '行为模式加载失败'
      return result
    } finally {
      loading.value = false
    }
  }

  const fetchWorkflows = async () => {
    loading.value = true
    workflowsError.value = null

    try {
      const result = await patternsApi.getWorkflowsApi()
      if (result.data) workflows.value = result.data
      else workflowsError.value = result.error ?? '工作流加载失败'
      return result
    } finally {
      loading.value = false
    }
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

  return {
    patterns,
    workflows,
    loading,
    patternsError,
    workflowsError,
    fetchPatterns,
    fetchWorkflows,
    createPattern,
    updatePattern,
    deletePattern,
  }
})

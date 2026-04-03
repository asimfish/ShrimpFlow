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
  const patternsLoaded = ref(false)
  const workflowsLoaded = ref(false)
  let patternsPromise: Promise<{ data: BehaviorPattern[] | null; error: string | null }> | null = null
  let workflowsPromise: Promise<{ data: TeamWorkflow[] | null; error: string | null }> | null = null

  const fetchPatterns = async (params?: { category?: string; status?: string }, force = false) => {
    const canUseCache = !params?.category && !params?.status
    if (!force && canUseCache && patternsPromise) return patternsPromise
    if (!force && canUseCache && patternsLoaded.value) return { data: patterns.value, error: null }

    loading.value = true
    patternsError.value = null

    patternsPromise = (async () => {
      try {
        const result = await patternsApi.getPatternsApi(params)
        if (result.data) patterns.value = result.data
        else patternsError.value = result.error ?? '行为模式加载失败'
        if (result.data && canUseCache) patternsLoaded.value = true
        return result
      } catch (e) {
        console.error(e)
        const msg = e instanceof Error ? e.message : '行为模式加载失败'
        patternsError.value = msg
        return { data: null, error: msg }
      }
    })()

    try {
      return await patternsPromise
    } finally {
      patternsPromise = null
      loading.value = false
    }
  }

  const fetchWorkflows = async (force = false) => {
    if (!force && workflowsPromise) return workflowsPromise
    if (!force && workflowsLoaded.value) return { data: workflows.value, error: null }

    loading.value = true
    workflowsError.value = null

    workflowsPromise = (async () => {
      try {
        const result = await patternsApi.getWorkflowsApi()
        if (result.data) workflows.value = result.data
        else workflowsError.value = result.error ?? '工作流加载失败'
        if (result.data) workflowsLoaded.value = true
        return result
      } catch (e) {
        console.error(e)
        const msg = e instanceof Error ? e.message : '工作流加载失败'
        workflowsError.value = msg
        return { data: null, error: msg }
      }
    })()

    try {
      return await workflowsPromise
    } finally {
      workflowsPromise = null
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

  const ensurePatternsLoaded = () => fetchPatterns(undefined, false)
  const ensureWorkflowsLoaded = () => fetchWorkflows(false)

  return {
    patterns,
    workflows,
    loading,
    patternsError,
    workflowsError,
    patternsLoaded,
    workflowsLoaded,
    fetchPatterns,
    fetchWorkflows,
    ensurePatternsLoaded,
    ensureWorkflowsLoaded,
    createPattern,
    updatePattern,
    deletePattern,
  }
})

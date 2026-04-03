import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { Skill } from '@/types'
import { getSkillsApi } from '@/http_api/skills'

export const useSkillsStore = defineStore('skills', () => {
  const skills = ref<Skill[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const loaded = ref(false)
  let fetchPromise: Promise<{ data: Skill[] | null; error: string | null }> | null = null

  const fetchSkills = async (force = false) => {
    if (!force && fetchPromise) return fetchPromise
    if (!force && loaded.value) return { data: skills.value, error: null }

    loading.value = true
    error.value = null
    fetchPromise = (async () => {
      try {
        const result = await getSkillsApi()
        if (result.data) {
          skills.value = result.data
          loaded.value = true
        } else if (result.error) {
          error.value = result.error
          console.error(result.error)
        }
        return result
      } catch (e) {
        console.error(e)
        const msg = e instanceof Error ? e.message : '技能加载失败'
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

  const ensureLoaded = () => fetchSkills(false)

  return { skills, loading, error, loaded, fetchSkills, ensureLoaded }
})

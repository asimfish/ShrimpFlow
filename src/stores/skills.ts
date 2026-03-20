import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { Skill } from '@/types'
import { getSkillsApi } from '@/http_api/skills'

export const useSkillsStore = defineStore('skills', () => {
  const skills = ref<Skill[]>([])
  const loading = ref(false)
  const loaded = ref(false)
  let fetchPromise: Promise<{ data: Skill[] | null; error: string | null }> | null = null

  const fetchSkills = async (force = false) => {
    if (!force && fetchPromise) return fetchPromise
    if (!force && loaded.value) return { data: skills.value, error: null }

    loading.value = true
    fetchPromise = (async () => {
      const result = await getSkillsApi()
      if (result.data) {
        skills.value = result.data
        loaded.value = true
      }
      return result
    })()

    try {
      return await fetchPromise
    } finally {
      fetchPromise = null
      loading.value = false
    }
  }

  const ensureLoaded = () => fetchSkills(false)

  return { skills, loading, loaded, fetchSkills, ensureLoaded }
})

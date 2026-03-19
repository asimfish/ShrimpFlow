import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { Skill } from '@/types'
import { getSkillsApi } from '@/http_api/skills'

export const useSkillsStore = defineStore('skills', () => {
  const skills = ref<Skill[]>([])
  const loading = ref(false)

  const fetchSkills = async () => {
    loading.value = true
    const { data } = await getSkillsApi()
    if (data) skills.value = data
    loading.value = false
  }

  return { skills, loading, fetchSkills }
})

import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { Skill } from '@/types'
import { mockSkills } from '@/mock/data'

export const useSkillsStore = defineStore('skills', () => {
  const skills = ref<Skill[]>(mockSkills)
  return { skills }
})

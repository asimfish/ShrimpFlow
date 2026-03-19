<script setup lang="ts">
import { ref } from 'vue'

import { useSkillsStore } from '@/stores/skills'
import type { Skill } from '@/types'
import SkillGraph from './skill_graph.vue'
import SkillDetailPanel from './skill_detail_panel.vue'

const skillsStore = useSkillsStore()
const selectedSkill = ref<Skill | null>(null)

const selectSkill = (skill: Skill) => {
  selectedSkill.value = skill
}

const closeDetail = () => {
  selectedSkill.value = null
}
</script>

<template>
  <div class="flex h-full">
    <div class="flex-1 flex flex-col overflow-hidden">
      <div class="p-6 pb-3">
        <h1 class="text-2xl font-semibold">技能图谱</h1>
        <p class="text-sm text-gray-400 mt-1">OpenClaw 追踪的开发者技能图</p>
      </div>
      <SkillGraph :skills="skillsStore.skills" @select="selectSkill" />
    </div>
    <SkillDetailPanel :skill="selectedSkill" @close="closeDetail" />
  </div>
</template>

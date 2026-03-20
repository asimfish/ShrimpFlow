<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { useSkillsStore } from '@/stores/skills'
import type { LearningPlan, Skill } from '@/types'
import { generateLearningPlanApi } from '@/http_api/skills'
import SkillGraph from './skill_graph.vue'
import SkillDetailPanel from './skill_detail_panel.vue'

const skillsStore = useSkillsStore()
const selectedSkill = ref<Skill | null>(null)
const learningGoal = ref('')
const planning = ref(false)
const planError = ref('')
const learningPlan = ref<LearningPlan | null>(null)

const selectSkill = (skill: Skill) => {
  selectedSkill.value = skill
}

const closeDetail = () => {
  selectedSkill.value = null
}

onMounted(() => {
  void skillsStore.ensureLoaded()
})

const generatePlan = async () => {
  if (!learningGoal.value.trim()) return
  planning.value = true
  planError.value = ''
  const res = await generateLearningPlanApi(learningGoal.value.trim())
  planning.value = false
  if (res.data) {
    learningPlan.value = res.data
  } else {
    planError.value = res.error ?? '学习计划生成失败'
  }
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
    <div class="w-[28rem] shrink-0 border-l border-surface-3 bg-surface-1 flex flex-col">
      <div class="p-4 border-b border-surface-3 space-y-3">
        <div>
          <div class="text-sm font-semibold text-gray-200">AI 学习计划</div>
          <div class="text-xs text-gray-500 mt-1">输入你的目标，系统会结合技能图谱和知识库给出下一步提升建议</div>
        </div>
        <textarea
          v-model="learningGoal"
          rows="3"
          placeholder="例如：我想在 2 个月内提升具身智能方向的实验设计、代码实现和论文复现能力"
          class="w-full bg-surface-2 border border-surface-3 rounded-xl px-3 py-2 text-sm text-gray-200 outline-none focus:border-openclaw resize-none"
        />
        <div class="flex items-center justify-between gap-3">
          <div v-if="planError" class="text-[11px] text-red-400">{{ planError }}</div>
          <button
            class="px-3 py-2 rounded-lg text-xs font-medium ml-auto"
            :class="planning ? 'bg-surface-3 text-gray-500' : 'bg-openclaw/15 text-openclaw hover:bg-openclaw/25'"
            :disabled="planning"
            @click="generatePlan"
          >
            {{ planning ? '生成中...' : '生成学习计划' }}
          </button>
        </div>
      </div>

      <div class="flex-1 min-h-0 overflow-y-auto">
        <div v-if="learningPlan" class="p-4 space-y-4">
          <div class="bg-surface-2 rounded-xl p-4 border border-openclaw/15">
            <div class="text-xs text-openclaw mb-2">目标</div>
            <div class="text-sm text-gray-100">{{ learningPlan.goal }}</div>
            <div class="text-xs text-gray-400 mt-3 leading-relaxed">{{ learningPlan.summary }}</div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="bg-surface-2 rounded-xl p-3">
              <div class="text-[11px] text-emerald-400 mb-2">当前强项</div>
              <div class="flex flex-wrap gap-1.5">
                <span v-for="item in learningPlan.strengths" :key="item" class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400">{{ item }}</span>
              </div>
            </div>
            <div class="bg-surface-2 rounded-xl p-3">
              <div class="text-[11px] text-amber-400 mb-2">重点补强</div>
              <div class="flex flex-wrap gap-1.5">
                <span v-for="item in learningPlan.focus_areas" :key="item" class="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400">{{ item }}</span>
              </div>
            </div>
          </div>
          <div v-for="phase in learningPlan.phases" :key="phase.title" class="bg-surface-2 rounded-xl p-4">
            <div class="text-sm font-medium text-gray-100">{{ phase.title }}</div>
            <div class="text-[11px] text-gray-500 mt-1">{{ phase.objective }}</div>
            <div class="mt-3 space-y-2">
              <div v-for="action in phase.actions" :key="action" class="flex items-start gap-2 text-xs text-gray-300">
                <span class="mt-1 w-1.5 h-1.5 rounded-full bg-openclaw shrink-0" />
                <span>{{ action }}</span>
              </div>
            </div>
          </div>
          <div class="bg-surface-2 rounded-xl p-4">
            <div class="text-[11px] text-cyan-300 mb-2">额外建议</div>
            <div class="space-y-2">
              <div v-for="item in learningPlan.recommendations" :key="item" class="text-xs text-gray-300 leading-relaxed">{{ item }}</div>
            </div>
          </div>
        </div>
        <div v-else class="p-4">
          <SkillDetailPanel :skill="selectedSkill" :embedded="true" @close="closeDetail" />
        </div>
      </div>
    </div>
  </div>
</template>

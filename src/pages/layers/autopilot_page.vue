<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { mockWorkflows, mockPatterns } from '@/mock/data'
import type { TeamWorkflow } from '@/types'

const router = useRouter()
const workflows = mockWorkflows
const patterns = mockPatterns

const selectedPatterns = ref<Set<number>>(new Set())
const workflowName = ref('')
const targetTeam = ref('')
const createSuccess = ref(false)

const statusColorMap: Record<string, string> = {
  draft: 'bg-gray-500/20 text-gray-400',
  active: 'bg-accent/20 text-accent',
  distributed: 'bg-emerald-500/20 text-emerald-400',
}

const statusLabel: Record<string, string> = {
  draft: '草稿',
  active: '已激活',
  distributed: '已下发',
}

const executionSteps = ['触发', '检查', '执行', '记录']

const getStepStatus = (wfStatus: string) => {
  if (wfStatus === 'draft') return 0
  if (wfStatus === 'active') return 2
  return 4
}

const getPatternNames = (ids: number[]) =>
  ids.map(id => patterns.find(p => p.id === id)?.name).filter(Boolean)

const togglePattern = (id: number) => {
  if (selectedPatterns.value.has(id)) selectedPatterns.value.delete(id)
  else selectedPatterns.value.add(id)
}

const handleCreate = () => {
  if (!workflowName.value || !targetTeam.value || selectedPatterns.value.size === 0) return
  createSuccess.value = true
  setTimeout(() => {
    createSuccess.value = false
    workflowName.value = ''
    targetTeam.value = ''
    selectedPatterns.value.clear()
  }, 3000)
}

const handleClickWorkflow = (wf: TeamWorkflow) => {
  router.push(`/workflows/${wf.id}`)
}
</script>

<template>
  <div class="p-6 space-y-6 overflow-y-auto h-full">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-semibold">Layer 4: Autopilot</h1>
      <p class="text-sm text-gray-400 mt-1">团队 Workflow 下发</p>
    </div>

    <!-- 执行流程说明 -->
    <div class="bg-surface-1 rounded-xl border border-surface-3 p-4">
      <div class="flex items-center gap-6 justify-center text-sm">
        <div v-for="(step, idx) in executionSteps" :key="step" class="flex items-center gap-3">
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center text-xs text-emerald-400 font-medium">
              {{ idx + 1 }}
            </div>
            <span class="text-gray-300">{{ step }}</span>
          </div>
          <svg v-if="idx < executionSteps.length - 1" class="w-5 h-5 text-gray-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
        </div>
      </div>
    </div>

    <!-- Workflow 列表 -->
    <div>
      <div class="text-sm font-medium mb-3 text-gray-300">Workflow 列表 ({{ workflows.length }})</div>
      <div class="grid grid-cols-2 gap-4">
        <div
          v-for="wf in workflows"
          :key="wf.id"
          class="bg-surface-1 rounded-xl border border-surface-3 p-4 space-y-3 cursor-pointer hover:border-emerald-500/40 transition-colors"
          @click="handleClickWorkflow(wf)"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium text-gray-200">{{ wf.name }}</span>
              <span class="text-[10px] px-2 py-0.5 rounded" :class="statusColorMap[wf.status]">{{ statusLabel[wf.status] }}</span>
            </div>
            <span class="text-xs text-gray-500">目标: {{ wf.target_team }}</span>
          </div>
          <div class="text-xs text-gray-400 leading-relaxed">{{ wf.description }}</div>
          <div class="flex flex-wrap gap-1.5">
            <span v-for="name in getPatternNames(wf.patterns)" :key="name" class="text-[10px] px-2 py-0.5 rounded-full bg-surface-3 text-gray-400">
              {{ name }}
            </span>
          </div>
          <!-- 执行状态步骤条 -->
          <div class="flex items-center gap-1 pt-2 border-t border-surface-3">
            <template v-for="(step, idx) in executionSteps" :key="step">
              <div
                class="flex-1 text-center py-1 rounded text-[10px]"
                :class="idx < getStepStatus(wf.status) ? 'bg-emerald-500/20 text-emerald-400' : 'bg-surface-3 text-gray-600'"
              >
                {{ step }}
              </div>
              <svg v-if="idx < executionSteps.length - 1" class="w-3 h-3 text-gray-600 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6" /></svg>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建新 Workflow -->
    <div class="bg-surface-1 rounded-xl border border-emerald-500/30 p-5 space-y-4">
      <div class="text-sm font-medium text-emerald-400">创建新 Workflow</div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <div class="text-[10px] text-gray-500 mb-1">Workflow 名称</div>
          <input
            v-model="workflowName"
            type="text"
            placeholder="输入 Workflow 名称..."
            class="w-full bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-xs text-gray-300 outline-none focus:border-emerald-500"
          />
        </div>
        <div>
          <div class="text-[10px] text-gray-500 mb-1">目标团队</div>
          <input
            v-model="targetTeam"
            type="text"
            placeholder="输入目标团队..."
            class="w-full bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-xs text-gray-300 outline-none focus:border-emerald-500"
          />
        </div>
      </div>
      <div>
        <div class="text-[10px] text-gray-500 mb-2">选择包含的行为模式</div>
        <div class="grid grid-cols-3 gap-2">
          <label
            v-for="p in patterns"
            :key="p.id"
            class="flex items-center gap-2 bg-surface-2 rounded-lg px-3 py-2 cursor-pointer hover:bg-surface-3/50 transition-colors"
          >
            <input
              type="checkbox"
              :checked="selectedPatterns.has(p.id)"
              class="w-3.5 h-3.5 rounded accent-emerald-500"
              @change="togglePattern(p.id)"
            />
            <span class="text-xs text-gray-300 truncate">{{ p.name }}</span>
          </label>
        </div>
      </div>
      <div class="flex items-center justify-between">
        <div class="text-[10px] text-gray-500">
          已选择 {{ selectedPatterns.size }} 个模式
        </div>
        <button
          class="px-4 py-2 rounded-lg text-xs font-medium transition-colors"
          :class="workflowName && targetTeam && selectedPatterns.size > 0 ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 cursor-pointer' : 'bg-surface-3 text-gray-600 cursor-not-allowed'"
          :disabled="!workflowName || !targetTeam || selectedPatterns.size === 0"
          @click="handleCreate"
        >
          创建
        </button>
      </div>
      <div v-if="createSuccess" class="text-xs text-emerald-400 bg-emerald-500/10 rounded-lg p-2">
        Workflow "{{ workflowName }}" 已成功创建，目标团队: {{ targetTeam }}
      </div>
    </div>
  </div>
</template>

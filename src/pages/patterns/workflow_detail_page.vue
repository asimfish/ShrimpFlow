<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { mockWorkflows, mockPatterns } from '@/mock/data'

const route = useRoute()
const router = useRouter()
const workflow = computed(() => mockWorkflows.find(w => w.id === Number(route.params.id)))
const includedPatterns = computed(() => workflow.value?.patterns.map(id => mockPatterns.find(p => p.id === id)).filter(Boolean) ?? [])

const statusColorMap: Record<string, string> = {
  draft: 'bg-gray-500/20 text-gray-400',
  active: 'bg-accent/20 text-accent',
  distributed: 'bg-emerald-500/20 text-emerald-400',
}

const statusLabel: Record<string, string> = {
  draft: '草稿', active: '已激活', distributed: '已下发',
}

const categoryColorMap: Record<string, string> = {
  git: 'bg-git/20 text-git border-git/30',
  coding: 'bg-accent/20 text-accent border-accent/30',
  review: 'bg-openclaw/20 text-openclaw border-openclaw/30',
  devops: 'bg-terminal/20 text-terminal border-terminal/30',
  collaboration: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
}

const categoryLabel: Record<string, string> = {
  git: 'Git 规范', coding: '编码习惯', review: '代码审查',
  devops: '运维部署', collaboration: '协作模式',
}

const confidenceColor = (c: number) => {
  if (c >= 85) return 'bg-emerald-500'
  if (c >= 70) return 'bg-accent'
  if (c >= 50) return 'bg-openclaw'
  return 'bg-gray-500'
}

const goBack = () => router.push('/patterns')
const goPattern = (id: number) => router.push(`/patterns/${id}`)

const executionSteps = [
  { label: '触发', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
  { label: '检查', icon: 'M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2m-6 9l2 2 4-4' },
  { label: '执行', icon: 'M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z' },
  { label: '记录', icon: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M16 13H8 M16 17H8 M10 9H8' },
]
</script>

<template>
  <div class="p-6 space-y-6 overflow-y-auto h-full">
    <!-- 返回按钮 -->
    <button class="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors cursor-pointer" @click="goBack">
      <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
      返回行为模式列表
    </button>

    <!-- 未找到 -->
    <div v-if="!workflow" class="text-center text-gray-500 py-20">
      <div class="text-lg mb-2">未找到该工作流</div>
      <button class="text-sm text-accent hover:text-accent-glow cursor-pointer" @click="goBack">返回列表</button>
    </div>

    <template v-if="workflow">
      <!-- 顶部信息 -->
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-6">
        <div class="flex items-start justify-between">
          <div class="space-y-2">
            <div class="flex items-center gap-3">
              <h1 class="text-xl font-semibold text-gray-100">{{ workflow.name }}</h1>
              <span class="text-[10px] px-2.5 py-0.5 rounded" :class="statusColorMap[workflow.status]">{{ statusLabel[workflow.status] }}</span>
            </div>
            <div class="text-xs text-gray-500">目标团队: {{ workflow.target_team }}</div>
          </div>
        </div>
      </div>

      <!-- 描述 -->
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-6">
        <div class="text-sm font-medium text-gray-300 mb-3">描述</div>
        <div class="text-sm text-gray-400 leading-relaxed">{{ workflow.description }}</div>
      </div>

      <!-- 包含的行为模式 -->
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-6">
        <div class="text-sm font-medium text-gray-300 mb-4">包含的行为模式 ({{ includedPatterns.length }})</div>
        <div class="grid grid-cols-2 gap-3">
          <div
            v-for="p in includedPatterns"
            :key="p!.id"
            class="bg-surface-2 rounded-lg p-4 space-y-3 cursor-pointer hover:border-accent/40 border border-surface-3 transition-colors"
            @click="goPattern(p!.id)"
          >
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium text-gray-200">{{ p!.name }}</span>
              <span class="text-[10px] px-2 py-0.5 rounded border" :class="categoryColorMap[p!.category]">{{ categoryLabel[p!.category] }}</span>
            </div>
            <div>
              <div class="flex items-center justify-between mb-1">
                <span class="text-[10px] text-gray-500">置信度</span>
                <span class="text-[10px] text-gray-400">{{ p!.confidence }}%</span>
              </div>
              <div class="h-1.5 bg-surface-3 rounded-full overflow-hidden">
                <div class="h-full rounded-full transition-all" :class="confidenceColor(p!.confidence)" :style="{ width: `${p!.confidence}%` }" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 执行流程 -->
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-6">
        <div class="text-sm font-medium text-gray-300 mb-5">执行流程</div>
        <div class="flex items-center justify-center gap-3">
          <template v-for="(step, idx) in executionSteps" :key="step.label">
            <div class="flex flex-col items-center gap-2">
              <div class="w-14 h-14 rounded-xl bg-surface-2 border border-surface-3 flex items-center justify-center">
                <svg class="w-6 h-6 text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path :d="step.icon" /></svg>
              </div>
              <span class="text-xs text-gray-400">{{ step.label }}</span>
            </div>
            <svg v-if="idx < executionSteps.length - 1" class="w-6 h-6 text-gray-600 shrink-0 -mt-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
          </template>
        </div>
      </div>

      <!-- 适用场景 -->
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-6">
        <div class="text-sm font-medium text-gray-300 mb-3">适用场景</div>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="p in includedPatterns"
            :key="'scenarios-' + p!.id"
            class="contents"
          >
            <span
              v-for="scenario in p!.applicable_scenarios"
              :key="scenario"
              class="text-xs px-3 py-1 rounded-full bg-surface-3 text-gray-400 border border-surface-3"
            >
              {{ scenario }}
            </span>
          </span>
        </div>
      </div>
    </template>
  </div>
</template>

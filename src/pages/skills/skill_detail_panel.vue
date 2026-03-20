<script setup lang="ts">
import { computed } from 'vue'

import type { Skill } from '@/types'

const props = defineProps<{
  skill: Skill | null
  embedded?: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const categoryColor: Record<string, string> = {
  openclaw: '#f59e0b',
  language: '#38bdf8',
  devops: '#f87171',
  vcs: '#34d399',
  framework: '#a78bfa',
  tool: '#64748b',
  'package-manager': '#94a3b8',
  editor: '#94a3b8',
  network: '#94a3b8',
}

const categoryLabel: Record<string, string> = {
  openclaw: 'OpenClaw',
  language: '编程语言',
  devops: '运维部署',
  vcs: '版本控制',
  framework: '框架',
  tool: '工具',
  'package-manager': '包管理',
  editor: '编辑器',
  network: '网络',
}

const formatDate = (ts: number) => {
  const d = new Date(ts * 1000)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const lastUsedText = computed(() => {
  if (!props.skill) return ''
  const now = Math.floor(Date.now() / 1000)
  const diff = now - props.skill.last_used
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  return `${Math.floor(diff / 86400)} 天前`
})

const levelDesc = computed(() => {
  if (!props.skill) return ''
  const lv = props.skill.level
  if (lv >= 80) return '专家'
  if (lv >= 60) return '熟练'
  if (lv >= 40) return '中级'
  if (lv >= 20) return '初学'
  return '入门'
})
</script>

<template>
  <div
    v-if="skill"
    :class="props.embedded ? 'bg-surface-1 rounded-xl border border-surface-3 flex flex-col overflow-hidden' : 'w-80 shrink-0 bg-surface-1 border-l border-surface-3 flex flex-col overflow-hidden'"
  >
    <div class="flex items-center justify-between px-4 py-3 border-b border-surface-3">
      <div class="flex items-center gap-2">
        <div class="w-3 h-3 rounded-full" :style="{ background: categoryColor[skill.category] }" />
        <span class="text-sm font-semibold text-gray-200">{{ skill.name }}</span>
      </div>
      <button class="text-gray-500 hover:text-gray-300 text-lg leading-none cursor-pointer" @click="emit('close')">x</button>
    </div>

    <div class="flex-1 overflow-y-auto p-4 space-y-4">
      <!-- Level -->
      <div class="bg-surface-2 rounded-xl p-4 text-center">
        <div class="text-3xl font-bold" :style="{ color: categoryColor[skill.category] }">Lv.{{ skill.level }}</div>
        <div class="text-xs text-gray-400 mt-1">{{ levelDesc }}</div>
        <div class="mt-3 h-2 bg-surface-3 rounded-full overflow-hidden">
          <div class="h-full rounded-full transition-all" :style="{ width: `${skill.level}%`, background: categoryColor[skill.category] }" />
        </div>
      </div>

      <!-- Stats -->
      <div class="grid grid-cols-2 gap-3">
        <div class="bg-surface-2 rounded-lg p-3">
          <div class="text-xs text-gray-500">总使用次数</div>
          <div class="text-lg font-bold text-gray-200 mt-1">{{ skill.total_uses }}</div>
        </div>
        <div class="bg-surface-2 rounded-lg p-3">
          <div class="text-xs text-gray-500">类别</div>
          <div class="text-sm text-gray-300 mt-1">{{ categoryLabel[skill.category] }}</div>
        </div>
        <div class="bg-surface-2 rounded-lg p-3">
          <div class="text-xs text-gray-500">最近使用</div>
          <div class="text-xs text-gray-300 mt-1">{{ lastUsedText }}</div>
        </div>
        <div class="bg-surface-2 rounded-lg p-3">
          <div class="text-xs text-gray-500">首次发现</div>
          <div class="text-xs text-gray-300 mt-1">{{ formatDate(skill.first_seen) }}</div>
        </div>
      </div>

      <!-- OpenClaw badge -->
      <div v-if="skill.category === 'openclaw'" class="bg-openclaw/10 border border-openclaw/20 rounded-xl p-3">
        <div class="text-xs text-openclaw font-medium">OpenClaw 追踪技能</div>
        <div class="text-xs text-gray-400 mt-1">该技能主要通过 OpenClaw AI 辅助交互发展而来。</div>
      </div>
    </div>
  </div>
</template>

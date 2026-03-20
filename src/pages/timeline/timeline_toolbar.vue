<script setup lang="ts">
import { useEventsStore } from '@/stores/events'

const store = useEventsStore()

const sources = ['', 'openclaw', 'terminal', 'git', 'claude_code', 'codex', 'env']
const sourceLabels: Record<string, string> = {
  '': '全部来源',
  openclaw: 'OpenClaw',
  terminal: '终端',
  git: 'Git',
  claude_code: 'Claude Code',
  codex: 'Codex',
  env: '环境',
}

const timeRanges = [
  { value: 'today' as const, label: '今天' },
  { value: 'week' as const, label: '本周' },
  { value: 'month' as const, label: '本月' },
  { value: 'all' as const, label: '全部' },
]
</script>

<template>
  <div class="px-6 py-3 flex items-center gap-3 border-b border-surface-3">
    <!-- Source filter -->
    <select
      v-model="store.sourceFilter"
      class="bg-surface-2 border border-surface-3 rounded-lg px-3 py-1.5 text-xs text-gray-300 outline-none focus:border-accent"
    >
      <option v-for="s in sources" :key="s" :value="s">{{ sourceLabels[s] }}</option>
    </select>

    <!-- Project filter -->
    <select
      v-model="store.projectFilter"
      class="bg-surface-2 border border-surface-3 rounded-lg px-3 py-1.5 text-xs text-gray-300 outline-none focus:border-accent"
    >
      <option value="">全部项目</option>
      <option v-for="p in store.projects" :key="p" :value="p">{{ p }}</option>
    </select>

    <!-- Time range -->
    <div class="flex items-center bg-surface-2 rounded-lg border border-surface-3 overflow-hidden">
      <button
        v-for="r in timeRanges"
        :key="r.value"
        @click="store.timeRange = r.value"
        class="px-2.5 py-1.5 text-xs transition-colors"
        :class="store.timeRange === r.value ? 'bg-accent text-white' : 'text-gray-400 hover:text-white'"
      >
        {{ r.label }}
      </button>
    </div>

    <!-- Search -->
    <input
      v-model="store.searchQuery"
      type="text"
      placeholder="搜索事件..."
      class="bg-surface-2 border border-surface-3 rounded-lg px-3 py-1.5 text-xs text-gray-300 outline-none focus:border-accent flex-1 max-w-xs"
    />

    <!-- Count -->
    <div class="text-xs text-gray-500 ml-auto">
      {{ store.filteredEvents.length }} 个事件
    </div>
  </div>
</template>

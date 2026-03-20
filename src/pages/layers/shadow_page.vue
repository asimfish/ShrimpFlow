<script setup lang="ts">
import { computed, ref } from 'vue'

import { useEventsStore } from '@/stores/events'

const eventsStore = useEventsStore()

const sourceNames: Record<string, string> = {
  openclaw: 'OpenClaw',
  terminal: '终端',
  git: 'Git',
  claude_code: 'Claude Code',
  codex: 'Codex',
  cursor: 'Cursor',
  vscode: 'VS Code',
  env: '环境',
}

const sourceColors: Record<string, string> = {
  openclaw: '#22d3ee',
  terminal: '#a78bfa',
  git: '#f97316',
  claude_code: '#818cf8',
  codex: '#67e8f9',
  cursor: '#34d399',
  vscode: '#38bdf8',
  env: '#6b7280',
}

const sourceBgClass: Record<string, string> = {
  openclaw: 'bg-[#22d3ee]',
  terminal: 'bg-[#a78bfa]',
  git: 'bg-[#f97316]',
  claude_code: 'bg-[#818cf8]',
  codex: 'bg-[#67e8f9]',
  cursor: 'bg-[#34d399]',
  vscode: 'bg-[#38bdf8]',
  env: 'bg-[#6b7280]',
}

const sourceTextClass: Record<string, string> = {
  openclaw: 'text-[#22d3ee]',
  terminal: 'text-[#a78bfa]',
  git: 'text-[#f97316]',
  claude_code: 'text-[#818cf8]',
  codex: 'text-[#67e8f9]',
  cursor: 'text-[#34d399]',
  vscode: 'text-[#38bdf8]',
  env: 'text-[#6b7280]',
}

const sources = ['openclaw', 'terminal', 'git', 'claude_code', 'codex', 'cursor', 'vscode', 'env'] as const

// 每个来源的事件统计
const sourceCounts = computed(() => {
  const counts: Record<string, number> = { openclaw: 0, terminal: 0, git: 0, claude_code: 0, codex: 0, cursor: 0, vscode: 0, env: 0 }
  for (const e of eventsStore.events) {
    counts[e.source]++
  }
  return counts
})

const totalEvents = computed(() => eventsStore.events.length)

// 每个来源最新事件
const latestBySource = computed(() => {
  const latest: Record<string, string> = {}
  for (const s of sources) {
    const events = eventsStore.events.filter(e => e.source === s)
    if (events.length > 0) {
      const sorted = [...events].sort((a, b) => b.timestamp - a.timestamp)
      latest[s] = formatTime(sorted[0].timestamp)
    }
  }
  return latest
})

// 最大来源数量(用于柱状图比例)
const maxSourceCount = computed(() => Math.max(...Object.values(sourceCounts.value), 1))

// 按项目分组事件
const projects = ['embodied-nav', 'grasp-policy', 'ros2-workspace', 'paper-reproduce', 'sim2real-transfer']
const expandedProjects = ref<Set<string>>(new Set())

const toggleProject = (project: string) => {
  if (expandedProjects.value.has(project)) {
    expandedProjects.value = new Set([...expandedProjects.value].filter(p => p !== project))
  } else {
    expandedProjects.value = new Set([...expandedProjects.value, project])
  }
}

const eventsByProject = computed(() => {
  const map: Record<string, typeof eventsStore.events> = {}
  for (const p of projects) {
    map[p] = eventsStore.events.filter(e => e.project === p).sort((a, b) => b.timestamp - a.timestamp)
  }
  return map
})

// 数据采集状态
const collectionStatus = computed(() =>
  sources.map(s => {
    const events = eventsStore.events.filter(e => e.source === s)
    const sorted = [...events].sort((a, b) => b.timestamp - a.timestamp)
    const lastSync = sorted.length > 0 ? sorted[0].timestamp : 0
    return {
      source: s,
      name: sourceNames[s],
      count: events.length,
      status: events.length > 0 ? '运行中' : '未连接',
      lastSync: lastSync > 0 ? formatDateTime(lastSync) : '--',
    }
  })
)

// CSS 饼图角度计算
const pieSegments = computed(() => {
  const total = totalEvents.value
  if (total === 0) return []
  let cumulative = 0
  return sources.map(s => {
    const count = sourceCounts.value[s]
    const start = cumulative
    const deg = (count / total) * 360
    cumulative += deg
    return { source: s, start, deg, color: sourceColors[s], percent: ((count / total) * 100).toFixed(1) }
  })
})

const pieGradient = computed(() => {
  const segments = pieSegments.value
  if (segments.length === 0) return 'conic-gradient(#242438 0deg 360deg)'
  const stops = segments.map(s => `${s.color} ${s.start}deg ${s.start + s.deg}deg`).join(', ')
  return `conic-gradient(${stops})`
})

const formatTime = (ts: number) => {
  const d = new Date(ts * 1000)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const formatDateTime = (ts: number) => {
  const d = new Date(ts * 1000)
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hour = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${month}-${day} ${hour}:${min}`
}
</script>

<template>
  <div class="p-6 space-y-6 overflow-y-auto h-full">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-semibold">Layer 1: Shadow</h1>
      <p class="text-sm text-gray-400 mt-1">全量记录开发行为</p>
    </div>

    <!-- 事件来源统计卡片 -->
    <div class="grid grid-cols-5 gap-4">
      <div
        v-for="s in sources"
        :key="s"
        class="bg-surface-1 rounded-xl p-4 border border-surface-3"
      >
        <div class="flex items-center gap-2 mb-3">
          <div class="w-2 h-2 rounded-full" :class="sourceBgClass[s]" />
          <div class="text-xs" :class="sourceTextClass[s]">{{ sourceNames[s] }}</div>
        </div>
        <div class="text-xl font-bold">{{ sourceCounts[s] }}</div>
        <div class="text-xs text-gray-500 mt-1">最新: {{ latestBySource[s] }}</div>
        <!-- 小柱状图 -->
        <div class="mt-3 h-1.5 bg-surface-3 rounded-full overflow-hidden">
          <div
            class="h-full rounded-full transition-all"
            :style="{ width: `${(sourceCounts[s] / maxSourceCount) * 100}%`, backgroundColor: sourceColors[s] }"
          />
        </div>
      </div>
    </div>

    <div class="grid grid-cols-3 gap-4">
      <!-- 事件分布饼图 -->
      <div class="bg-surface-1 rounded-xl p-4 border border-surface-3">
        <div class="text-sm font-medium mb-4">事件来源分布</div>
        <div class="flex items-center gap-6">
          <!-- CSS 饼图 -->
          <div
            class="w-32 h-32 rounded-full shrink-0"
            :style="{ background: pieGradient }"
          />
          <!-- 图例 -->
          <div class="space-y-2 min-w-0">
            <div v-for="seg in pieSegments" :key="seg.source" class="flex items-center gap-2">
              <div class="w-2.5 h-2.5 rounded-sm shrink-0" :style="{ backgroundColor: seg.color }" />
              <span class="text-xs text-gray-300 truncate">{{ sourceNames[seg.source] }}</span>
              <span class="text-xs text-gray-500 ml-auto">{{ seg.percent }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 数据采集状态 -->
      <div class="col-span-2 bg-surface-1 rounded-xl p-4 border border-surface-3">
        <div class="text-sm font-medium mb-4">数据采集状态</div>
        <div class="space-y-3">
          <div
            v-for="item in collectionStatus"
            :key="item.source"
            class="flex items-center gap-4 bg-surface-2 rounded-lg px-4 py-3"
          >
            <div class="w-2 h-2 rounded-full shrink-0" :style="{ backgroundColor: sourceColors[item.source] }" />
            <div class="w-24 text-xs font-medium" :style="{ color: sourceColors[item.source] }">{{ item.name }}</div>
            <div class="flex items-center gap-1.5">
              <div
                class="w-1.5 h-1.5 rounded-full"
                :class="item.status === '运行中' ? 'bg-emerald-400' : 'bg-gray-500'"
              />
              <span class="text-xs" :class="item.status === '运行中' ? 'text-emerald-400' : 'text-gray-500'">{{ item.status }}</span>
            </div>
            <div class="text-xs text-gray-500 ml-auto">{{ item.count }} 条记录</div>
            <div class="text-xs text-gray-500">同步: {{ item.lastSync }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 按项目分组的事件列表 -->
    <div class="bg-surface-1 rounded-xl p-4 border border-surface-3">
      <div class="text-sm font-medium mb-4">按项目分组事件</div>
      <div class="space-y-2">
        <div v-for="project in projects" :key="project">
          <!-- 项目标题行 -->
          <div
            class="flex items-center gap-3 bg-surface-2 rounded-lg px-4 py-3 cursor-pointer hover:bg-surface-3/50 transition-colors"
            @click="toggleProject(project)"
          >
            <svg
              class="w-3 h-3 text-gray-400 transition-transform"
              :class="expandedProjects.has(project) ? 'rotate-90' : ''"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M8 5l8 7-8 7z" />
            </svg>
            <span class="text-xs font-mono text-gray-200">{{ project }}</span>
            <span class="text-xs text-gray-500 ml-auto">{{ eventsByProject[project]?.length }} 条事件</span>
          </div>
          <!-- 展开的事件列表 -->
          <div v-if="expandedProjects.has(project)" class="ml-6 mt-1 space-y-1">
            <div
              v-for="event in eventsByProject[project]?.slice(0, 20)"
              :key="event.id"
              class="flex items-start gap-2 px-3 py-2 rounded-lg bg-surface-3/30"
            >
              <div class="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" :style="{ backgroundColor: sourceColors[event.source] }" />
              <div class="min-w-0 flex-1">
                <div class="text-xs font-mono truncate text-gray-300">{{ event.action }}</div>
                <div class="text-[10px] text-gray-500">{{ sourceNames[event.source] }} · {{ formatTime(event.timestamp) }}</div>
              </div>
            </div>
            <div v-if="(eventsByProject[project]?.length ?? 0) > 20" class="text-[10px] text-gray-500 px-3 py-1">
              ... 还有 {{ (eventsByProject[project]?.length ?? 0) - 20 }} 条事件
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

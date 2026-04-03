<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { useEventsStore } from '@/stores/events'

const route = useRoute()
const eventsStore = useEventsStore()

const navItems = [
  { path: '/dashboard', label: '总览', icon: 'grid' },
  { path: '/profile', label: '我的画像', icon: 'user' },
  { path: '/openclaw', label: 'OpenClaw', icon: 'message' },
  { path: '/timeline', label: '时间线', icon: 'clock' },
  { path: '/digest', label: '报告', icon: 'calendar' },
  { path: '/skills', label: '技能图谱', icon: 'zap' },
  { path: '/twin', label: 'My AI Twin', icon: 'twin' },
  { path: '/patterns', label: '行为模式', icon: 'brain' },
  { path: '/memory', label: '记忆系统', icon: 'database' },
  { path: '/community', label: '社区', icon: 'globe' },
  { path: '/architecture', label: '架构', icon: 'layers' },
]

const isActive = (path: string) => route.path === path || route.path.startsWith(path + '/')

const sourceColorMap: Record<string, string> = {
  openclaw: 'text-openclaw',
  terminal: 'text-terminal',
  git: 'text-git',
  claude_code: 'text-claude',
  codex: 'text-cyan-300',
  cursor: 'text-emerald-400',
  vscode: 'text-sky-400',
  env: 'text-env',
}

const sourceLabelMap: Record<string, string> = {
  openclaw: 'OpenClaw',
  terminal: '终端',
  git: 'Git',
  claude_code: 'Claude',
  codex: 'Codex',
  cursor: 'Cursor',
  vscode: 'VS Code',
  env: '环境',
}

const liveEvents = computed(() =>
  eventsStore.liveEvents.map(event => ({
    id: event.id,
    color: sourceColorMap[event.source] ?? 'text-gray-300',
    text: `${sourceLabelMap[event.source] ?? event.source}: ${event.action}`,
  })),
)

const realtimeIndicatorClass = computed(() => {
  if (eventsStore.realtimeStatus === 'connected') return 'bg-emerald-400 animate-pulse'
  if (eventsStore.realtimeStatus === 'connecting') return 'bg-amber-400 animate-pulse'
  return 'bg-gray-500'
})

const realtimeLabel = computed(() => {
  if (eventsStore.realtimeStatus === 'connected') return '实时事件流'
  if (eventsStore.realtimeStatus === 'connecting') return '连接事件流中'
  if (eventsStore.realtimeStatus === 'disconnected') return '事件流已断开'
  return '等待事件流'
})
</script>

<template>
  <aside class="w-56 bg-surface-1 border-r border-surface-3/35 flex flex-col shrink-0">
    <!-- Logo -->
    <div class="px-5 pt-6 pb-5 border-b border-surface-3/35">
      <div class="flex items-center gap-2.5">
        <div class="w-8 h-8 relative">
          <svg viewBox="0 0 32 32" class="w-full h-full">
            <circle cx="13" cy="16" r="9" fill="none" stroke="#7c5cfc" stroke-width="1.5" opacity="0.6" class="logo-orbit-1" />
            <circle cx="19" cy="16" r="9" fill="none" stroke="#f59e0b" stroke-width="1.5" opacity="0.6" class="logo-orbit-2" />
            <circle cx="16" cy="16" r="4" fill="#7c5cfc" opacity="0.9" class="logo-core" />
          </svg>
        </div>
        <div>
          <div class="font-semibold text-sm">ShrimpFlow</div>
          <div class="text-[11px] text-openclaw">Powered by OpenClaw</div>
        </div>
      </div>
    </div>

    <!-- Nav -->
    <nav class="flex-1 p-3 space-y-1">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="flex items-center gap-3 pl-[10px] pr-3 py-2 rounded-md text-sm transition-colors duration-150 border-l-2 border-l-transparent"
        :class="
          isActive(item.path)
            ? 'border-l-accent bg-accent/[0.07] text-gray-100'
            : 'text-gray-400 hover:text-gray-200 hover:bg-white/[0.035]'
        "
      >
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <template v-if="item.icon === 'grid'">
            <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" />
          </template>
          <template v-if="item.icon === 'clock'">
            <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
          </template>
          <template v-if="item.icon === 'calendar'">
            <rect x="3" y="4" width="18" height="18" rx="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
          </template>
          <template v-if="item.icon === 'zap'">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
          </template>
          <template v-if="item.icon === 'message'">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </template>
          <template v-if="item.icon === 'brain'">
            <path d="M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-2.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7z" />
            <line x1="9" y1="21" x2="15" y2="21" />
          </template>
          <template v-if="item.icon === 'globe'">
            <circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
          </template>
          <template v-if="item.icon === 'user'">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
          </template>
          <template v-if="item.icon === 'twin'">
            <circle cx="12" cy="8" r="4" /><path d="M20 21a8 8 0 1 0-16 0" /><circle cx="19" cy="8" r="2" opacity="0.6" /><line x1="19" y1="11" x2="19" y2="14" opacity="0.6" />
          </template>
          <template v-if="item.icon === 'database'">
            <ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4.03 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5" />
          </template>
          <template v-if="item.icon === 'layers'">
            <polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" />
          </template>
        </svg>
        {{ item.label }}
      </router-link>
    </nav>

    <!-- 实时事件流 -->
    <div class="border-t border-surface-3/35 p-3">
      <div class="flex items-center gap-1.5 mb-2">
        <div class="w-1.5 h-1.5 rounded-full" :class="realtimeIndicatorClass" />
        <span class="text-[10px] text-gray-500">{{ realtimeLabel }}</span>
      </div>
      <div class="space-y-1 overflow-hidden h-[72px]">
        <TransitionGroup name="event-slide">
          <div
            v-for="ev in liveEvents"
            :key="ev.id"
            class="text-[10px] font-mono truncate transition-all duration-300"
            :class="ev.color"
          >
            {{ ev.text }}
          </div>
        </TransitionGroup>
        <div v-if="liveEvents.length === 0" class="text-[10px] text-gray-600">
          暂无实时事件
        </div>
      </div>
      <div v-if="eventsStore.realtimeError" class="mt-2 text-[10px] text-amber-400/80">
        {{ eventsStore.realtimeError }}
      </div>
    </div>

    <!-- Footer -->
    <div class="p-3 border-t border-surface-3/35">
      <div class="flex items-center justify-between">
        <div class="text-[10px] text-gray-600">OpenClaw Hackathon</div>
        <kbd class="text-[9px] text-gray-600 bg-surface-3 px-1.5 py-0.5 rounded">Cmd+K</kbd>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.event-slide-enter-active { transition: all 0.3s ease; }
.event-slide-leave-active { transition: all 0.2s ease; position: absolute; }
.event-slide-enter-from { opacity: 0; transform: translateY(-8px); }
.event-slide-leave-to { opacity: 0; }

@keyframes orbit-spin-1 {
  0% { transform: rotate(0deg); transform-origin: 16px 16px; }
  100% { transform: rotate(360deg); transform-origin: 16px 16px; }
}
@keyframes orbit-spin-2 {
  0% { transform: rotate(0deg); transform-origin: 16px 16px; }
  100% { transform: rotate(-360deg); transform-origin: 16px 16px; }
}
@keyframes core-breathe {
  0%, 100% { r: 4; opacity: 0.9; }
  50% { r: 5; opacity: 1; }
}
.logo-orbit-1 { animation: orbit-spin-1 12s linear infinite; }
.logo-orbit-2 { animation: orbit-spin-2 15s linear infinite; }
.logo-core { animation: core-breathe 3s ease-in-out infinite; }
</style>

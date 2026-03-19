<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import type { DevEvent } from '@/types'
import { useOpenClawStore } from '@/stores/openclaw'
import { dayjs } from '@/libs/dayjs'

const props = defineProps<{
  event: DevEvent | null
}>()

const emit = defineEmits<{
  close: []
}>()

const router = useRouter()
const openclawStore = useOpenClawStore()

const goToSession = () => {
  if (props.event?.openclaw_session_id) {
    openclawStore.selectSession(props.event.openclaw_session_id)
    router.push('/openclaw')
  }
}
const sourceLabel: Record<string, string> = {
  openclaw: 'OpenClaw',
  terminal: '终端',
  git: 'Git',
  claude_code: 'Claude Code',
  env: '环境',
}

const sourceDot: Record<string, string> = {
  openclaw: 'bg-openclaw',
  terminal: 'bg-terminal',
  git: 'bg-git',
  claude_code: 'bg-claude',
  env: 'bg-env',
}

const sourceText: Record<string, string> = {
  openclaw: 'text-openclaw',
  terminal: 'text-terminal',
  git: 'text-git',
  claude_code: 'text-claude',
  env: 'text-env',
}

const formatTime = (ts: number) => dayjs(ts * 1000).format('YYYY-MM-DD HH:mm:ss')

const formatDuration = (ms: number) => {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}min`
}

const exitCodeClass = computed(() => {
  if (!props.event) return ''
  return props.event.exit_code === 0 ? 'text-success' : 'text-danger'
})
</script>

<template>
  <div
    v-if="event"
    class="w-80 shrink-0 bg-surface-1 border-l border-surface-3 flex flex-col overflow-hidden"
  >
    <div class="flex items-center justify-between px-4 py-3 border-b border-surface-3">
      <div class="flex items-center gap-2">
        <div class="w-2 h-2 rounded-full" :class="sourceDot[event.source]" />
        <span class="text-sm font-medium" :class="sourceText[event.source]">
          {{ sourceLabel[event.source] }}
        </span>
      </div>
      <button class="text-gray-500 hover:text-gray-300 text-lg leading-none cursor-pointer" @click="emit('close')">
        x
      </button>
    </div>

    <div class="flex-1 overflow-y-auto p-4 space-y-4">
      <div>
        <div class="text-xs text-gray-500 mb-1">操作</div>
        <div class="text-sm font-mono text-gray-200 bg-surface-2 rounded-lg p-3 break-all">{{ event.action }}</div>
      </div>

      <div>
        <div class="text-xs text-gray-500 mb-1">语义</div>
        <div class="text-sm text-gray-300">{{ event.semantic }}</div>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div class="bg-surface-2 rounded-lg p-3">
          <div class="text-xs text-gray-500">时间</div>
          <div class="text-xs text-gray-300 mt-1">{{ formatTime(event.timestamp) }}</div>
        </div>
        <div class="bg-surface-2 rounded-lg p-3">
          <div class="text-xs text-gray-500">耗时</div>
          <div class="text-xs text-gray-300 mt-1">{{ formatDuration(event.duration_ms) }}</div>
        </div>
        <div class="bg-surface-2 rounded-lg p-3">
          <div class="text-xs text-gray-500">退出码</div>
          <div class="text-xs mt-1" :class="exitCodeClass">{{ event.exit_code }}</div>
        </div>
        <div class="bg-surface-2 rounded-lg p-3">
          <div class="text-xs text-gray-500">项目</div>
          <div class="text-xs text-gray-300 mt-1">{{ event.project }}</div>
        </div>
      </div>

      <div class="bg-surface-2 rounded-lg p-3">
        <div class="text-xs text-gray-500 mb-1">目录</div>
        <div class="text-xs font-mono text-gray-300 break-all">{{ event.directory }}</div>
      </div>

      <div v-if="event.tags.length">
        <div class="text-xs text-gray-500 mb-2">标签</div>
        <div class="flex flex-wrap gap-1.5">
          <span v-for="tag in event.tags" :key="tag" class="text-[11px] px-2 py-0.5 rounded-full bg-surface-3 text-gray-400">
            {{ tag }}
          </span>
        </div>
      </div>

      <!-- OpenClaw 对话跳转 -->
      <div v-if="event.openclaw_session_id">
        <button
          class="w-full bg-openclaw/10 border border-openclaw/20 rounded-lg p-3 text-left hover:bg-openclaw/20 transition-colors cursor-pointer"
          @click="goToSession"
        >
          <div class="text-xs text-openclaw font-medium">查看 OpenClaw 对话</div>
          <div class="text-[10px] text-gray-400 mt-1">点击查看完整的 AI 交互记录</div>
        </button>
      </div>
    </div>
  </div>
</template>

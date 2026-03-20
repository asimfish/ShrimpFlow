<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'

import { useSkillsStore } from '@/stores/skills'
import { searchApi } from '@/http_api/search'

const router = useRouter()
const skillsStore = useSkillsStore()

const visible = ref(false)
const query = ref('')
const inputRef = ref<HTMLInputElement>()

type SearchResult = {
  type: 'event' | 'session' | 'skill' | 'pattern'
  label: string
  description: string
  color: string
  action: () => void
}

const results = ref<SearchResult[]>([])

watch(query, async (q) => {
  const trimmed = q.toLowerCase().trim()
  if (!trimmed) { results.value = []; return }

  const { data } = await searchApi(trimmed)
  if (!data) { results.value = []; return }

  const out: SearchResult[] = []

  for (const s of data.sessions) {
    out.push({
      type: 'session', label: s.title, description: `OpenClaw · ${s.category}`,
      color: 'text-openclaw',
      action: () => { router.push('/openclaw'); close() },
    })
    if (out.length >= 12) break
  }

  for (const p of data.patterns) {
    out.push({
      type: 'pattern', label: p.name, description: `置信度 ${p.confidence}%`,
      color: 'text-purple-400',
      action: () => { router.push(`/patterns/${p.id}`); close() },
    })
    if (out.length >= 12) break
  }

  for (const s of skillsStore.skills) {
    if (s.name.toLowerCase().includes(trimmed)) {
      out.push({
        type: 'skill', label: s.name, description: `Lv.${s.level}`,
        color: 'text-accent',
        action: () => { router.push('/skills'); close() },
      })
    }
    if (out.length >= 12) break
  }

  for (const e of data.events) {
    const sourceColors: Record<string, string> = { openclaw: 'text-openclaw', terminal: 'text-terminal', git: 'text-git', claude_code: 'text-claude', codex: 'text-cyan-300', env: 'text-env' }
    out.push({
      type: 'event', label: e.action.slice(0, 60), description: `${e.project} · ${e.source}`,
      color: sourceColors[e.source] ?? 'text-gray-400',
      action: () => { router.push('/timeline'); close() },
    })
    if (out.length >= 12) break
  }

  results.value = out.slice(0, 10)
})

const close = () => {
  visible.value = false
  query.value = ''
}

const open = () => {
  visible.value = true
  nextTick(() => inputRef.value?.focus())
}

const onKeydown = (e: KeyboardEvent) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    visible.value ? close() : open()
  }
  if (e.key === 'Escape' && visible.value) close()
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))

const typeIcon: Record<string, string> = {
  event: '>', session: 'OC', skill: '*', pattern: '~',
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]" @click.self="close">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="close" />
      <div class="relative w-[560px] bg-surface-1 border border-surface-3 rounded-2xl shadow-2xl overflow-hidden">
        <!-- 搜索输入 -->
        <div class="flex items-center gap-3 px-4 py-3 border-b border-surface-3">
          <svg class="w-4 h-4 text-gray-500 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            ref="inputRef"
            v-model="query"
            type="text"
            placeholder="搜索事件、会话、技能、模式..."
            class="flex-1 bg-transparent text-sm text-gray-200 outline-none placeholder-gray-600"
          />
          <kbd class="text-[10px] text-gray-600 bg-surface-3 px-1.5 py-0.5 rounded">ESC</kbd>
        </div>

        <!-- 结果列表 -->
        <div class="max-h-[360px] overflow-y-auto">
          <div v-if="query && results.length === 0" class="p-6 text-center text-sm text-gray-500">
            没有找到匹配的结果
          </div>
          <div v-if="!query" class="p-6 text-center text-sm text-gray-600">
            输入关键词搜索...
          </div>
          <button
            v-for="(r, i) in results"
            :key="i"
            class="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-surface-2 transition-colors text-left"
            @click="r.action()"
          >
            <span class="w-6 h-6 rounded-md bg-surface-3 flex items-center justify-center text-[10px] font-mono shrink-0" :class="r.color">
              {{ typeIcon[r.type] }}
            </span>
            <div class="min-w-0 flex-1">
              <div class="text-xs text-gray-200 truncate">{{ r.label }}</div>
              <div class="text-[10px] text-gray-500">{{ r.description }}</div>
            </div>
            <span class="text-[10px] text-gray-600 shrink-0">{{ r.type === 'event' ? '事件' : r.type === 'session' ? '会话' : r.type === 'skill' ? '技能' : '模式' }}</span>
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

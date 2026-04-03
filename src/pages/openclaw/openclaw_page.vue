<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { useOpenClawStore } from '@/stores/openclaw'
import { dayjs } from '@/libs/dayjs'
import type { OpenClawInvocationLog } from '@/types'
import { getSessionInvocationsApi } from '@/http_api/openclaw'

const store = useOpenClawStore()

onMounted(async () => {
  await Promise.all([store.ensureSessionsLoaded(), store.ensureDocumentsLoaded()])
})

const categories = ['', 'paper', 'debug', 'review', 'experiment', 'architecture', 'learning']
const origins = ['all', 'openclaw', 'claude_code', 'codex', 'cursor', 'vscode'] as const
const categoryLabels: Record<string, string> = {
  '': '全部',
  paper: '论文分析',
  debug: '调试排查',
  review: '代码审查',
  experiment: '实验总结',
  architecture: '方案设计',
  learning: '学习探索',
}

const originLabels: Record<typeof origins[number], string> = {
  all: '全部来源',
  openclaw: 'OpenClaw',
  claude_code: 'Claude Code',
  codex: 'Codex',
  cursor: 'Cursor',
  vscode: 'VS Code',
}

const originColors: Record<string, string> = {
  openclaw: 'bg-openclaw/20 text-openclaw',
  claude_code: 'bg-claude/20 text-claude',
  codex: 'bg-cyan-300/20 text-cyan-300',
  cursor: 'bg-emerald-500/20 text-emerald-400',
  vscode: 'bg-sky-500/20 text-sky-400',
  unknown: 'bg-surface-3 text-gray-400',
}

const categoryColors: Record<string, string> = {
  paper: 'bg-blue-500/20 text-blue-400',
  debug: 'bg-red-500/20 text-red-400',
  review: 'bg-openclaw/20 text-openclaw',
  experiment: 'bg-emerald-500/20 text-emerald-400',
  architecture: 'bg-purple-500/20 text-purple-400',
  learning: 'bg-cyan-500/20 text-cyan-400',
}

const docTypeLabels: Record<string, string> = {
  daily_task: '每日任务',
  paper_note: '论文笔记',
  experiment_log: '实验日志',
  meeting_note: '会议纪要',
  daily_summary: '每日总结',
  ai_tools_daily: 'AI 工具日报',
  ai_tools_weekly: 'AI 工具周报',
  ai_tools_index: 'AI 工具索引',
  github_daily: 'GitHub 日报',
  media_daily: '媒体日报',
  misc: '其他文档',
}

const docTypeColors: Record<string, string> = {
  daily_task: 'bg-accent/20 text-accent',
  paper_note: 'bg-blue-500/20 text-blue-400',
  experiment_log: 'bg-emerald-500/20 text-emerald-400',
  meeting_note: 'bg-openclaw/20 text-openclaw',
  daily_summary: 'bg-openclaw/20 text-openclaw',
  ai_tools_daily: 'bg-cyan-500/20 text-cyan-400',
  ai_tools_weekly: 'bg-cyan-500/20 text-cyan-400',
  ai_tools_index: 'bg-cyan-500/20 text-cyan-400',
  github_daily: 'bg-git/20 text-git',
  media_daily: 'bg-purple-500/20 text-purple-400',
  misc: 'bg-surface-3 text-gray-400',
}

const formatTime = (ts: number) => dayjs(ts * 1000).format('MM-DD HH:mm')
const analysisError = ref<string | null>(null)
const invocationLogs = ref<OpenClawInvocationLog[]>([])

const analyzeCurrentSession = async () => {
  analysisError.value = null
  const result = await store.analyzeSelectedSession()
  if (result && result.error) analysisError.value = result.error
  await loadInvocationLogs()
}

const loadInvocationLogs = async () => {
  if (!store.selectedSessionId) {
    invocationLogs.value = []
    return
  }
  const result = await getSessionInvocationsApi(store.selectedSessionId)
  invocationLogs.value = result.data ?? []
}

const selectedDocId = ref<number | null>(null)
const docSortBy = ref<'date' | 'type'>('date')

const selectedDocument = computed(() =>
  store.filteredDocuments.find(doc => doc.id === selectedDocId.value) ?? null
)

// 按日期分组，最新在前
const documentsByDate = computed(() => {
  const sorted = [...store.filteredDocuments].sort((a, b) => b.created_at - a.created_at)
  const groups: { date: string; docs: typeof sorted }[] = []
  const map = new Map<string, typeof sorted>()
  for (const doc of sorted) {
    const date = dayjs(doc.created_at * 1000).format('YYYY-MM-DD')
    if (!map.has(date)) map.set(date, [])
    map.get(date)!.push(doc)
  }
  for (const [date, docs] of map) groups.push({ date, docs })
  return groups
})

// 按类型分组
const documentsByType = computed(() => {
  const sorted = [...store.filteredDocuments].sort((a, b) => b.created_at - a.created_at)
  const groups: { type: string; label: string; docs: typeof sorted }[] = []
  const map = new Map<string, typeof sorted>()
  for (const doc of sorted) {
    if (!map.has(doc.type)) map.set(doc.type, [])
    map.get(doc.type)!.push(doc)
  }
  for (const [type, docs] of map) groups.push({ type, label: docTypeLabels[type] ?? type, docs })
  return groups
})

const filteredSessionIds = computed(() => store.filteredSessions.map(session => session.id))
const documentIds = computed(() => store.filteredDocuments.map(doc => doc.id))

const syncSelections = () => {
  if (store.activeTab === 'sessions') {
    if (filteredSessionIds.value.length === 0) {
      store.selectedSessionId = null
      return
    }

    if (!filteredSessionIds.value.includes(store.selectedSessionId ?? -1)) {
      store.selectSession(filteredSessionIds.value[0])
    }
    return
  }

  if (documentIds.value.length === 0) {
    selectedDocId.value = null
    return
  }

  if (!documentIds.value.includes(selectedDocId.value ?? -1)) {
    selectedDocId.value = documentIds.value[0]
  }
}

watch(
  () => [
    store.activeTab,
    store.categoryFilter,
    filteredSessionIds.value.join(','),
    documentIds.value.join(','),
    store.selectedSessionId,
    selectedDocId.value,
  ],
  syncSelections,
  { immediate: true },
)

watch(() => store.selectedSessionId, () => {
  void loadInvocationLogs()
}, { immediate: true })
</script>

<template>
  <div class="flex h-full">
    <!-- 左侧面板 -->
    <div class="w-80 shrink-0 bg-surface-1 border-r border-surface-3 flex flex-col">
      <!-- Tab 切换 -->
      <div class="flex border-b border-surface-3">
        <button
          class="flex-1 py-3 text-xs font-medium transition-colors"
          :class="store.activeTab === 'sessions' ? 'text-openclaw border-b-2 border-openclaw' : 'text-gray-500 hover:text-gray-300'"
          @click="store.activeTab = 'sessions'"
        >
          对话记录
        </button>
        <button
          class="flex-1 py-3 text-xs font-medium transition-colors"
          :class="store.activeTab === 'documents' ? 'text-openclaw border-b-2 border-openclaw' : 'text-gray-500 hover:text-gray-300'"
          @click="store.activeTab = 'documents'"
        >
          知识库
        </button>
      </div>

      <!-- 会话列表 -->
      <template v-if="store.activeTab === 'sessions'">
        <div class="px-3 py-2 border-b border-surface-3">
          <div class="text-[10px] uppercase tracking-[0.18em] text-gray-600 mb-2">来源</div>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="origin in origins"
              :key="origin"
              class="text-[10px] px-2.5 py-1 rounded-full transition-colors"
              :class="store.originFilter === origin ? 'bg-openclaw/20 text-openclaw' : 'bg-surface-2 text-gray-500 hover:text-gray-300'"
              @click="store.originFilter = origin"
            >
              {{ originLabels[origin] }}
            </button>
          </div>
        </div>

        <div class="px-3 py-2 flex flex-wrap gap-1.5 border-b border-surface-3">
          <button
            v-for="cat in categories"
            :key="cat"
            class="text-[10px] px-2 py-1 rounded-full transition-colors"
            :class="store.categoryFilter === cat ? 'bg-openclaw/20 text-openclaw' : 'bg-surface-2 text-gray-500 hover:text-gray-300'"
            @click="store.categoryFilter = cat"
          >
            {{ categoryLabels[cat] }}
          </button>
        </div>

        <!-- 列表 -->
        <div class="flex-1 overflow-y-auto">
          <button
            v-for="session in store.filteredSessions"
            :key="session.id"
            class="w-full text-left p-3 border-b border-surface-3/50 transition-colors"
            :class="store.selectedSessionId === session.id ? 'bg-surface-2' : 'hover:bg-surface-2/50'"
            @click="store.selectSession(session.id)"
          >
            <div class="flex items-center gap-2 mb-2">
              <span class="text-[10px] font-mono text-gray-500">{{ session.index_label ?? `S-${String(session.id).padStart(4, '0')}` }}</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded" :class="originColors[session.origin ?? 'unknown'] ?? originColors.unknown">
                {{ session.origin_label ?? originLabels[(session.origin ?? 'unknown') as keyof typeof originLabels] ?? '未知来源' }}
              </span>
              <span class="text-[10px] px-1.5 py-0.5 rounded" :class="categoryColors[session.category]">
                {{ categoryLabels[session.category] }}
              </span>
            </div>
            <div class="text-sm text-gray-100 leading-snug">{{ session.display_title ?? session.title }}</div>
            <div class="text-[11px] text-gray-500 line-clamp-2 mt-1">{{ session.display_summary ?? session.summary }}</div>
            <div class="flex items-center gap-2 mt-2">
              <span class="text-[10px] text-gray-500">{{ session.project }}</span>
              <span class="text-[10px] text-gray-600">{{ formatTime(session.created_at) }}</span>
            </div>
          </button>
          <div v-if="store.filteredSessions.length === 0" class="p-6 text-center text-xs text-gray-500">
            当前筛选下没有会话
          </div>
        </div>
      </template>

      <!-- 知识库文档列表 -->
      <template v-else>
        <div class="px-3 py-2 border-b border-surface-3 space-y-2">
          <div class="flex items-center gap-2">
            <select
              v-model="store.documentOriginFilter"
              class="flex-1 bg-surface-2 border border-surface-3 rounded-lg px-2 py-1.5 text-[11px] text-gray-300"
            >
              <option value="all">全部来源</option>
              <option value="openclaw">OpenClaw</option>
              <option value="claude_code">Claude Code</option>
              <option value="codex">Codex</option>
              <option value="cursor">Cursor</option>
              <option value="vscode">VS Code</option>
            </select>
            <select
              v-model="store.documentTypeFilter"
              class="flex-1 bg-surface-2 border border-surface-3 rounded-lg px-2 py-1.5 text-[11px] text-gray-300"
            >
              <option value="all">全部类型</option>
              <option v-for="(label, type) in docTypeLabels" :key="type" :value="type">{{ label }}</option>
            </select>
          </div>
          <div class="flex gap-1">
            <button
              class="flex-1 py-1 text-[11px] rounded-lg transition-colors"
              :class="docSortBy === 'date' ? 'bg-surface-3 text-gray-200' : 'text-gray-500 hover:text-gray-300'"
              @click="docSortBy = 'date'"
            >按日期</button>
            <button
              class="flex-1 py-1 text-[11px] rounded-lg transition-colors"
              :class="docSortBy === 'type' ? 'bg-surface-3 text-gray-200' : 'text-gray-500 hover:text-gray-300'"
              @click="docSortBy = 'type'"
            >按类型</button>
          </div>
        </div>
        <div class="flex-1 overflow-y-auto">
          <!-- 日期分组 -->
          <template v-if="docSortBy === 'date'">
            <div v-for="group in documentsByDate" :key="group.date">
              <div class="px-3 py-1.5 text-[10px] text-gray-600 bg-surface-2/50 sticky top-0 font-medium">{{ group.date }} · {{ group.docs.length }} 篇</div>
              <button
                v-for="doc in group.docs"
                :key="doc.id"
                class="w-full text-left px-3 py-2.5 border-b border-surface-3/50 transition-colors"
                :class="selectedDocId === doc.id ? 'bg-surface-2' : 'hover:bg-surface-2/50'"
                @click="selectedDocId = doc.id"
              >
                <div class="flex items-center gap-1.5 mb-1">
                  <span class="text-[10px] px-1.5 py-0.5 rounded" :class="originColors[doc.origin ?? 'unknown'] ?? originColors.unknown">
                    {{ doc.origin_label ?? originLabels[(doc.origin ?? 'unknown') as keyof typeof originLabels] ?? '未知' }}
                  </span>
                  <span class="text-[10px] px-1.5 py-0.5 rounded" :class="docTypeColors[doc.type]">{{ docTypeLabels[doc.type] }}</span>
                  <span class="text-[10px] text-gray-600 ml-auto">{{ formatTime(doc.created_at) }}</span>
                </div>
                <div class="text-xs text-gray-200 leading-snug">{{ doc.display_title ?? doc.title }}</div>
                <div class="text-[10px] text-gray-500 line-clamp-1 mt-0.5">{{ doc.preview_excerpt ?? doc.title }}</div>
              </button>
            </div>
            <div v-if="store.filteredDocuments.length === 0" class="p-6 text-center text-xs text-gray-500">当前筛选下没有文档</div>
          </template>
          <!-- 类型分组 -->
          <template v-else>
            <div v-for="group in documentsByType" :key="group.type">
              <div class="px-3 py-1.5 text-[10px] text-gray-600 bg-surface-2/50 sticky top-0 font-medium">{{ group.label }} · {{ group.docs.length }} 篇</div>
              <button
                v-for="doc in group.docs"
                :key="doc.id"
                class="w-full text-left px-3 py-2.5 border-b border-surface-3/50 transition-colors"
                :class="selectedDocId === doc.id ? 'bg-surface-2' : 'hover:bg-surface-2/50'"
                @click="selectedDocId = doc.id"
              >
                <div class="flex items-center gap-1.5 mb-1">
                  <span class="text-[10px] px-1.5 py-0.5 rounded" :class="originColors[doc.origin ?? 'unknown'] ?? originColors.unknown">
                    {{ doc.origin_label ?? originLabels[(doc.origin ?? 'unknown') as keyof typeof originLabels] ?? '未知' }}
                  </span>
                  <span class="text-[10px] text-gray-600 ml-auto">{{ formatTime(doc.created_at) }}</span>
                </div>
                <div class="text-xs text-gray-200 leading-snug">{{ doc.display_title ?? doc.title }}</div>
                <div class="text-[10px] text-gray-500 line-clamp-1 mt-0.5">{{ doc.preview_excerpt ?? doc.title }}</div>
              </button>
            </div>
            <div v-if="store.filteredDocuments.length === 0" class="p-6 text-center text-xs text-gray-500">当前筛选下没有文档</div>
          </template>
        </div>
      </template>
    </div>

    <!-- 右侧内容区 -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- 会话对话视图 -->
      <template v-if="store.activeTab === 'sessions' && store.selectedSession">
        <!-- 会话头部 -->
        <div class="p-4 border-b border-surface-3">
          <div class="flex items-center justify-between gap-3 mb-1">
            <div class="flex items-center gap-2">
              <span class="text-[10px] font-mono text-gray-500">{{ store.selectedSession.index_label ?? `S-${String(store.selectedSession.id).padStart(4, '0')}` }}</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded" :class="originColors[store.selectedSession.origin ?? 'unknown'] ?? originColors.unknown">
                {{ store.selectedSession.origin_label ?? originLabels[(store.selectedSession.origin ?? 'unknown') as keyof typeof originLabels] ?? '未知来源' }}
              </span>
              <span class="text-[10px] px-1.5 py-0.5 rounded" :class="categoryColors[store.selectedSession.category]">
                {{ categoryLabels[store.selectedSession.category] }}
              </span>
              <span class="text-xs text-gray-500">{{ store.selectedSession.project }}</span>
              <span v-if="store.selectedSession.analysis_status" class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400">
                {{ store.selectedSession.analysis_status }}
              </span>
            </div>
            <button
              class="px-2.5 py-1 rounded-lg text-[10px] font-medium"
              :class="store.analyzing ? 'bg-surface-3 text-gray-500' : 'bg-openclaw/15 text-openclaw hover:bg-openclaw/25'"
              :disabled="store.analyzing"
              @click="analyzeCurrentSession"
            >
              {{ store.analyzing ? '分析中...' : '按 Active Profile 分析' }}
            </button>
          </div>
          <h2 class="text-base font-medium text-gray-200">{{ store.selectedSession.display_title ?? store.selectedSession.title }}</h2>
          <p class="text-xs text-gray-500 mt-1">{{ store.selectedSession.display_summary ?? store.selectedSession.summary }}</p>
          <div class="flex flex-wrap gap-1 mt-2">
            <span v-for="tag in store.selectedSession.tags" :key="tag" class="text-[10px] px-1.5 py-0.5 rounded-full bg-surface-3 text-gray-400">
              {{ tag }}
            </span>
          </div>
          <div v-if="store.selectedSession.analysis_summary" class="mt-3 bg-surface-2 rounded-lg p-3">
            <div class="text-[10px] text-gray-500 mb-1">Active ClawProfile 分析</div>
            <div class="text-xs text-gray-300 leading-relaxed">{{ store.selectedSession.analysis_summary }}</div>
            <div v-if="store.selectedSession.injected_pattern_slugs?.length" class="flex flex-wrap gap-1.5 mt-2">
              <span
                v-for="slug in store.selectedSession.injected_pattern_slugs"
                :key="slug"
                class="text-[10px] px-2 py-0.5 rounded bg-accent/15 text-accent font-mono"
              >
                {{ slug }}
              </span>
            </div>
          </div>
          <div v-if="analysisError" class="mt-2 text-[11px] text-red-400">{{ analysisError }}</div>
          <div v-if="invocationLogs.length" class="mt-3 bg-surface-2 rounded-lg p-3">
            <div class="text-[10px] text-gray-500 mb-2">Invocation Log</div>
            <div class="space-y-2 max-h-32 overflow-y-auto">
              <div v-for="log in invocationLogs" :key="log.id" class="border border-surface-3 rounded-lg p-2">
                <div class="flex items-center justify-between gap-2">
                  <div class="text-[10px] text-gray-400">{{ log.provider || 'local' }} / {{ log.model || log.selector_type }}</div>
                  <div class="text-[10px] text-gray-500">{{ log.created_at ? formatTime(log.created_at) : '' }}</div>
                </div>
                <div class="text-[10px] text-gray-300 mt-1">{{ log.response_summary }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 对话消息 -->
        <div class="flex-1 overflow-y-auto p-4 space-y-4">
          <div
            v-for="(msg, idx) in store.selectedSession.messages"
            :key="idx"
            class="flex"
            :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[75%] rounded-xl px-4 py-3"
              :class="msg.role === 'user' ? 'bg-accent/20 text-gray-200' : 'bg-surface-2 text-gray-300 border border-surface-3'"
            >
              <!-- 角色标识 -->
              <div class="flex items-center gap-1.5 mb-2">
                <div
                  v-if="msg.role === 'assistant'"
                  class="w-4 h-4 rounded-full flex items-center justify-center"
                  :class="(store.selectedSession.origin ?? 'openclaw') === 'claude_code' ? 'bg-claude/30' : (store.selectedSession.origin ?? 'openclaw') === 'codex' ? 'bg-cyan-300/20' : (store.selectedSession.origin ?? 'openclaw') === 'cursor' ? 'bg-emerald-500/20' : (store.selectedSession.origin ?? 'openclaw') === 'vscode' ? 'bg-sky-500/20' : 'bg-openclaw/30'"
                >
                  <span class="text-[8px] font-bold" :class="(store.selectedSession.origin ?? 'openclaw') === 'claude_code' ? 'text-claude' : (store.selectedSession.origin ?? 'openclaw') === 'codex' ? 'text-cyan-300' : (store.selectedSession.origin ?? 'openclaw') === 'cursor' ? 'text-emerald-400' : (store.selectedSession.origin ?? 'openclaw') === 'vscode' ? 'text-sky-400' : 'text-openclaw'">
                    {{ (store.selectedSession.origin ?? 'openclaw') === 'claude_code' ? 'CC' : (store.selectedSession.origin ?? 'openclaw') === 'codex' ? 'CX' : (store.selectedSession.origin ?? 'openclaw') === 'cursor' ? 'CU' : (store.selectedSession.origin ?? 'openclaw') === 'vscode' ? 'VS' : 'OC' }}
                  </span>
                </div>
                <span class="text-[10px]" :class="msg.role === 'user' ? 'text-accent' : ((store.selectedSession.origin ?? 'openclaw') === 'claude_code' ? 'text-claude' : (store.selectedSession.origin ?? 'openclaw') === 'codex' ? 'text-cyan-300' : (store.selectedSession.origin ?? 'openclaw') === 'cursor' ? 'text-emerald-400' : (store.selectedSession.origin ?? 'openclaw') === 'vscode' ? 'text-sky-400' : 'text-openclaw')">
                  {{ msg.role === 'user' ? '你' : ((store.selectedSession.origin ?? 'openclaw') === 'claude_code' ? 'Claude Code' : (store.selectedSession.origin ?? 'openclaw') === 'codex' ? 'Codex' : (store.selectedSession.origin ?? 'openclaw') === 'cursor' ? 'Cursor' : (store.selectedSession.origin ?? 'openclaw') === 'vscode' ? 'VS Code' : 'OpenClaw') }}
                </span>
                <span class="text-[10px] text-gray-600">{{ formatTime(msg.timestamp) }}</span>
              </div>
              <!-- 消息内容 - 简单渲染 markdown -->
              <div class="text-xs leading-relaxed whitespace-pre-wrap">{{ msg.content }}</div>
            </div>
          </div>
        </div>
      </template>

      <!-- 知识库文档视图 -->
      <template v-else-if="store.activeTab === 'documents' && selectedDocument">
        <div class="flex-1 overflow-y-auto p-6">
          <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-[10px] font-mono text-gray-500">{{ selectedDocument.index_label ?? `K-${String(selectedDocument.id).padStart(4, '0')}` }}</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded" :class="originColors[selectedDocument.origin ?? 'unknown'] ?? originColors.unknown">
                {{ selectedDocument.origin_label ?? originLabels[(selectedDocument.origin ?? 'unknown') as keyof typeof originLabels] ?? '未知来源' }}
              </span>
              <span class="text-[10px] px-1.5 py-0.5 rounded" :class="docTypeColors[selectedDocument.type]">
                {{ docTypeLabels[selectedDocument.type] }}
              </span>
              <span class="text-[10px] text-gray-500">{{ formatTime(selectedDocument.created_at) }}</span>
            </div>
            <h3 class="text-sm font-medium text-gray-200 mb-2">{{ selectedDocument.display_title ?? selectedDocument.title }}</h3>
            <p class="text-[11px] text-gray-500 mb-3">{{ selectedDocument.preview_excerpt ?? selectedDocument.title }}</p>
            <div class="text-xs text-gray-400 leading-relaxed whitespace-pre-wrap">{{ selectedDocument.content }}</div>
            <div class="flex flex-wrap gap-1 mt-3">
              <span v-for="tag in selectedDocument.tags" :key="tag" class="text-[10px] px-1.5 py-0.5 rounded-full bg-surface-3 text-gray-500">
                {{ tag }}
              </span>
            </div>
          </div>
        </div>
      </template>

      <!-- 空状态 -->
      <template v-else>
        <div class="flex-1 flex items-center justify-center">
          <div class="text-center text-gray-500">
            <div class="text-3xl mb-2 opacity-30">&#128172;</div>
            <div class="text-sm">选择一个会话查看详情</div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

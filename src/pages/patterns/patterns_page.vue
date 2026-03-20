<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { usePatternsStore } from '@/stores/patterns'
import { exportPatternsApi, importPatternsApi } from '@/http_api/patterns'

const router = useRouter()
const store = usePatternsStore()
const expandedPatterns = ref<Set<number>>(new Set())
const selectedForExport = ref<Set<number>>(new Set())
const exportSuccess = ref(false)
const exportMsg = ref('')
const exportError = ref('')

const fileInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)
const importMsg = ref('')
const importError = ref('')

const categoryFilter = ref<'all' | 'git' | 'coding' | 'review' | 'devops' | 'collaboration'>('all')
const statusFilter = ref<'all' | 'learning' | 'confirmed' | 'exportable'>('all')
const sourceFilter = ref<'all' | 'auto' | 'manual' | 'imported' | 'forked'>('all')
const searchQuery = ref('')

const showWorkflowDemo = ref(false)

onMounted(async () => {
  await Promise.all([store.ensurePatternsLoaded(), store.ensureWorkflowsLoaded()])
})

const toggleExpand = (id: number) => {
  if (expandedPatterns.value.has(id)) expandedPatterns.value.delete(id)
  else expandedPatterns.value.add(id)
}

const toggleSelect = (id: number) => {
  const next = new Set(selectedForExport.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedForExport.value = next
}

const handleExport = async () => {
  const ids = [...selectedForExport.value]
  if (ids.length === 0) return
  exportError.value = ''
  const res = await exportPatternsApi(ids)
  if (res.data) {
    const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${res.data.profile.name || 'clawprofile'}-${Date.now()}.clawprofile.json`
    a.click()
    URL.revokeObjectURL(url)
    exportMsg.value = `已导出 ${res.data.patterns.length} 个模式和 ${res.data.workflows.length} 个工作流`
    exportSuccess.value = true
    setTimeout(() => { exportSuccess.value = false }, 3000)
  } else {
    exportError.value = res.error ?? 'ClawProfile 导出失败'
  }
}

const handleImportFile = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  importing.value = true
  importMsg.value = ''
  importError.value = ''
  const text = await file.text()
  const json = JSON.parse(text)
  const payload = Array.isArray(json)
    ? { patterns: json }
    : {
        profile: json.profile,
        patterns: json.patterns ?? [],
        workflows: json.workflows ?? [],
      }
  const res = await importPatternsApi(payload)
  importing.value = false
  if (res.data) {
    importMsg.value = `成功导入 ${res.data.imported} 个模式，${res.data.workflows} 个工作流`
    await Promise.all([store.fetchPatterns(undefined, true), store.fetchWorkflows(true)])
    setTimeout(() => { importMsg.value = '' }, 4000)
  } else {
    importError.value = res.error ?? 'ClawProfile 导入失败'
  }
  // 重置 input 以便重复导入同一文件
  if (fileInput.value) fileInput.value.value = ''
}

const handleDelete = async (id: number) => {
  await store.deletePattern(id)
  const next = new Set(selectedForExport.value)
  next.delete(id)
  selectedForExport.value = next
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

const statusColorMap: Record<string, string> = {
  learning: 'bg-yellow-500/20 text-yellow-400',
  confirmed: 'bg-blue-500/20 text-blue-400',
  exportable: 'bg-emerald-500/20 text-emerald-400',
  draft: 'bg-gray-500/20 text-gray-400',
  active: 'bg-accent/20 text-accent',
  distributed: 'bg-emerald-500/20 text-emerald-400',
}

const statusLabel: Record<string, string> = {
  learning: '学习中', confirmed: '已确认', exportable: '可导出',
  draft: '草稿', active: '已激活', distributed: '已下发',
}

const getPatternNames = (ids: number[]) =>
  ids.map(id => store.patterns.find(p => p.id === id)?.name).filter(Boolean)

const confidenceColor = (c: number) => {
  if (c >= 85) return 'bg-emerald-500'
  if (c >= 70) return 'bg-accent'
  if (c >= 50) return 'bg-openclaw'
  return 'bg-gray-500'
}

const confidenceLevelColor: Record<string, string> = {
  low: 'bg-red-500/20 text-red-400',
  medium: 'bg-yellow-500/20 text-yellow-400',
  high: 'bg-blue-500/20 text-blue-400',
  very_high: 'bg-emerald-500/20 text-emerald-400',
}

const confidenceLevelLabel: Record<string, string> = {
  low: '低', medium: '中', high: '高', very_high: '极高',
}

const sourceLabel: Record<string, string> = {
  auto: '自动挖掘',
  manual: '手工维护',
  imported: '社区导入',
  forked: '派生模式',
}

const filteredPatterns = computed(() =>
  store.patterns.filter(pattern => {
    if (categoryFilter.value !== 'all' && pattern.category !== categoryFilter.value) return false
    if (statusFilter.value !== 'all' && pattern.status !== statusFilter.value) return false
    if (sourceFilter.value !== 'all' && pattern.source !== sourceFilter.value) return false
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.toLowerCase()
      return (
        pattern.name.toLowerCase().includes(q)
        || pattern.description.toLowerCase().includes(q)
        || pattern.learned_from.toLowerCase().includes(q)
      )
    }
    return true
  })
)

const patternStats = computed(() => ({
  auto: store.patterns.filter(p => p.source === 'auto').length,
  imported: store.patterns.filter(p => p.source === 'imported').length,
  exportable: store.patterns.filter(p => p.status === 'exportable').length,
}))
</script>

<template>
  <div class="p-6 space-y-6 overflow-y-auto h-full">
    <div>
      <h1 class="text-2xl font-semibold">行为模式</h1>
      <p class="text-sm text-gray-400 mt-1">从你的开发行为中学习模式，下发为团队 Workflow</p>
    </div>

    <div class="grid grid-cols-4 gap-4">
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-4">
        <div class="text-[11px] text-gray-500">总模式数</div>
        <div class="text-2xl font-semibold text-gray-100 mt-1">{{ store.patterns.length }}</div>
      </div>
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-4">
        <div class="text-[11px] text-gray-500">自动挖掘</div>
        <div class="text-2xl font-semibold text-accent mt-1">{{ patternStats.auto }}</div>
      </div>
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-4">
        <div class="text-[11px] text-gray-500">社区导入</div>
        <div class="text-2xl font-semibold text-openclaw mt-1">{{ patternStats.imported }}</div>
      </div>
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-4">
        <div class="text-[11px] text-gray-500">可导出 ClawProfile</div>
        <div class="text-2xl font-semibold text-emerald-400 mt-1">{{ patternStats.exportable }}</div>
      </div>
    </div>

    <!-- 流程说明 -->
    <div class="bg-surface-1 rounded-xl border border-surface-3 p-4">
      <div class="flex items-center gap-8 justify-center text-sm">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center">
            <svg class="w-4 h-4 text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" /></svg>
          </div>
          <span class="text-gray-300">记录行为</span>
        </div>
        <svg class="w-5 h-5 text-gray-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center">
            <svg class="w-4 h-4 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-2.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7z" /></svg>
          </div>
          <span class="text-gray-300">学习模式</span>
        </div>
        <svg class="w-5 h-5 text-gray-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
            <svg class="w-4 h-4 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>
          </div>
          <span class="text-gray-300">导出 / 下发</span>
        </div>
      </div>
    </div>

    <div class="bg-surface-1 rounded-xl border border-surface-3 p-4 space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <div class="text-sm font-medium text-gray-200">ClawProfile 管理</div>
          <div class="text-xs text-gray-500 mt-1">导出选中的本地模式为完整 ClawProfile，或导入社区/本地 profile</div>
        </div>
        <div class="flex items-center gap-2">
          <button class="px-3 py-2 rounded-lg bg-surface-2 text-xs text-gray-300 hover:bg-surface-3" @click="fileInput?.click()">
            {{ importing ? '导入中...' : '导入 ClawProfile' }}
          </button>
          <button
            class="px-3 py-2 rounded-lg text-xs font-medium"
            :class="selectedForExport.size ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30' : 'bg-surface-2 text-gray-500 cursor-not-allowed'"
            :disabled="selectedForExport.size === 0"
            @click="handleExport"
          >
            导出 ClawProfile
          </button>
        </div>
      </div>
      <input ref="fileInput" type="file" accept=".json,.clawprofile" class="hidden" @change="handleImportFile" />
      <div v-if="importMsg" class="text-xs text-emerald-400">{{ importMsg }}</div>
      <div v-if="importError" class="text-xs text-red-400">{{ importError }}</div>
      <div v-if="exportSuccess" class="text-xs text-emerald-400">{{ exportMsg }}</div>
      <div v-if="exportError" class="text-xs text-red-400">{{ exportError }}</div>
    </div>

    <div class="bg-surface-1 rounded-xl border border-surface-3 p-4 space-y-3">
      <div class="flex items-center gap-3 flex-wrap">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索模式名、描述、来源..."
          class="flex-1 min-w-56 bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-sm text-gray-300 outline-none focus:border-accent"
        />
        <select v-model="categoryFilter" class="bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-sm text-gray-300">
          <option value="all">全部分类</option>
          <option value="git">Git 规范</option>
          <option value="coding">编码习惯</option>
          <option value="review">代码审查</option>
          <option value="devops">运维部署</option>
          <option value="collaboration">协作模式</option>
        </select>
        <select v-model="statusFilter" class="bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-sm text-gray-300">
          <option value="all">全部状态</option>
          <option value="learning">学习中</option>
          <option value="confirmed">已确认</option>
          <option value="exportable">可导出</option>
        </select>
        <select v-model="sourceFilter" class="bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-sm text-gray-300">
          <option value="all">全部来源</option>
          <option value="auto">自动挖掘</option>
          <option value="manual">手工维护</option>
          <option value="imported">社区导入</option>
          <option value="forked">派生模式</option>
        </select>
      </div>
      <div class="text-xs text-gray-500">当前显示 {{ filteredPatterns.length }} / {{ store.patterns.length }} 个模式</div>
    </div>

    <!-- 已学习的行为模式 -->
    <div>
      <div class="text-sm font-medium mb-3 text-gray-300">已学习的行为模式 ({{ filteredPatterns.length }})</div>
      <div class="grid grid-cols-2 gap-4">
        <div
          v-for="pattern in filteredPatterns"
          :key="pattern.id"
          class="bg-surface-1 rounded-xl border border-surface-3 p-4 space-y-3 cursor-pointer hover:border-accent/30 transition-colors"
          :class="pattern.id === 99 ? 'border-emerald-500/40 ring-1 ring-emerald-500/20' : ''"
          @click="pattern.id === 99 ? (showWorkflowDemo = true) : router.push(`/patterns/${pattern.id}`)"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-[11px] px-2 py-0.5 rounded border" :class="categoryColorMap[pattern.category]">{{ categoryLabel[pattern.category] }}</span>
              <span class="text-[10px] px-2 py-0.5 rounded" :class="statusColorMap[pattern.status]">
                <span v-if="pattern.status === 'learning'" class="inline-block w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse mr-1" />
                {{ statusLabel[pattern.status] }}
              </span>
              <span v-if="pattern.confidence_level" class="text-[10px] px-1.5 py-0.5 rounded" :class="confidenceLevelColor[pattern.confidence_level]">{{ confidenceLevelLabel[pattern.confidence_level] }}</span>
              <span v-if="pattern.source" class="text-[10px] px-1.5 py-0.5 rounded bg-surface-3 text-gray-500">{{ sourceLabel[pattern.source] ?? pattern.source }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[10px] text-gray-500">{{ pattern.evidence_count }} 条证据</span>
              <input
                v-if="pattern.status === 'exportable'"
                type="checkbox"
                :checked="selectedForExport.has(pattern.id)"
                class="w-3.5 h-3.5 rounded accent-emerald-500"
                @click.stop
                @change="toggleSelect(pattern.id)"
              />
            </div>
          </div>
          <div class="text-sm font-medium text-gray-200">{{ pattern.name }}</div>
          <div class="text-xs text-gray-400 leading-relaxed">{{ pattern.description }}</div>
          <div>
            <div class="flex items-center justify-between mb-1">
              <span class="text-[10px] text-gray-500">置信度</span>
              <span class="text-[10px] text-gray-400">{{ pattern.confidence }}%</span>
            </div>
            <div class="h-1.5 bg-surface-3 rounded-full overflow-hidden">
              <div class="h-full rounded-full transition-all" :class="confidenceColor(pattern.confidence)" :style="{ width: `${pattern.confidence}%` }" />
            </div>
          </div>
          <div class="bg-surface-2 rounded-lg p-2.5">
            <div class="text-[10px] text-gray-500 mb-1">可执行规则</div>
            <div class="text-xs text-gray-300 font-mono">{{ pattern.rule }}</div>
          </div>

          <!-- trigger 展示 -->
          <div v-if="pattern.trigger" class="bg-surface-2 rounded-lg p-2.5">
            <div class="text-[10px] text-gray-500 mb-1">触发条件</div>
            <template v-if="typeof pattern.trigger === 'object'">
              <div class="text-xs text-gray-300">{{ (pattern.trigger as any).when }}</div>
              <div v-if="(pattern.trigger as any).globs" class="flex flex-wrap gap-1 mt-1">
                <span v-for="g in (pattern.trigger as any).globs" :key="g" class="text-[10px] px-1.5 py-0.5 rounded bg-surface-3 text-gray-500 font-mono">{{ g }}</span>
              </div>
            </template>
            <div v-else class="text-xs text-gray-300">{{ pattern.trigger }}</div>
          </div>

          <!-- body 预览 -->
          <div v-if="pattern.body && expandedPatterns.has(pattern.id)" class="bg-surface-2 rounded-lg p-2.5">
            <div class="text-[10px] text-gray-500 mb-1">Prompt 正文</div>
            <div class="text-xs text-gray-400 whitespace-pre-wrap leading-relaxed max-h-32 overflow-y-auto">{{ pattern.body }}</div>
          </div>

          <!-- 学习过程折叠区 -->
          <button class="text-[10px] text-accent hover:text-accent-glow transition-colors" @click.stop="toggleExpand(pattern.id)">
            {{ expandedPatterns.has(pattern.id) ? '收起学习过程' : '查看学习过程' }}
          </button>
          <div v-if="expandedPatterns.has(pattern.id)" class="space-y-2 border-t border-surface-3 pt-3">
            <div class="text-[10px] text-gray-500 mb-2">置信度演化过程</div>
            <div v-for="(snap, idx) in pattern.evolution" :key="idx" class="flex items-center gap-2">
              <span class="text-[10px] text-gray-600 w-12 shrink-0">{{ snap.date }}</span>
              <div class="flex-1 h-1 bg-surface-3 rounded-full overflow-hidden">
                <div class="h-full rounded-full transition-all" :class="confidenceColor(snap.confidence)" :style="{ width: `${snap.confidence}%` }" />
              </div>
              <span class="text-[10px] text-gray-500 w-8 text-right">{{ snap.confidence }}%</span>
            </div>
            <div class="space-y-1.5 mt-2">
              <div v-for="(snap, idx) in pattern.evolution" :key="'desc-'+idx" class="flex items-start gap-2">
                <div class="w-1.5 h-1.5 rounded-full mt-1 shrink-0" :class="confidenceColor(snap.confidence)" />
                <div class="text-[10px] text-gray-400">
                  <span class="text-gray-500">{{ snap.date }}</span> {{ snap.event_description }}
                </div>
              </div>
            </div>
          </div>

          <div class="text-[10px] text-gray-500">数据来源: {{ pattern.learned_from }}</div>
          <button class="text-[10px] text-red-400 hover:text-red-300 transition-colors" @click.stop="handleDelete(pattern.id)">删除</button>
        </div>
      </div>
    </div>

    <!-- 团队 Workflow 下发 -->
    <div>
      <div class="text-sm font-medium mb-3 text-gray-300">团队 Workflow 下发</div>
      <div class="space-y-3">
        <div
          v-for="wf in store.workflows"
          :key="wf.id"
          class="bg-surface-1 rounded-xl border border-surface-3 p-4 cursor-pointer hover:border-accent/30 transition-colors"
          @click="router.push(`/workflows/${wf.id}`)"
        >
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium text-gray-200">{{ wf.name }}</span>
              <span class="text-[10px] px-2 py-0.5 rounded" :class="statusColorMap[wf.status]">{{ statusLabel[wf.status] }}</span>
            </div>
            <span class="text-xs text-gray-500">目标: {{ wf.target_team }}</span>
          </div>
          <div class="text-xs text-gray-400 mb-3">{{ wf.description }}</div>
          <div class="flex flex-wrap gap-1.5">
            <span v-for="name in getPatternNames(wf.patterns)" :key="name" class="text-[10px] px-2 py-0.5 rounded-full bg-surface-3 text-gray-400">
              {{ name }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Workflow 动画弹窗 -->
  <Teleport to="body">
    <div v-if="showWorkflowDemo" class="fixed inset-0 z-50 flex items-center justify-center bg-black/80" @click.self="showWorkflowDemo = false">
      <div class="relative w-[90vw] h-[85vh] rounded-xl overflow-hidden border border-surface-3 shadow-2xl">
        <button class="absolute top-3 right-3 z-10 w-8 h-8 rounded-full bg-surface-2/90 border border-surface-3 flex items-center justify-center text-gray-400 hover:text-white transition-colors" @click="showWorkflowDemo = false">
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
        </button>
        <iframe src="/devtwin_workflow.html" class="w-full h-full border-0" />
      </div>
    </div>
  </Teleport>
</template>

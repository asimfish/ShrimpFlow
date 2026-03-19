<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { usePatternsStore } from '@/stores/patterns'
import { exportPatternsApi } from '@/http_api/patterns'

const router = useRouter()
const store = usePatternsStore()
const expandedPatterns = ref<Set<number>>(new Set())
const selectedForExport = ref<Set<number>>(new Set())
const targetProject = ref('')
const exportSuccess = ref(false)
const exportMsg = ref('')

// id=99 是特殊的"代码开发与Git提交规范"模式，点击展示 workflow 动画
const showWorkflowDemo = ref(false)

onMounted(async () => {
  await Promise.all([store.fetchPatterns(), store.fetchWorkflows()])
})

const toggleExpand = (id: number) => {
  if (expandedPatterns.value.has(id)) expandedPatterns.value.delete(id)
  else expandedPatterns.value.add(id)
}

const toggleSelect = (id: number) => {
  if (selectedForExport.value.has(id)) selectedForExport.value.delete(id)
  else selectedForExport.value.add(id)
}

const handleExport = async () => {
  const ids = [...selectedForExport.value]
  const res = await exportPatternsApi(ids)
  if (res.data) {
    exportSuccess.value = true
    exportMsg.value = `${ids.length} 个模式已成功导出`
    setTimeout(() => { exportSuccess.value = false }, 3000)
  }
}

const handleDelete = async (id: number) => {
  await store.deletePattern(id)
  selectedForExport.value.delete(id)
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
</script>

<template>
  <div class="p-6 space-y-6 overflow-y-auto h-full">
    <div>
      <h1 class="text-2xl font-semibold">行为模式</h1>
      <p class="text-sm text-gray-400 mt-1">从你的开发行为中学习模式，下发为团队 Workflow</p>
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

    <!-- 已学习的行为模式 -->
    <div>
      <div class="text-sm font-medium mb-3 text-gray-300">已学习的行为模式 ({{ store.patterns.length }})</div>
      <div class="grid grid-cols-2 gap-4">
        <div v-for="pattern in store.patterns" :key="pattern.id" class="bg-surface-1 rounded-xl border border-surface-3 p-4 space-y-3 cursor-pointer hover:border-accent/30 transition-colors" :class="pattern.id === 99 ? 'border-emerald-500/40 ring-1 ring-emerald-500/20' : ''" @click="pattern.id === 99 ? (showWorkflowDemo = true) : router.push(`/patterns/${pattern.id}`)">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-[11px] px-2 py-0.5 rounded border" :class="categoryColorMap[pattern.category]">{{ categoryLabel[pattern.category] }}</span>
              <span class="text-[10px] px-2 py-0.5 rounded" :class="statusColorMap[pattern.status]">
                <span v-if="pattern.status === 'learning'" class="inline-block w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse mr-1" />
                {{ statusLabel[pattern.status] }}
              </span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[10px] text-gray-500">{{ pattern.evidence_count }} 条证据</span>
              <input
                v-if="pattern.status === 'exportable'"
                type="checkbox"
                :checked="selectedForExport.has(pattern.id)"
                class="w-3.5 h-3.5 rounded accent-emerald-500"
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

          <!-- 学习过程折叠区 -->
          <button class="text-[10px] text-accent hover:text-accent-glow transition-colors" @click="toggleExpand(pattern.id)">
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

    <!-- 模式导入区域 -->
    <div class="bg-surface-1 rounded-xl border border-emerald-500/30 p-5">
      <div class="text-sm font-medium mb-3 text-emerald-400">导入模式到新项目</div>
      <div class="flex items-end gap-4">
        <div class="flex-1">
          <div class="text-[10px] text-gray-500 mb-1">目标项目</div>
          <input
            v-model="targetProject"
            type="text"
            placeholder="输入项目名称..."
            class="w-full bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-xs text-gray-300 outline-none focus:border-emerald-500"
          />
        </div>
        <div class="text-[10px] text-gray-500">
          已选择 {{ selectedForExport.size }} 个模式
        </div>
        <button
          class="px-4 py-2 rounded-lg text-xs font-medium transition-colors"
          :class="selectedForExport.size > 0 && targetProject ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 cursor-pointer' : 'bg-surface-3 text-gray-600 cursor-not-allowed'"
          :disabled="selectedForExport.size === 0 || !targetProject"
          @click="handleExport"
        >
          开始导入
        </button>
      </div>
      <div v-if="exportSuccess" class="mt-3 text-xs text-emerald-400 bg-emerald-500/10 rounded-lg p-2">
        {{ exportMsg }}
      </div>
    </div>

    <!-- 团队 Workflow 下发 -->
    <div>
      <div class="text-sm font-medium mb-3 text-gray-300">团队 Workflow 下发</div>
      <div class="space-y-3">
        <div v-for="wf in store.workflows" :key="wf.id" class="bg-surface-1 rounded-xl border border-surface-3 p-4 cursor-pointer hover:border-accent/30 transition-colors" @click="router.push(`/workflows/${wf.id}`)">
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

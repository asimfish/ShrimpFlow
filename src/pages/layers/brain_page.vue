<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import type { BehaviorPattern, Episode, EpisodeStats, ArchetypeSummary, FeatureGraphStats, EvidenceLedgerStats } from '@/types'

import { useEventsStore } from '@/stores/events'
import { usePatternsStore } from '@/stores/patterns'
import { mineAllPatterns } from '@/utils/pattern_mining'
import { getEpisodesApi, getEpisodeStatsApi, getArchetypesApi, getFeatureGraphStatsApi, getEvidenceLedgerStatsApi } from '@/http_api/episodes'
import { getAgentTasteApi, relearnAgentTasteApi, autoConfirmPatternsApi, getAutonomousSuggestionsApi } from '@/http_api/agent_taste'
import type { TasteProfile, AutoConfirmResult, AutonomousTaskSuggestion } from '@/http_api/agent_taste'
import { dayjs } from '@/libs/dayjs'
import { generateClawsApi, getCotProfileApi, exportMarkdownApi } from '@/http_api/claw_gen'
import type { ClawGenResult, CotProfile } from '@/http_api/claw_gen'

const router = useRouter()
const eventsStore = useEventsStore()
const patternsStore = usePatternsStore()

const episodes = ref<Episode[]>([])
const episodeStats = ref<EpisodeStats | null>(null)
const archetypes = ref<ArchetypeSummary[]>([])
const graphStats = ref<FeatureGraphStats | null>(null)
const ledgerStats = ref<EvidenceLedgerStats | null>(null)
const showEpisodes = ref(true)
const showGraph = ref(true)
const showLedger = ref(true)

// Taste Agent
const tasteProfile = ref<TasteProfile | null>(null)
const tasteLoading = ref(false)
const tasteError = ref('')
const autoConfirmResult = ref<AutoConfirmResult | null>(null)
const autoConfirming = ref(false)
const relearning = ref(false)
const autonomousSuggestions = ref<AutonomousTaskSuggestion[]>([])

const loadTasteProfile = async () => {
  tasteLoading.value = true
  tasteError.value = ''
  const res = await getAgentTasteApi()
  tasteLoading.value = false
  if (res.data) tasteProfile.value = res.data
  else tasteError.value = res.error ?? '加载失败'
}

const handleRelearn = async () => {
  relearning.value = true
  const res = await relearnAgentTasteApi()
  relearning.value = false
  if (res.data) tasteProfile.value = res.data
}

const handleAutoConfirm = async () => {
  autoConfirming.value = true
  autoConfirmResult.value = null
  const res = await autoConfirmPatternsApi()
  autoConfirming.value = false
  if (res.data) {
    autoConfirmResult.value = res.data
    await loadTasteProfile()
    await patternsStore.fetchPatterns(undefined, true)
  }
}

onMounted(async () => {
  await Promise.all([eventsStore.ensureLoaded(), patternsStore.ensurePatternsLoaded()])
  const [epRes, statsRes, archRes, graphRes, ledgerRes] = await Promise.all([
    getEpisodesApi(30),
    getEpisodeStatsApi(),
    getArchetypesApi(),
    getFeatureGraphStatsApi(),
    getEvidenceLedgerStatsApi(),
  ])
  if (epRes.data) episodes.value = epRes.data
  if (statsRes.data) episodeStats.value = statsRes.data
  if (archRes.data) archetypes.value = archRes.data
  if (graphRes.data) graphStats.value = graphRes.data
  if (ledgerRes.data) ledgerStats.value = ledgerRes.data
  void loadTasteProfile()
  void loadCotProfile()
  getAutonomousSuggestionsApi().then(res => {
    if (res.data?.suggestions) autonomousSuggestions.value = res.data.suggestions
  })
})

// 运行挖掘算法
const minedPatterns = computed(() => mineAllPatterns(eventsStore.events))
const showMining = ref(true)

const categoryColorMap: Record<string, string> = {
  git: 'bg-git/20 text-git',
  coding: 'bg-accent/20 text-accent',
  review: 'bg-openclaw/20 text-openclaw',
  devops: 'bg-terminal/20 text-terminal',
  collaboration: 'bg-purple-500/20 text-purple-400',
}

const categoryLabel: Record<string, string> = {
  git: 'Git 规范',
  coding: '编码习惯',
  review: '代码审查',
  devops: '运维部署',
  collaboration: '协作模式',
}

const statusLabel: Record<string, string> = {
  learning: '学习中',
  confirmed: '已确认',
  exportable: '可导出',
}

const confidenceColor = (c: number) => {
  if (c >= 85) return 'bg-emerald-500'
  if (c >= 70) return 'bg-accent'
  if (c >= 50) return 'bg-openclaw'
  return 'bg-gray-500'
}

const learningPatterns = computed(() =>
  patternsStore.patterns.filter((p: BehaviorPattern) => p.status === 'learning')
)

const confirmedPatterns = computed(() =>
  patternsStore.patterns.filter((p: BehaviorPattern) => p.status === 'confirmed')
)

const exportablePatterns = computed(() =>
  patternsStore.patterns.filter((p: BehaviorPattern) => p.status === 'exportable')
)

const handleClickPattern = (pattern: BehaviorPattern) => {
  router.push(`/patterns/${pattern.id}`)
}

const outcomeClass = (outcome: string) => {
  if (outcome === 'success') return 'bg-emerald-500/15 text-emerald-400'
  if (outcome === 'failure') return 'bg-red-500/15 text-red-400'
  return 'bg-gray-500/15 text-gray-400'
}

const outcomeLabel = (outcome: string) => {
  if (outcome === 'success') return '成功'
  if (outcome === 'failure') return '失败'
  return '未知'
}

const formatDuration = (seconds: number) => {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  return `${(seconds / 3600).toFixed(1)}h`
}

const archetypeLabelMap: Record<string, string> = {
  'debug-fix-commit': '调试-修复-提交',
  'test-driven-dev': '测试驱动开发',
  'ai-assisted-coding': 'AI辅助编码',
  'deploy-ops': '部署运维',
  'code-review': '代码审查',
  'learning-exploration': '学习探索',
  'rapid-iteration': '快速迭代',
  'general': '通用',
}

const archetypeLabel = (key: string) => archetypeLabelMap[key] ?? key

const archetypeColorMap: Record<string, string> = {
  'debug-fix-commit': 'text-red-400',
  'test-driven-dev': 'text-emerald-400',
  'ai-assisted-coding': 'text-cyan-400',
  'deploy-ops': 'text-orange-400',
  'code-review': 'text-blue-400',
  'learning-exploration': 'text-purple-400',
  'rapid-iteration': 'text-yellow-400',
  'general': 'text-gray-400',
}

const archetypeColor = (key: string) => archetypeColorMap[key] ?? 'text-gray-400'

const evidenceTypeColor = (type: string) => {
  if (type === 'support') return 'bg-emerald-400'
  if (type === 'conflict') return 'bg-red-400'
  if (type === 'novelty') return 'bg-blue-400'
  if (type === 'utility') return 'bg-amber-400'
  return 'bg-gray-400'
}

const evidenceTypeLabel = (type: string) => {
  if (type === 'support') return '支持'
  if (type === 'conflict') return '冲突'
  if (type === 'novelty') return '新颖'
  if (type === 'utility') return '实用'
  return type
}

// Claw Generator (M1+M2+M3)
const cotProfile = ref<CotProfile | null>(null)
const clawGenResult = ref<ClawGenResult | null>(null)
const clawGenerating = ref(false)
const markdownExport = ref('')
const showMarkdown = ref(false)

const loadCotProfile = async () => {
  const res = await getCotProfileApi()
  if (res.data) cotProfile.value = res.data
}

const handleGenerateClaw = async () => {
  clawGenerating.value = true
  clawGenResult.value = null
  const res = await generateClawsApi()
  clawGenerating.value = false
  if (res.data) {
    clawGenResult.value = res.data
    await patternsStore.fetchPatterns(undefined, true)
  }
}

const handleExportMarkdown = async () => {
  const res = await exportMarkdownApi()
  if (res.data) {
    markdownExport.value = res.data.markdown
    showMarkdown.value = true
  }
}

const copyMarkdownToClipboard = () => {
  if (typeof navigator !== 'undefined') {
    void navigator.clipboard.writeText(markdownExport.value)
  }
}
</script>

<template>
  <div class="p-6 space-y-6 overflow-y-auto h-full">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-semibold">Layer 3: Brain</h1>
      <p class="text-sm text-gray-400 mt-1">从开发行为中自动学习模式 · 已分析 {{ eventsStore.events.length }} 个事件</p>
    </div>

    <!-- Episode 统计概览 -->
    <div v-if="episodeStats">
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <span class="inline-block w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
          <span class="text-sm font-medium text-violet-400">Episode 任务片段 ({{ episodeStats.total_episodes }})</span>
        </div>
        <button @click="showEpisodes = !showEpisodes" class="text-[10px] text-gray-500 hover:text-gray-300 transition-colors">
          {{ showEpisodes ? '收起' : '展开' }}
        </button>
      </div>

      <!-- 统计卡片 -->
      <div class="grid grid-cols-4 gap-3 mb-4">
        <div class="bg-surface-1 rounded-lg border border-surface-3 p-3 text-center">
          <div class="text-lg font-semibold text-violet-400">{{ episodeStats.total_episodes }}</div>
          <div class="text-[10px] text-gray-500">任务片段</div>
        </div>
        <div class="bg-surface-1 rounded-lg border border-surface-3 p-3 text-center">
          <div class="text-lg font-semibold text-cyan-400">{{ episodeStats.total_atoms }}</div>
          <div class="text-[10px] text-gray-500">行为原子</div>
        </div>
        <div class="bg-surface-1 rounded-lg border border-surface-3 p-3 text-center">
          <div class="text-lg font-semibold text-emerald-400">{{ episodeStats.by_outcome?.success ?? 0 }}</div>
          <div class="text-[10px] text-gray-500">成功任务</div>
        </div>
        <div class="bg-surface-1 rounded-lg border border-surface-3 p-3 text-center">
          <div class="text-lg font-semibold text-red-400">{{ episodeStats.by_outcome?.failure ?? 0 }}</div>
          <div class="text-[10px] text-gray-500">失败任务</div>
        </div>
      </div>

      <!-- 分类分布 -->
      <div v-if="Object.keys(episodeStats.by_category).length" class="flex flex-wrap gap-2 mb-4">
        <span
          v-for="(count, cat) in episodeStats.by_category" :key="cat"
          class="text-[10px] px-2 py-1 rounded-full bg-surface-2 text-gray-300"
        >
          {{ cat }}: {{ count }}
        </span>
      </div>

      <!-- Episode 列表 -->
      <div v-if="showEpisodes" class="space-y-2">
        <div
          v-for="ep in episodes.slice(0, 15)" :key="ep.id"
          class="bg-surface-1 rounded-lg border border-surface-3 p-3 hover:border-violet-500/30 transition-colors"
        >
          <div class="flex items-center justify-between mb-1.5">
            <div class="flex items-center gap-2">
              <span class="text-[10px] px-2 py-0.5 rounded-full" :class="outcomeClass(ep.outcome)">
                {{ outcomeLabel(ep.outcome) }}
              </span>
              <span class="text-[10px] px-2 py-0.5 rounded bg-violet-500/15 text-violet-400">{{ ep.task_category }}</span>
              <span v-if="ep.project" class="text-[10px] text-gray-500">{{ ep.project }}</span>
            </div>
            <span class="text-[10px] text-gray-500">{{ formatDuration(ep.duration_seconds) }}</span>
          </div>
          <div class="text-xs text-gray-200 mb-1.5">{{ ep.task_label }}</div>
          <div class="flex items-center gap-1 flex-wrap">
            <span
              v-for="(tool, i) in ep.tool_sequence.slice(0, 8)" :key="i"
              class="text-[9px] px-1.5 py-0.5 rounded bg-surface-2 text-gray-400"
            >
              {{ tool }}
            </span>
            <span v-if="ep.tool_sequence.length > 8" class="text-[9px] text-gray-500">+{{ ep.tool_sequence.length - 8 }}</span>
          </div>
          <div class="text-[10px] text-gray-500 mt-1">
            {{ dayjs.unix(ep.start_ts).format('YYYY-MM-DD HH:mm') }} · {{ ep.event_count }} 个事件
          </div>
        </div>
        <div v-if="!episodes.length" class="text-center text-xs text-gray-500 py-6">
          暂无 Episode 数据，执行一键采集后自动生成
        </div>
      </div>
    </div>

    <!-- Feature Graph 行为原型图谱 -->
    <div v-if="graphStats">
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <span class="inline-block w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
          <span class="text-sm font-medium text-indigo-400">Feature Graph 行为原型 ({{ graphStats.total_nodes }} 节点 / {{ graphStats.total_edges }} 边)</span>
        </div>
        <button @click="showGraph = !showGraph" class="text-[10px] text-gray-500 hover:text-gray-300 transition-colors">
          {{ showGraph ? '收起' : '展开' }}
        </button>
      </div>

      <div v-if="showGraph" class="space-y-3">
        <!-- 图谱统计 -->
        <div class="grid grid-cols-4 gap-3">
          <div class="bg-surface-1 rounded-lg border border-surface-3 p-3 text-center">
            <div class="text-lg font-semibold text-indigo-400">{{ graphStats.total_nodes }}</div>
            <div class="text-[10px] text-gray-500">特征节点</div>
          </div>
          <div class="bg-surface-1 rounded-lg border border-surface-3 p-3 text-center">
            <div class="text-lg font-semibold text-blue-400">{{ graphStats.total_edges }}</div>
            <div class="text-[10px] text-gray-500">相似度边</div>
          </div>
          <div class="bg-surface-1 rounded-lg border border-surface-3 p-3 text-center">
            <div class="text-lg font-semibold text-purple-400">{{ Object.keys(graphStats.archetype_distribution).length }}</div>
            <div class="text-[10px] text-gray-500">行为原型</div>
          </div>
          <div class="bg-surface-1 rounded-lg border border-surface-3 p-3 text-center">
            <div class="text-lg font-semibold text-teal-400">{{ Object.keys(graphStats.edge_type_distribution).length }}</div>
            <div class="text-[10px] text-gray-500">边类型</div>
          </div>
        </div>

        <!-- 行为原型分布 -->
        <div class="bg-surface-1 rounded-xl border border-indigo-500/20 p-4">
          <div class="text-xs text-indigo-400 mb-3">行为原型分布</div>
          <div class="space-y-2">
            <div v-for="(count, archetype) in graphStats.archetype_distribution" :key="archetype"
              class="flex items-center gap-3"
            >
              <span class="text-xs text-gray-300 w-40 truncate">{{ archetypeLabel(archetype as string) }}</span>
              <div class="flex-1 h-2 bg-surface-3 rounded-full overflow-hidden">
                <div class="h-full bg-indigo-500 rounded-full" :style="{ width: `${(count / graphStats!.total_nodes) * 100}%` }" />
              </div>
              <span class="text-[10px] text-gray-500 w-8 text-right">{{ count }}</span>
            </div>
          </div>
        </div>

        <!-- 原型详情卡片 -->
        <div v-if="archetypes.length" class="grid grid-cols-2 gap-3">
          <div v-for="arch in archetypes.slice(0, 6)" :key="arch.archetype"
            class="bg-surface-1 rounded-lg border border-surface-3 p-3"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-medium" :class="archetypeColor(arch.archetype)">{{ archetypeLabel(arch.archetype) }}</span>
              <span class="text-[10px] text-gray-500">{{ arch.count }} 个 Episode</span>
            </div>
            <div v-if="arch.top_projects.length" class="flex flex-wrap gap-1 mb-1">
              <span v-for="proj in arch.top_projects" :key="proj" class="text-[9px] px-1.5 py-0.5 rounded bg-surface-2 text-gray-400">{{ proj }}</span>
            </div>
            <div v-if="arch.top_categories.length" class="flex flex-wrap gap-1">
              <span v-for="cat in arch.top_categories" :key="cat" class="text-[9px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400">{{ cat }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Evidence Ledger 证据账本 -->
    <div v-if="ledgerStats && ledgerStats.total > 0">
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <span class="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          <span class="text-sm font-medium text-amber-400">Evidence Ledger 证据账本 ({{ ledgerStats.total }} 条记录)</span>
        </div>
        <button @click="showLedger = !showLedger" class="text-[10px] text-gray-500 hover:text-gray-300 transition-colors">
          {{ showLedger ? '收起' : '展开' }}
        </button>
      </div>

      <div v-if="showLedger" class="space-y-3">
        <div class="grid grid-cols-4 gap-3">
          <div class="bg-surface-1 rounded-lg border border-surface-3 p-3 text-center">
            <div class="text-lg font-semibold text-emerald-400">{{ ledgerStats.by_type.support ?? 0 }}</div>
            <div class="text-[10px] text-gray-500">支持证据</div>
          </div>
          <div class="bg-surface-1 rounded-lg border border-surface-3 p-3 text-center">
            <div class="text-lg font-semibold text-red-400">{{ ledgerStats.by_type.conflict ?? 0 }}</div>
            <div class="text-[10px] text-gray-500">冲突证据</div>
          </div>
          <div class="bg-surface-1 rounded-lg border border-surface-3 p-3 text-center">
            <div class="text-lg font-semibold text-blue-400">{{ ledgerStats.by_type.novelty ?? 0 }}</div>
            <div class="text-[10px] text-gray-500">新颖证据</div>
          </div>
          <div class="bg-surface-1 rounded-lg border border-surface-3 p-3 text-center">
            <div class="text-lg font-semibold text-amber-400">{{ ledgerStats.by_type.utility ?? 0 }}</div>
            <div class="text-[10px] text-gray-500">实用证据</div>
          </div>
        </div>

        <div class="bg-surface-1 rounded-xl border border-amber-500/20 p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs text-amber-400">置信度变化趋势</span>
            <span class="text-[10px] text-gray-500">平均 delta: {{ ledgerStats.avg_delta > 0 ? '+' : '' }}{{ ledgerStats.avg_delta }}</span>
          </div>
          <div class="flex items-center gap-3">
            <div v-for="(count, etype) in ledgerStats.by_type" :key="etype" class="flex items-center gap-1.5">
              <span class="inline-block w-2 h-2 rounded-full" :class="evidenceTypeColor(etype as string)" />
              <span class="text-[10px] text-gray-400">{{ evidenceTypeLabel(etype as string) }}: {{ count }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 自动挖掘结果 -->
    <div>
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <span class="inline-block w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span class="text-sm font-medium text-cyan-400">自动挖掘结果 ({{ minedPatterns.length }})</span>
        </div>
        <button @click="showMining = !showMining" class="text-[10px] text-gray-500 hover:text-gray-300 transition-colors">
          {{ showMining ? '收起' : '展开' }}
        </button>
      </div>
      <div v-if="showMining" class="space-y-4">
        <!-- 频繁序列 -->
        <div class="bg-surface-1 rounded-xl border border-cyan-500/20 p-4">
          <div class="text-xs text-cyan-400 mb-3">频繁行为序列</div>
          <div class="space-y-2">
            <div v-for="p in minedPatterns.filter(p => p.type === 'sequence').slice(0, 5)" :key="p.id"
              class="bg-surface-2 rounded-lg p-3"
            >
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs font-mono text-gray-200">{{ p.name }}</span>
                <span class="text-[10px] text-cyan-400">{{ p.occurrences }} 次</span>
              </div>
              <div class="flex items-center gap-2">
                <div class="flex-1 h-1.5 bg-surface-3 rounded-full overflow-hidden">
                  <div class="h-full bg-cyan-500 rounded-full" :style="{ width: `${p.confidence}%` }" />
                </div>
                <span class="text-[10px] text-gray-500">{{ p.confidence }}%</span>
              </div>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <!-- 时间模式 -->
          <div class="bg-surface-1 rounded-xl border border-amber-500/20 p-4">
            <div class="text-xs text-amber-400 mb-3">时间规律</div>
            <div class="space-y-2">
              <div v-for="p in minedPatterns.filter(p => p.type === 'time')" :key="p.id"
                class="flex items-center justify-between py-1.5 border-b border-surface-3 last:border-0"
              >
                <div>
                  <div class="text-xs text-gray-200">{{ p.name }}</div>
                  <div class="text-[10px] text-gray-500">{{ p.description }}</div>
                </div>
                <span class="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400">{{ p.confidence }}%</span>
              </div>
            </div>
          </div>

          <!-- 关联模式 -->
          <div class="bg-surface-1 rounded-xl border border-pink-500/20 p-4">
            <div class="text-xs text-pink-400 mb-3">行为关联</div>
            <div class="space-y-2">
              <div v-for="p in minedPatterns.filter(p => p.type === 'correlation').slice(0, 5)" :key="p.id"
                class="flex items-center justify-between py-1.5 border-b border-surface-3 last:border-0"
              >
                <div>
                  <div class="text-xs font-mono text-gray-200">{{ p.name }}</div>
                  <div class="text-[10px] text-gray-500">{{ p.occurrences }} 次观察</div>
                </div>
                <span class="text-[10px] px-2 py-0.5 rounded-full bg-pink-500/15 text-pink-400">{{ p.confidence }}%</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 算法说明 -->
        <div class="bg-surface-2 rounded-lg p-3 text-[10px] text-gray-500 leading-relaxed">
          挖掘算法: 频繁序列挖掘（滑动窗口 + 最小支持度过滤）| 时间模式检测（小时/星期分布统计）| 关联规则挖掘（连续事件对频率分析）
        </div>
      </div>
    </div>

    <!-- 正在学习 -->
    <div>
      <div class="flex items-center gap-2 mb-3">
        <span class="inline-block w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
        <span class="text-sm font-medium text-yellow-400">正在学习 ({{ learningPatterns.length }})</span>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div
          v-for="pattern in learningPatterns"
          :key="pattern.id"
          class="bg-surface-1 rounded-xl border border-surface-3 p-4 space-y-3 cursor-pointer hover:border-yellow-500/40 transition-colors"
          @click="handleClickPattern(pattern)"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-[11px] px-2 py-0.5 rounded" :class="categoryColorMap[pattern.category]">{{ categoryLabel[pattern.category] }}</span>
              <span class="text-[10px] px-2 py-0.5 rounded bg-yellow-500/20 text-yellow-400 flex items-center gap-1">
                <span class="inline-block w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
                {{ statusLabel[pattern.status] }}
              </span>
            </div>
            <span class="text-[10px] text-gray-500">{{ pattern.evidence_count }} 条证据</span>
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
        </div>
      </div>
    </div>

    <!-- 已确认 -->
    <div>
      <div class="flex items-center gap-2 mb-3">
        <span class="inline-block w-2 h-2 rounded-full bg-blue-400" />
        <span class="text-sm font-medium text-blue-400">已确认 ({{ confirmedPatterns.length }})</span>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div
          v-for="pattern in confirmedPatterns"
          :key="pattern.id"
          class="bg-surface-1 rounded-xl border border-surface-3 p-4 space-y-3 cursor-pointer hover:border-blue-500/40 transition-colors"
          @click="handleClickPattern(pattern)"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-[11px] px-2 py-0.5 rounded" :class="categoryColorMap[pattern.category]">{{ categoryLabel[pattern.category] }}</span>
              <span class="text-[10px] px-2 py-0.5 rounded bg-blue-500/20 text-blue-400">{{ statusLabel[pattern.status] }}</span>
            </div>
            <span class="text-[10px] text-gray-500">{{ pattern.evidence_count }} 条证据</span>
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
        </div>
      </div>
    </div>

    <!-- Taste Agent -->
    <div>
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <span class="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          <span class="text-sm font-medium text-amber-400">Taste Agent 自动代理</span>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="text-[10px] px-2 py-1 rounded bg-surface-2 text-gray-400 hover:text-gray-200 transition-colors"
            :class="relearning ? 'opacity-50 pointer-events-none' : ''"
            @click="handleRelearn"
          >{{ relearning ? '重学中...' : '重新学习' }}</button>
          <button
            class="text-[10px] px-3 py-1 rounded transition-colors"
            :class="autoConfirming ? 'bg-surface-3 text-gray-500' : 'bg-amber-500/15 text-amber-400 hover:bg-amber-500/25'"
            :disabled="autoConfirming"
            @click="handleAutoConfirm"
          >{{ autoConfirming ? '执行中...' : '一键自动确认' }}</button>
        </div>
      </div>

      <!-- 执行结果 -->
      <div v-if="autoConfirmResult" class="mb-4 bg-surface-1 rounded-xl border border-amber-500/20 p-4">
        <div class="text-xs text-amber-400 mb-2">本次执行结果</div>
        <div class="grid grid-cols-3 gap-3">
          <div class="text-center">
            <div class="text-lg font-semibold text-emerald-400">{{ autoConfirmResult.confirmed }}</div>
            <div class="text-[10px] text-gray-500">已确认</div>
          </div>
          <div class="text-center">
            <div class="text-lg font-semibold text-blue-400">{{ autoConfirmResult.collect_more }}</div>
            <div class="text-[10px] text-gray-500">待积累</div>
          </div>
          <div class="text-center">
            <div class="text-lg font-semibold text-gray-400">{{ autoConfirmResult.deferred }}</div>
            <div class="text-[10px] text-gray-500">已推迟</div>
          </div>
        </div>
      </div>

      <div v-if="tasteLoading" class="text-xs text-gray-500 py-4 text-center">加载中...</div>
      <div v-else-if="tasteError" class="text-xs text-red-400 py-2">{{ tasteError }}</div>
      <div v-else-if="tasteProfile" class="space-y-4">
        <!-- 摘要 -->
        <div class="bg-surface-1 rounded-xl border border-surface-3 p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-[11px] text-amber-400">偏好摘要</span>
            <span class="text-[10px] text-gray-500">已学习 {{ tasteProfile.decision_history_count }} 条决策</span>
          </div>
          <div class="text-xs text-gray-300 leading-relaxed">{{ tasteProfile.taste_summary ?? '尚未形成偏好，请先进行几次 Pattern 确认/拒绝操作后重新学习。' }}</div>
          <div class="mt-3 flex items-center gap-3">
            <span class="text-[10px] text-gray-500">置信阈值</span>
            <span class="text-[11px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-300">{{ tasteProfile.preferred_confidence_threshold }}%</span>
            <span class="text-[10px] text-gray-500">偏好来源</span>
            <span v-for="src in tasteProfile.preferred_sources.slice(0, 3)" :key="src" class="text-[10px] px-2 py-0.5 rounded bg-surface-2 text-gray-300">{{ src }}</span>
            <span v-if="!tasteProfile.preferred_sources.length" class="text-[10px] text-gray-600">暂无</span>
          </div>
        </div>

        <!-- 类别权重 -->
        <div v-if="Object.keys(tasteProfile.preferred_categories).length" class="bg-surface-1 rounded-xl border border-surface-3 p-4">
          <div class="text-[11px] text-gray-400 mb-3">类别偏好权重</div>
          <div class="space-y-2">
            <div v-for="(weight, cat) in tasteProfile.preferred_categories" :key="cat" class="flex items-center gap-2">
              <span class="text-[10px] text-gray-400 w-20 shrink-0">{{ cat }}</span>
              <div class="flex-1 h-1.5 bg-surface-3 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all"
                  :class="(weight as number) >= 65 ? 'bg-emerald-500' : (weight as number) >= 45 ? 'bg-amber-500' : 'bg-gray-500'"
                  :style="{ width: `${weight}%` }"
                />
              </div>
              <span class="text-[10px] text-gray-500 w-8 text-right">{{ weight }}</span>
            </div>
          </div>
        </div>

        <!-- 待处理推荐 -->
        <div v-if="tasteProfile.top_pending.length">
          <div class="text-[11px] text-gray-400 mb-2">Taste Agent 优先推荐确认 ({{ tasteProfile.top_pending.length }})</div>
          <div class="space-y-2">
            <div
              v-for="p in tasteProfile.top_pending"
              :key="p.id"
              class="bg-surface-1 rounded-lg border border-surface-3 p-3 cursor-pointer hover:border-amber-500/30 transition-colors"
              @click="router.push(`/patterns/${p.id}`)"
            >
              <div class="flex items-center justify-between mb-1">
                <div class="flex items-center gap-2">
                  <span class="text-[10px] px-2 py-0.5 rounded" :class="categoryColorMap[p.category] ?? 'bg-gray-500/20 text-gray-400'">{{ categoryLabel[p.category] ?? p.category }}</span>
                  <span
                    class="text-[10px] px-2 py-0.5 rounded"
                    :class="p.taste_action === 'confirm' ? 'bg-emerald-500/15 text-emerald-400' : p.taste_action === 'collect_more' ? 'bg-blue-500/15 text-blue-400' : 'bg-gray-500/15 text-gray-400'"
                  >{{ p.taste_action === 'confirm' ? '建议确认' : p.taste_action === 'collect_more' ? '待积累' : '推迟' }}</span>
                </div>
                <span class="text-[10px] text-gray-500">优先分 {{ p.priority_score }}</span>
              </div>
              <div class="text-xs font-medium text-gray-200">{{ p.name }}</div>
              <div class="text-[10px] text-gray-500 mt-1 leading-relaxed">{{ p.taste_reasons.slice(0, 2).join(' · ') }}</div>
            </div>
          </div>
        </div>
        <div v-else class="text-xs text-gray-600 py-2">暂无 learning 状态的 Pattern，采集后会自动出现。</div>
      </div>
    </div>

    <!-- Autonomous Suggestions -->
    <div v-if="autonomousSuggestions.length">
      <div class="flex items-center gap-2 mb-3">
        <span class="inline-block w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
        <span class="text-sm font-medium text-teal-400">自主任务建议 ({{ autonomousSuggestions.length }})</span>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div v-for="(s, idx) in autonomousSuggestions" :key="idx" class="bg-surface-1 rounded-xl border border-surface-3 p-4 space-y-2">
          <div class="text-sm font-medium text-gray-200">{{ s.task }}</div>
          <div class="text-[11px] text-gray-400 leading-relaxed">{{ s.reason }}</div>
          <div class="flex items-center gap-3 text-[11px]">
            <span class="text-gray-500">置信度 <span :class="s.confidence >= 80 ? 'text-emerald-400' : s.confidence >= 60 ? 'text-amber-400' : 'text-gray-400'" class="font-medium">{{ s.confidence }}%</span></span>
            <span class="text-gray-500">频率 <span class="text-teal-400">{{ s.frequency }}</span></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 可导出 -->
    <div>
      <div class="flex items-center gap-2 mb-3">
        <span class="inline-block w-2 h-2 rounded-full bg-emerald-400" />
        <span class="text-sm font-medium text-emerald-400">可导出 ({{ exportablePatterns.length }})</span>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div
          v-for="pattern in exportablePatterns"
          :key="pattern.id"
          class="bg-surface-1 rounded-xl border border-surface-3 p-4 space-y-3 cursor-pointer hover:border-emerald-500/40 transition-colors"
          @click="handleClickPattern(pattern)"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-[11px] px-2 py-0.5 rounded" :class="categoryColorMap[pattern.category]">{{ categoryLabel[pattern.category] }}</span>
              <span class="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400">{{ statusLabel[pattern.status] }}</span>
              <span v-if="pattern.confidence >= 80" class="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">高置信</span>
            </div>
            <span class="text-[10px] text-gray-500">{{ pattern.evidence_count }} 条证据</span>
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
        </div>
      </div>
    </div>

    <!-- Claw Generator: CoT推理 + Workflow重建 → ClawProfile -->
    <div class="bg-surface-1 rounded-lg border border-surface-3 p-4 space-y-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="inline-block w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
          <span class="text-sm font-medium text-violet-400">Claw Generator</span>
          <span class="text-[10px] text-gray-600">CoT推理挖掘 + Workflow重建 → ClawProfile</span>
        </div>
        <div class="flex items-center gap-2">
          <button class="px-2 py-1 text-[10px] rounded bg-surface-2 text-gray-400 hover:text-gray-200 transition-colors" @click="handleExportMarkdown">导出 CLAUDE.md</button>
          <button class="px-2 py-1 text-[10px] rounded bg-violet-500/20 text-violet-400 hover:bg-violet-500/30 transition-colors" :disabled="clawGenerating" @click="handleGenerateClaw">
            {{ clawGenerating ? '挖掘中...' : '一键挖掘' }}
          </button>
        </div>
      </div>

      <!-- CoT 画像 -->
      <div v-if="cotProfile && cotProfile.session_count > 0" class="grid grid-cols-3 gap-2 text-[10px]">
        <div class="bg-surface-2 rounded p-2">
          <div class="text-gray-500 mb-0.5">推理深度</div>
          <div class="text-violet-400 font-medium">{{ cotProfile.avg_reasoning_depth }}/100</div>
          <div class="h-1 bg-surface-3 rounded-full mt-1 overflow-hidden">
            <div class="h-full bg-violet-500/60 rounded-full" :style="{ width: `${cotProfile.avg_reasoning_depth}%` }" />
          </div>
        </div>
        <div class="bg-surface-2 rounded p-2">
          <div class="text-gray-500 mb-0.5">步骤化思考率</div>
          <div class="text-blue-400 font-medium">{{ Math.round(cotProfile.step_thinking_rate * 100) }}%</div>
          <div class="h-1 bg-surface-3 rounded-full mt-1 overflow-hidden">
            <div class="h-full bg-blue-500/60 rounded-full" :style="{ width: `${cotProfile.step_thinking_rate * 100}%` }" />
          </div>
        </div>
        <div class="bg-surface-2 rounded p-2">
          <div class="text-gray-500 mb-0.5">修正次数</div>
          <div class="text-amber-400 font-medium">{{ cotProfile.total_corrections }}</div>
          <div class="text-[9px] text-gray-600 mt-0.5">{{ cotProfile.session_count }} 次对话</div>
        </div>
      </div>

      <!-- 生成结果 -->
      <div v-if="clawGenResult" class="space-y-2">
        <div class="text-[10px] text-gray-500">生成了 {{ clawGenResult.total_generated }} 个规范候选</div>
        <div v-if="clawGenResult.cot_skills.length" class="space-y-1">
          <div class="text-[10px] text-violet-400/70">CoT 推理技能 ({{ clawGenResult.cot_skills.length }})</div>
          <div v-for="s in clawGenResult.cot_skills" :key="s.id" class="flex items-center gap-2 px-2 py-1 rounded bg-surface-2">
            <span class="text-[10px] text-gray-300 flex-1 truncate">{{ s.name }}</span>
            <span class="text-[10px] text-violet-400">{{ s.confidence }}%</span>
          </div>
        </div>
        <div v-if="clawGenResult.workflow_patterns.length" class="space-y-1">
          <div class="text-[10px] text-cyan-400/70">Workflow 模板 ({{ clawGenResult.workflow_patterns.length }})</div>
          <div v-for="w in clawGenResult.workflow_patterns" :key="w.id" class="flex items-center gap-2 px-2 py-1 rounded bg-surface-2">
            <span class="text-[10px] text-gray-300 flex-1 truncate">{{ w.name }}</span>
            <span class="text-[10px] text-cyan-400">{{ w.confidence }}%</span>
          </div>
        </div>
      </div>

      <!-- Markdown 导出面板 -->
      <div v-if="showMarkdown && markdownExport" class="relative">
        <div class="flex items-center justify-between mb-1">
          <span class="text-[10px] text-gray-500">CLAUDE.md 格式导出</span>
          <button class="text-[10px] text-gray-600 hover:text-gray-400" @click="showMarkdown = false">关闭</button>
        </div>
        <pre class="text-[10px] font-mono text-gray-400 bg-[#0d0d1a] rounded p-3 max-h-48 overflow-y-auto whitespace-pre-wrap">{{ markdownExport }}</pre>
        <button class="mt-1 text-[10px] text-accent hover:underline" @click="copyMarkdownToClipboard()">复制到剪贴板</button>
      </div>
    </div>
  </div>
</template>
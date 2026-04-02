<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { generateClawsApi, exportMarkdownApi, getAlignmentScoreApi } from '@/http_api/claw_gen'
import type { CotProfile, AlignmentScore, ClawGenResult } from '@/http_api/claw_gen'
import { get, post } from '@/http_api/client'
import { getMemoryHealthApi } from '@/http_api/stats'
import type { MemoryHealth } from '@/types'
import { usePatternsStore } from '@/stores/patterns'

const router = useRouter()
const patternsStore = usePatternsStore()

const cotProfile = ref<CotProfile & Record<string, number> | null>(null)
const alignmentScore = ref<AlignmentScore | null>(null)
const memoryHealth = ref<MemoryHealth | null>(null)
const genResult = ref<ClawGenResult | null>(null)
const markdownOutput = ref('')
const showMarkdown = ref(false)
const generating = ref(false)
const loading = ref(true)
const maturity = ref<Record<string, any> | null>(null)
const beforeAfter = ref<{comparisons: any[]} | null>(null)
const loadingBA = ref(false)

// 5维度标签
const tasteDims = [
  { key: 'rigor', label: '理论严谨', icon: '⚖', color: '#6366f1', desc: '对形式化/证明/baseline的重视程度' },
  { key: 'elegance', label: '解法优雅', icon: '✨', color: '#ec4899', desc: '偏好简洁、最优解而非复杂方案' },
  { key: 'novelty', label: '创新导向', icon: '🔭', color: '#f59e0b', desc: '关注研究空白与新贡献的程度' },
  { key: 'simplicity', label: '极简主义', icon: '◉', color: '#10b981', desc: '倾向于减少不必要复杂度' },
  { key: 'reproducibility', label: '可复现性', icon: '♻', color: '#06b6d4', desc: '重视实验可复现与环境配置' },
]

// 雷达图点坐标计算
const radarCenter = { x: 150, y: 150 }
const radarRadius = 110
const radarLevels = [0.25, 0.5, 0.75, 1.0]

const getPoint = (index: number, total: number, ratio: number) => {
  const angle = (index / total) * 2 * Math.PI - Math.PI / 2
  return {
    x: radarCenter.x + radarRadius * ratio * Math.cos(angle),
    y: radarCenter.y + radarRadius * ratio * Math.sin(angle),
  }
}

const radarPolygon = computed(() => {
  if (!cotProfile.value) return ''
  const dims = tasteDims.map(d => ((cotProfile.value as any)[d.key] ?? 0) / 100)
  return dims.map((v, i) => {
    const p = getPoint(i, tasteDims.length, v)
    return `${p.x},${p.y}`
  }).join(' ')
})

const radarGridPolygon = (level: number) => {
  return tasteDims.map((_, i) => {
    const p = getPoint(i, tasteDims.length, level)
    return `${p.x},${p.y}`
  }).join(' ')
}

// 飞轮数据
const flywheelStats = computed(() => {
  const total = patternsStore.patterns.length
  const confirmed = patternsStore.patterns.filter(p => p.status === 'confirmed').length
  const avgConfidence = total > 0
    ? Math.round(patternsStore.patterns.reduce((s, p) => s + p.confidence, 0) / total)
    : 0
  return { total, confirmed, avgConfidence }
})

// 规则演化时间轴 (按 created_at 排序，取前15个)
const timelinePatterns = computed(() => {
  return [...patternsStore.patterns]
    .filter(p => p.created_at)
    .sort((a, b) => (a.created_at || 0) - (b.created_at || 0))
    .slice(-12)
})

const handleGenerate = async () => {
  generating.value = true
  genResult.value = null
  const res = await generateClawsApi()
  generating.value = false
  if (res.data) {
    genResult.value = res.data
    await patternsStore.fetchPatterns(undefined, true)
  }
}

const handleExport = async () => {
  const res = await exportMarkdownApi()
  if (res.data) {
    markdownOutput.value = res.data.markdown
    showMarkdown.value = true
  }
}

const handleBeforeAfter = async () => {
  loadingBA.value = true
  beforeAfter.value = null
  const res = await post<{comparisons: any[]}>('/claw/before-after', {})
  if (res.data) beforeAfter.value = res.data
  loadingBA.value = false
}

const handleCopy = async () => {
  await navigator.clipboard.writeText(markdownOutput.value)
}

const confidenceBarWidth = (c: number) => `${c}%`
const confidenceColor = (c: number) => {
  if (c >= 80) return 'bg-emerald-500'
  if (c >= 60) return 'bg-blue-500'
  if (c >= 40) return 'bg-amber-400'
  return 'bg-gray-500'
}
const statusColor = (s: string) => {
  if (s === 'confirmed') return 'text-emerald-400'
  if (s === 'learning') return 'text-amber-400'
  return 'text-gray-500'
}

const formatDate = (ts: number) => {
  const d = new Date(ts * 1000)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

onMounted(async () => {
  loading.value = true
  await patternsStore.ensurePatternsLoaded()
  const [twinRes, healthRes, alignRes, maturityRes] = await Promise.all([
    get<CotProfile & Record<string, number>>('/claw/twin-snapshot'),
    getMemoryHealthApi(),
    getAlignmentScoreApi(),
    get<Record<string, any>>('/claw/twin-maturity'),
  ])
  if (twinRes.data) cotProfile.value = twinRes.data
  if (healthRes.data) memoryHealth.value = healthRes.data
  if (alignRes.data) alignmentScore.value = alignRes.data
  if (maturityRes.data) maturity.value = maturityRes.data
  loading.value = false
})
</script>

<template>
  <div class="p-6 overflow-y-auto h-full space-y-6">

    <!-- Header: 核心叙事 -->
    <div class="flex items-end justify-between">
      <div>
        <h1 class="text-2xl font-semibold">My AI Twin</h1>
        <p class="text-sm text-gray-400 mt-0.5">AI 正在学习你的思维方式，而不只是记住你做过什么</p>
      </div>
      <div class="flex gap-2">
        <button class="px-3 py-2 text-xs rounded-lg bg-surface-2 text-gray-300 hover:bg-surface-3 transition-colors" @click="handleExport">
          导出 CLAUDE.md
        </button>
        <button
          class="px-4 py-2 text-xs font-medium rounded-lg transition-all"
          :class="generating ? 'bg-surface-2 text-gray-500' : 'bg-violet-500/20 text-violet-400 hover:bg-violet-500/30 active:scale-95'"
          :disabled="generating"
          @click="handleGenerate"
        >
          {{ generating ? '挖掘中...' : 'Claw the Claw' }}
        </button>
      </div>
    </div>

    <!-- V6: 研究品味雷达图 + CoT 画像 -->
    <div class="grid grid-cols-2 gap-4">
      <!-- 雷达图 -->
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
        <div class="text-sm font-medium text-gray-200 mb-1">研究品味雷达</div>
        <p class="text-[10px] text-gray-500 mb-4">基于 {{ cotProfile?.session_count ?? 0 }} 次 AI 对话分析</p>
        <div class="flex items-center gap-4">
          <!-- SVG 雷达 -->
          <svg viewBox="0 0 300 300" class="w-44 h-44 shrink-0">
            <!-- 网格 -->
            <polygon v-for="level in radarLevels" :key="level" :points="radarGridPolygon(level)" fill="none" stroke="#374151" stroke-width="1" />
            <!-- 轴线 -->
            <line v-for="(_, i) in tasteDims" :key="i"
              :x1="radarCenter.x" :y1="radarCenter.y"
              :x2="getPoint(i, tasteDims.length, 1).x"
              :y2="getPoint(i, tasteDims.length, 1).y"
              stroke="#374151" stroke-width="1" />
            <!-- 数据区域 -->
            <polygon v-if="cotProfile" :points="radarPolygon" fill="rgba(139,92,246,0.2)" stroke="#8b5cf6" stroke-width="2" stroke-linejoin="round" />
            <!-- 数据点 -->
            <template v-if="cotProfile">
              <circle v-for="(dim, i) in tasteDims" :key="dim.key"
                :cx="getPoint(i, tasteDims.length, ((cotProfile as any)[dim.key] ?? 0) / 100).x"
                :cy="getPoint(i, tasteDims.length, ((cotProfile as any)[dim.key] ?? 0) / 100).y"
                r="4" :fill="dim.color" />
            </template>
            <!-- 轴标签 -->
            <text v-for="(dim, i) in tasteDims" :key="dim.key + '-label'"
              :x="getPoint(i, tasteDims.length, 1.22).x"
              :y="getPoint(i, tasteDims.length, 1.22).y"
              text-anchor="middle" dominant-baseline="middle"
              font-size="11" fill="#9ca3af">
              {{ dim.label }}
            </text>
          </svg>
          <!-- 维度列表 -->
          <div class="flex-1 space-y-2.5">
            <div v-for="dim in tasteDims" :key="dim.key" class="space-y-1">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-1.5">
                  <div class="w-2 h-2 rounded-full" :style="{ background: dim.color }" />
                  <span class="text-[11px] text-gray-300">{{ dim.label }}</span>
                </div>
                <span class="text-[11px] font-mono" :style="{ color: dim.color }">
                  {{ cotProfile ? ((cotProfile as any)[dim.key] ?? 0) : 0 }}
                </span>
              </div>
              <div class="h-1.5 bg-surface-3 rounded-full overflow-hidden">
                <div class="h-full rounded-full transition-all duration-700"
                  :style="{ width: cotProfile ? `${(cotProfile as any)[dim.key] ?? 0}%` : '0%', background: dim.color, opacity: '0.7' }" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- CoT 数据面板 + 飞轮 -->
      <div class="space-y-3">
        <!-- CoT 核心数据 -->
        <div class="bg-surface-1 rounded-xl border border-surface-3 p-4">
          <div class="text-sm font-medium text-gray-200 mb-3">认知模式分析</div>
          <div v-if="cotProfile && cotProfile.session_count > 0" class="grid grid-cols-2 gap-2.5">
            <div class="bg-surface-2 rounded-lg p-3">
              <div class="text-xs text-gray-500 mb-1">推理深度</div>
              <div class="text-xl font-bold text-violet-400">{{ cotProfile.avg_reasoning_depth }}<span class="text-sm text-gray-600">/100</span></div>
              <div class="h-1 bg-surface-3 rounded-full mt-1.5 overflow-hidden">
                <div class="h-full bg-violet-500/70 rounded-full" :style="{ width: `${cotProfile.avg_reasoning_depth}%` }" />
              </div>
            </div>
            <div class="bg-surface-2 rounded-lg p-3">
              <div class="text-xs text-gray-500 mb-1">步骤化思考</div>
              <div class="text-xl font-bold text-blue-400">{{ Math.round(cotProfile.step_thinking_rate * 100) }}<span class="text-sm text-gray-600">%</span></div>
              <div class="h-1 bg-surface-3 rounded-full mt-1.5 overflow-hidden">
                <div class="h-full bg-blue-500/70 rounded-full" :style="{ width: `${cotProfile.step_thinking_rate * 100}%` }" />
              </div>
            </div>
            <div class="bg-surface-2 rounded-lg p-3">
              <div class="text-xs text-gray-500 mb-1">修正信号</div>
              <div class="text-xl font-bold text-amber-400">{{ cotProfile.total_corrections }}</div>
              <div class="text-[10px] text-gray-600 mt-0.5">揭示隐性偏好</div>
            </div>
            <div class="bg-surface-2 rounded-lg p-3">
              <div class="text-xs text-gray-500 mb-1">分析对话</div>
              <div class="text-xl font-bold text-gray-200">{{ cotProfile.session_count }}</div>
              <div class="text-[10px] text-gray-600 mt-0.5">会话</div>
            </div>
          </div>
          <div v-else class="text-xs text-gray-500 py-3 text-center">暂无足够对话数据</div>
        </div>

        <!-- V2: 认知对齐分数 -->
        <div v-if="alignmentScore" class="bg-surface-1 rounded-xl border border-surface-3 p-4">
          <div class="text-sm font-medium text-gray-200 mb-2">认知对齐分数</div>
          <p class="text-[10px] text-gray-500 mb-3">ClawProfile 与真实行为的匹配度</p>
          <div class="flex items-center gap-4">
            <div class="w-16 h-16 rounded-full border-4 flex items-center justify-center shrink-0"
              :class="{ 'border-emerald-400': alignmentScore.grade === 'A', 'border-blue-400': alignmentScore.grade === 'B', 'border-amber-400': alignmentScore.grade === 'C', 'border-orange-400': alignmentScore.grade === 'D', 'border-red-400': alignmentScore.grade === 'F' }">
              <div class="text-center">
                <div class="text-xl font-bold leading-none"
                  :class="{ 'text-emerald-400': alignmentScore.grade === 'A', 'text-blue-400': alignmentScore.grade === 'B', 'text-amber-400': alignmentScore.grade === 'C', 'text-orange-400': alignmentScore.grade === 'D', 'text-red-400': alignmentScore.grade === 'F' }">{{ alignmentScore.grade }}</div>
                <div class="text-[9px] text-gray-500">{{ alignmentScore.score }}</div>
              </div>
            </div>
            <div class="flex-1 space-y-1.5 text-[10px]">
              <div class="flex justify-between"><span class="text-gray-500">已确认规范</span><span class="text-emerald-400">{{ alignmentScore.confirmed }}</span></div>
              <div class="flex justify-between"><span class="text-gray-500">充分证据支撑</span><span class="text-blue-400">{{ alignmentScore.well_supported }}</span></div>
              <div class="flex justify-between"><span class="text-gray-500">主要领域</span><span class="text-gray-300">{{ alignmentScore.top_categories.slice(0,2).join(' / ') || '-' }}</span></div>
            </div>
          </div>
        </div>

    <!-- V8: 飞轮效应 -->
        <div class="bg-surface-1 rounded-xl border border-surface-3 p-4">
          <div class="text-sm font-medium text-gray-200 mb-2">飞轮效应</div>
          <p class="text-[10px] text-gray-500 mb-3">越用越准 — 数据积累量化</p>
          <div class="grid grid-cols-3 gap-2 text-center">
            <div>
              <div class="text-2xl font-bold text-gray-200">{{ flywheelStats.total }}</div>
              <div class="text-[10px] text-gray-500 mt-0.5">规范总数</div>
            </div>
            <div>
              <div class="text-2xl font-bold text-emerald-400">{{ flywheelStats.confirmed }}</div>
              <div class="text-[10px] text-gray-500 mt-0.5">已确认</div>
            </div>
            <div>
              <div class="text-2xl font-bold text-blue-400">{{ flywheelStats.avgConfidence }}<span class="text-sm">%</span></div>
              <div class="text-[10px] text-gray-500 mt-0.5">平均置信度</div>
            </div>
          </div>
          <div class="mt-3 pt-3 border-t border-surface-3">
            <div class="flex items-center justify-between text-[10px] text-gray-500">
              <span>你 → DevTwin 观察</span>
              <span class="text-violet-400">→</span>
              <span>规则生成</span>
              <span class="text-violet-400">→</span>
              <span>AI 更懂你</span>
              <span class="text-violet-400">→</span>
              <span>你更信任 AI</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- V7: Claw 演化时间轴 -->
    <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
      <div class="flex items-center justify-between mb-4">
        <div>
          <div class="text-sm font-medium text-gray-200">Claw 演化时间轴</div>
          <p class="text-[10px] text-gray-500 mt-0.5">每条规则的诞生与成长轨迹</p>
        </div>
        <span class="text-[10px] text-gray-600">最近 {{ timelinePatterns.length }} 条</span>
      </div>

      <div class="relative">
        <!-- 时间轴线 -->
        <div class="absolute left-16 top-0 bottom-0 w-px bg-surface-3" />

        <div class="space-y-3">
          <div v-for="p in timelinePatterns" :key="p.id" class="flex items-start gap-3 group">
            <!-- 日期 -->
            <div class="w-14 text-right shrink-0">
              <span class="text-[10px] text-gray-600">{{ p.created_at ? formatDate(p.created_at) : '--' }}</span>
            </div>
            <!-- 时间点 -->
            <div class="relative z-10 mt-1.5 shrink-0">
              <div class="w-2 h-2 rounded-full border-2 border-surface-1 transition-all group-hover:scale-150"
                :class="p.status === 'confirmed' ? 'bg-emerald-500' : p.status === 'learning' ? 'bg-amber-400' : 'bg-gray-600'" />
            </div>
            <!-- 规则卡 -->
            <div class="flex-1 bg-surface-2 rounded-lg px-3 py-2 hover:bg-surface-3 transition-colors cursor-pointer group-hover:border-accent/20 border border-transparent"
              @click="router.push(`/patterns/${p.id}`)">
              <div class="flex items-center justify-between">
                <span class="text-xs text-gray-200 truncate flex-1">{{ p.name }}</span>
                <div class="flex items-center gap-2 ml-2 shrink-0">
                  <span class="text-[10px]" :class="statusColor(p.status)">
                    {{ p.status === 'confirmed' ? 'confirmed' : p.status === 'learning' ? 'learning' : p.status }}
                  </span>
                  <!-- 置信度条 -->
                  <div class="w-16 h-1 bg-surface-3 rounded-full overflow-hidden">
                    <div class="h-full rounded-full" :class="confidenceColor(p.confidence)" :style="{ width: confidenceBarWidth(p.confidence) }" />
                  </div>
                  <span class="text-[10px] text-gray-600 tabular-nums">{{ p.confidence }}%</span>
                </div>
              </div>
              <div class="text-[10px] text-gray-500 mt-0.5">{{ p.category }} · {{ p.source || 'auto' }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 生成结果 -->
    <div v-if="genResult" class="bg-surface-1 rounded-xl border border-violet-500/20 p-5">
      <div class="flex items-center gap-2 mb-3">
        <div class="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
        <span class="text-sm font-medium text-violet-400">Claw the Claw 完成</span>
        <span class="text-[10px] text-gray-500">生成了 {{ genResult.total_generated }} 条新规范</span>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div v-if="genResult.cot_skills.length">
          <div class="text-[10px] text-gray-500 mb-1.5">CoT 推理技能 ({{ genResult.cot_skills.length }})</div>
          <div class="space-y-1">
            <div v-for="s in genResult.cot_skills" :key="s.id" class="flex items-center gap-2 text-xs bg-surface-2 px-2 py-1 rounded-lg">
              <div class="w-1.5 h-1.5 rounded-full bg-violet-400 shrink-0" />
              <span class="text-gray-300 flex-1 truncate">{{ s.name }}</span>
              <span class="text-violet-400/70">{{ s.confidence }}%</span>
            </div>
          </div>
        </div>
        <div v-if="genResult.workflow_patterns.length">
          <div class="text-[10px] text-gray-500 mb-1.5">Workflow 模板 ({{ genResult.workflow_patterns.length }})</div>
          <div class="space-y-1">
            <div v-for="w in genResult.workflow_patterns" :key="w.id" class="flex items-center gap-2 text-xs bg-surface-2 px-2 py-1 rounded-lg">
              <div class="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0" />
              <span class="text-gray-300 flex-1 truncate">{{ w.name }}</span>
              <span class="text-cyan-400/70">{{ w.confidence }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- V10: Twin 成熟度 + 关键洞察 -->
    <div v-if="maturity" class="bg-surface-1 rounded-xl border border-surface-3 p-5">
      <div class="flex items-center justify-between mb-4">
        <div>
          <div class="text-sm font-medium text-gray-200">AI Twin 成熟度</div>
          <p class="text-[10px] text-gray-500 mt-0.5">{{ maturity.stage }} — {{ maturity.stage_desc }}</p>
        </div>
        <div class="text-3xl font-bold text-violet-400">{{ maturity.maturity }}<span class="text-sm text-gray-500">%</span></div>
      </div>

      <!-- 成熟度进度条 -->
      <div class="h-3 bg-surface-3 rounded-full overflow-hidden mb-4">
        <div class="h-full rounded-full transition-all duration-1000"
          :style="{ width: `${maturity.maturity}%`, background: 'linear-gradient(90deg, #7c3aed, #8b5cf6, #a78bfa)' }" />
      </div>

      <!-- 三维度分解 -->
      <div class="grid grid-cols-3 gap-3 mb-4 text-center text-[10px]">
        <div class="bg-surface-2 rounded-lg p-2.5">
          <div class="text-gray-500">数据量</div>
          <div class="text-lg font-bold text-gray-200 mt-0.5">{{ maturity.breakdown?.data }}<span class="text-gray-600">/30</span></div>
          <div class="text-gray-600">{{ maturity.stats?.sessions_7d }}次会话 · {{ maturity.stats?.episodes_30d }}个片段</div>
        </div>
        <div class="bg-surface-2 rounded-lg p-2.5">
          <div class="text-gray-500">质量</div>
          <div class="text-lg font-bold text-emerald-400 mt-0.5">{{ maturity.breakdown?.quality }}<span class="text-gray-600">/40</span></div>
          <div class="text-gray-600">{{ maturity.stats?.confirmed_patterns }}/{{ maturity.stats?.total_patterns }} 规范已确认</div>
        </div>
        <div class="bg-surface-2 rounded-lg p-2.5">
          <div class="text-gray-500">多样性</div>
          <div class="text-lg font-bold text-blue-400 mt-0.5">{{ maturity.breakdown?.diversity }}<span class="text-gray-600">/30</span></div>
          <div class="text-gray-600">品味维度分布均匀度</div>
        </div>
      </div>

      <!-- 关键洞察 -->
      <div v-if="maturity.insights?.length" class="space-y-2">
        <div class="text-[10px] text-gray-500 font-medium">关键洞察</div>
        <div v-for="insight in maturity.insights" :key="insight.type"
          class="flex items-start gap-3 bg-surface-2 rounded-lg px-3 py-2.5">
          <div class="w-6 h-6 rounded-lg shrink-0 flex items-center justify-center text-xs mt-0.5"
            :class="{ 'bg-violet-500/20 text-violet-400': insight.type === 'dominant_trait', 'bg-amber-500/20 text-amber-400': insight.type === 'correction_signal', 'bg-blue-500/20 text-blue-400': insight.type === 'potential' }">
            {{ insight.type === 'dominant_trait' ? '★' : insight.type === 'correction_signal' ? '✗' : '↑' }}
          </div>
          <div>
            <div class="text-xs font-medium text-gray-200">{{ insight.title }}</div>
            <div class="text-[10px] text-gray-500 mt-0.5 leading-relaxed">{{ insight.desc }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- V9: Before/After 对比 -->
    <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
      <div class="flex items-center justify-between mb-3">
        <div>
          <div class="text-sm font-medium text-gray-200">Before / After</div>
          <p class="text-[10px] text-gray-500 mt-0.5">有/没有你的 ClawProfile 时，AI 回答的差异</p>
        </div>
        <button
          class="px-3 py-1.5 text-xs rounded-lg transition-all"
          :class="loadingBA ? 'bg-surface-2 text-gray-500' : 'bg-surface-2 text-gray-300 hover:bg-surface-3'"
          :disabled="loadingBA"
          @click="handleBeforeAfter"
        >
          {{ loadingBA ? 'AI 生成中...' : '生成对比' }}
        </button>
      </div>

      <div v-if="!beforeAfter && !loadingBA" class="text-center py-8">
        <div class="text-gray-600 text-xs">点击"生成对比"查看 ClawProfile 的实际效果</div>
        <div class="text-gray-700 text-[10px] mt-1">需要已确认的规范 + AI 调用（约10秒）</div>
      </div>

      <div v-if="loadingBA" class="text-center py-8">
        <div class="w-5 h-5 border-2 border-violet-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
        <div class="text-[10px] text-gray-600">正在用你的 ClawProfile 生成对比示例...</div>
      </div>

      <div v-if="beforeAfter && beforeAfter.comparisons.length" class="space-y-4">
        <div v-for="comp in beforeAfter.comparisons" :key="comp.pattern_id" class="space-y-3">
          <div class="text-[10px] text-gray-500 font-mono border-b border-surface-3 pb-2">
            规范: <span class="text-violet-400">{{ comp.pattern_name }}</span>
            <span class="text-gray-600 ml-2">({{ comp.confidence }}%)</span>
          </div>
          <div class="text-xs text-gray-400 italic">问题: {{ comp.question }}</div>
          <div class="grid grid-cols-2 gap-3">
            <div class="bg-red-950/20 border border-red-900/30 rounded-lg p-3">
              <div class="text-[10px] text-red-400 font-medium mb-1.5">WITHOUT ClawProfile</div>
              <div class="text-[11px] text-gray-400 leading-relaxed">{{ comp.without }}</div>
            </div>
            <div class="bg-emerald-950/20 border border-emerald-900/30 rounded-lg p-3">
              <div class="text-[10px] text-emerald-400 font-medium mb-1.5">WITH ClawProfile ✓</div>
              <div class="text-[11px] text-gray-300 leading-relaxed">{{ comp.with }}</div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="beforeAfter && beforeAfter.comparisons.length === 0" class="text-center py-6">
        <div class="text-xs text-gray-500">{{ (beforeAfter as any).message || '暂无对比数据' }}</div>
      </div>
    </div>

    <!-- CLAUDE.md 导出 -->
    <div v-if="showMarkdown" class="bg-surface-1 rounded-xl border border-surface-3 overflow-hidden">
      <div class="flex items-center justify-between px-4 py-2.5 bg-[#1a1a2e] border-b border-surface-3">
        <div class="flex items-center gap-2">
          <div class="flex gap-1.5">
            <div class="w-3 h-3 rounded-full bg-red-500/80" />
            <div class="w-3 h-3 rounded-full bg-amber-500/80" />
            <div class="w-3 h-3 rounded-full bg-emerald-500/80" />
          </div>
          <span class="text-[11px] text-gray-500 font-mono ml-2">CLAUDE.md — 你的个人 AI 工作规范</span>
        </div>
        <div class="flex items-center gap-2">
          <button class="text-[10px] text-accent hover:underline" @click="handleCopy">复制</button>
          <button class="text-[10px] text-gray-500 hover:text-gray-300" @click="showMarkdown = false">关闭</button>
        </div>
      </div>
      <pre class="text-[11px] font-mono text-gray-400 bg-[#0d0d1a] px-5 py-4 max-h-72 overflow-y-auto whitespace-pre-wrap leading-relaxed">{{ markdownOutput }}</pre>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import * as d3 from 'd3'
import { generateClawsApi, exportMarkdownApi, getAlignmentScoreApi } from '@/http_api/claw_gen'
import type { CotProfile, AlignmentScore, ClawGenResult } from '@/http_api/claw_gen'

type TasteDimKey = 'rigor' | 'elegance' | 'novelty' | 'simplicity' | 'reproducibility'

type BeforeAfterComparison = {
  pattern_id: number
  pattern_name: string
  confidence: number
  question: string
  without: string
  with: string
}

type BeforeAfterPayload = {
  comparisons: BeforeAfterComparison[]
  message?: string
}

type TwinMaturity = {
  stage: string
  stage_desc: string
  maturity: number
  breakdown?: { data: number; quality: number; diversity: number }
  stats?: {
    sessions_7d: number
    episodes_30d: number
    confirmed_patterns: number
    total_patterns: number
  }
  insights?: Array<{ type: string; title: string; desc: string }>
}

const tasteDimScore = (profile: CotProfile | null, key: TasteDimKey): number =>
  profile ? (profile[key] ?? 0) : 0
import { get, post } from '@/http_api/client'
import { getMemoryHealthApi, getFlywheelTrendApi } from '@/http_api/stats'
import type { FlywheelPoint } from '@/http_api/stats'
import type { MemoryHealth } from '@/types'
import { usePatternsStore } from '@/stores/patterns'
import EmptyState from '@/components/shared/empty_state.vue'

const router = useRouter()
const patternsStore = usePatternsStore()

const cotProfile = ref<CotProfile | null>(null)
const alignmentScore = ref<AlignmentScore | null>(null)
const memoryHealth = ref<MemoryHealth | null>(null)
const genResult = ref<ClawGenResult | null>(null)
const markdownOutput = ref('')
const showMarkdown = ref(false)
const generating = ref(false)
const loading = ref(true)
const maturity = ref<TwinMaturity | null>(null)
const beforeAfter = ref<BeforeAfterPayload | null>(null)
const loadingBA = ref(false)
const flywheelTrend = ref<FlywheelPoint[]>([])
const flywheelChartRef = ref<HTMLDivElement | null>(null)

// 5维度标签
const tasteDims: { key: TasteDimKey; label: string; icon: string; color: string; desc: string }[] = [
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
  const dims = tasteDims.map(d => tasteDimScore(cotProfile.value, d.key) / 100)
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
  const res = await post<BeforeAfterPayload>('/claw/before-after', {})
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

const selectedTimelineId = ref<number | null>(null)
const evolutionChartRef = ref<HTMLDivElement | null>(null)

const toggleEvolution = (id: number) => {
  selectedTimelineId.value = selectedTimelineId.value === id ? null : id
}

const formatDate = (ts: number) => {
  const d = new Date(ts * 1000)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

const renderEvolutionChart = () => {
  const el = evolutionChartRef.value
  if (!el || !selectedTimelineId.value) return
  const pattern = patternsStore.patterns.find(p => p.id === selectedTimelineId.value)
  if (!pattern || !pattern.evolution || pattern.evolution.length < 2) return

  d3.select(el).selectAll('*').remove()
  const data = pattern.evolution

  const margin = { top: 8, right: 8, bottom: 18, left: 26 }
  const width = el.clientWidth - margin.left - margin.right
  const height = 80 - margin.top - margin.bottom

  const svg = d3.select(el).append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`)

  const x = d3.scalePoint<string>()
    .domain(data.map(d => d.date))
    .range([0, width])
    .padding(0.3)

  const y = d3.scaleLinear()
    .domain([0, 100])
    .range([height, 0])

  svg.append('g')
    .attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(x).tickValues(data.length <= 6 ? data.map(d => d.date) : [data[0].date, data[data.length - 1].date]))
    .selectAll('text').attr('fill', '#6b7280').attr('font-size', '8px')

  svg.selectAll('.domain, .tick line').attr('stroke', '#374151')

  const area = d3.area<typeof data[0]>()
    .x(d => x(d.date)!)
    .y0(height)
    .y1(d => y(d.confidence))
    .curve(d3.curveMonotoneX)

  svg.append('path').datum(data)
    .attr('d', area)
    .attr('fill', 'rgba(16,185,129,0.1)')

  svg.append('path').datum(data)
    .attr('d', d3.line<typeof data[0]>().x(d => x(d.date)!).y(d => y(d.confidence)).curve(d3.curveMonotoneX))
    .attr('fill', 'none').attr('stroke', '#10b981').attr('stroke-width', 1.5)

  svg.selectAll('.evo-dot')
    .data(data)
    .join('circle')
    .attr('cx', d => x(d.date)!)
    .attr('cy', d => y(d.confidence))
    .attr('r', 3)
    .attr('fill', d => d.event_description.includes('确认') || d.event_description.toLowerCase().includes('confirm') ? '#10b981' : d.event_description.includes('拒绝') ? '#ef4444' : '#6366f1')

  svg.selectAll('.evo-label')
    .data(data)
    .join('text')
    .attr('x', d => x(d.date)!)
    .attr('y', d => y(d.confidence) - 6)
    .attr('text-anchor', 'middle')
    .attr('font-size', '8px')
    .attr('fill', '#9ca3af')
    .text(d => d.confidence)
}

watch(selectedTimelineId, () => { nextTick(renderEvolutionChart) })

const renderFlywheelChart = () => {
  const el = flywheelChartRef.value
  const data = flywheelTrend.value
  if (!el || data.length < 2) return

  d3.select(el).selectAll('*').remove()

  const margin = { top: 18, right: 14, bottom: 24, left: 30 }
  const width = el.clientWidth - margin.left - margin.right
  const height = 148 - margin.top - margin.bottom
  const rootStyle = getComputedStyle(document.documentElement)
  const chart1 = rootStyle.getPropertyValue('--color-chart-1').trim() || '#818cf8'
  const chart2 = rootStyle.getPropertyValue('--color-chart-2').trim() || '#6ee7b7'

  const svg = d3.select(el).append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`)

  const parseDate = d3.timeParse('%Y-%m-%d')
  const parsed = data.map(d => ({ ...d, d: parseDate(d.date)! })).filter(d => d.d)

  const x = d3.scaleTime()
    .domain(d3.extent(parsed, d => d.d) as [Date, Date])
    .range([0, width])

  const yConf = d3.scaleLinear()
    .domain([0, 100])
    .range([height, 0])

  const yCount = d3.scaleLinear()
    .domain([0, d3.max(parsed, d => d.total) || 1])
    .range([height, 0])

  svg.append('g')
    .attr('transform', `translate(0,${height})`)
    .call(
      d3.axisBottom(x).ticks(Math.min(parsed.length, 5)).tickFormat((d) => d3.timeFormat('%m/%d')(d as Date)),
    )
    .selectAll('text').attr('fill', '#6b7280').attr('font-size', '9px')

  svg.selectAll('.domain, .tick line').attr('stroke', '#374151')

  // confidence area + line
  const confArea = d3.area<typeof parsed[0]>()
    .x(d => x(d.d))
    .y0(height)
    .y1(d => yConf(d.avg_confidence))
    .curve(d3.curveMonotoneX)

  svg.append('path')
    .datum(parsed)
    .attr('d', confArea)
    .attr('fill', chart1)
    .attr('fill-opacity', 0.14)

  svg.append('path')
    .datum(parsed)
    .attr('d', d3.line<typeof parsed[0]>().x(d => x(d.d)).y(d => yConf(d.avg_confidence)).curve(d3.curveMonotoneX))
    .attr('fill', 'none')
    .attr('stroke', chart1)
    .attr('stroke-width', 2)

  // total patterns line (dashed)
  svg.append('path')
    .datum(parsed)
    .attr('d', d3.line<typeof parsed[0]>().x(d => x(d.d)).y(d => yCount(d.total)).curve(d3.curveMonotoneX))
    .attr('fill', 'none')
    .attr('stroke', '#9ca3af')
    .attr('stroke-width', 1.5)
    .attr('stroke-dasharray', '4,3')

  // confirmed patterns line
  svg.append('path')
    .datum(parsed)
    .attr('d', d3.line<typeof parsed[0]>().x(d => x(d.d)).y(d => yCount(d.confirmed)).curve(d3.curveMonotoneX))
    .attr('fill', 'none')
    .attr('stroke', chart2)
    .attr('stroke-width', 1.5)

  // latest point dots
  const last = parsed[parsed.length - 1]
  svg.append('circle').attr('cx', x(last.d)).attr('cy', yConf(last.avg_confidence)).attr('r', 3).attr('fill', chart1)
  svg.append('circle').attr('cx', x(last.d)).attr('cy', yCount(last.confirmed)).attr('r', 3).attr('fill', chart2)
}

watch(flywheelTrend, () => { nextTick(renderFlywheelChart) })

onMounted(async () => {
  loading.value = true
  await patternsStore.ensurePatternsLoaded()
  const [twinRes, healthRes, alignRes, maturityRes, trendRes] = await Promise.all([
    get<CotProfile>('/claw/twin-snapshot'),
    getMemoryHealthApi(),
    getAlignmentScoreApi(),
    get<TwinMaturity>('/claw/twin-maturity'),
    getFlywheelTrendApi(),
  ])
  if (twinRes.data) cotProfile.value = twinRes.data
  if (healthRes.data) memoryHealth.value = healthRes.data
  if (alignRes.data) alignmentScore.value = alignRes.data
  if (maturityRes.data) maturity.value = maturityRes.data
  if (trendRes.data) flywheelTrend.value = trendRes.data.points
  loading.value = false
})
</script>

<template>
  <div class="p-6 overflow-y-auto h-full space-y-6">

    <!-- Header: 核心叙事 -->
    <div class="flex items-end justify-between">
      <div>
        <h1 class="text-2xl font-semibold heading-tight">My AI Twin</h1>
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
        <div class="flex items-center justify-between mb-1">
          <div class="text-sm font-medium text-gray-200">研究品味雷达</div>
          <span
            v-if="cotProfile?._confidence && cotProfile._confidence !== 'high'"
            class="text-[9px] px-1.5 py-0.5 rounded-full"
            :class="cotProfile._confidence === 'low' ? 'bg-amber-500/20 text-amber-300' : 'bg-sky-500/20 text-sky-300'"
            :title="`样本可信度：${cotProfile._confidence}（消息数 ${cotProfile._message_count ?? 0}）`"
          >{{ cotProfile._confidence === 'low' ? '样本不足 · 试用期估计' : '中置信' }}</span>
        </div>
        <p class="text-[10px] text-gray-500 mb-4">基于 {{ cotProfile?.session_count ?? 0 }} 次 AI 对话分析</p>
        <div class="flex items-center gap-4">
          <!-- SVG 雷达 -->
          <svg
            viewBox="0 0 300 300"
            class="w-44 h-44 shrink-0"
            :class="cotProfile?._confidence === 'low' ? 'opacity-60' : ''"
          >
            <!-- 网格 -->
            <polygon v-for="level in radarLevels" :key="level" :points="radarGridPolygon(level)" fill="none" stroke="#374151" stroke-width="1" />
            <!-- 轴线 -->
            <line v-for="(_, i) in tasteDims" :key="i"
              :x1="radarCenter.x" :y1="radarCenter.y"
              :x2="getPoint(i, tasteDims.length, 1).x"
              :y2="getPoint(i, tasteDims.length, 1).y"
              stroke="#374151" stroke-width="1" />
            <!-- 数据区域 -->
            <polygon
              v-if="cotProfile"
              :points="radarPolygon"
              fill="var(--color-chart-1)"
              fill-opacity="0.22"
              stroke="var(--color-chart-1)"
              :stroke-dasharray="cotProfile?._confidence === 'low' ? '4 3' : '0'"
              stroke-width="2"
              stroke-linejoin="round"
            />
            <!-- 数据点 -->
            <template v-if="cotProfile">
              <circle v-for="(dim, i) in tasteDims" :key="dim.key"
                :cx="getPoint(i, tasteDims.length, tasteDimScore(cotProfile, dim.key) / 100).x"
                :cy="getPoint(i, tasteDims.length, tasteDimScore(cotProfile, dim.key) / 100).y"
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
            <!-- 样本不足水印 -->
            <text
              v-if="cotProfile?._confidence === 'low'"
              x="150" y="150"
              text-anchor="middle"
              dominant-baseline="middle"
              font-size="11"
              fill="#f59e0b"
              opacity="0.8"
            >占位 · 需更多对话</text>
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
                  {{ tasteDimScore(cotProfile, dim.key) }}
                </span>
              </div>
              <div class="h-1.5 bg-surface-3 rounded-full overflow-hidden">
                <div class="h-full rounded-full transition-all duration-700"
                  :style="{ width: `${tasteDimScore(cotProfile, dim.key)}%`, background: dim.color, opacity: '0.7' }" />
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
          <EmptyState
            v-else
            icon="compass"
            compact
            title="雷达还在等你的对话"
            description="ShrimpFlow 需要从你和 AI 的真实对话里提炼思维风格。推荐先和 OpenClaw / Claude Code 交互几轮，或用 claude-code CLI 连 Profile。"
            action-label="打开 OpenClaw"
            action-to="/openclaw"
          />
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
        <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
          <div class="flex flex-wrap items-end justify-between gap-3 mb-4">
            <div>
              <div class="text-sm font-medium text-gray-200">飞轮效应</div>
              <p class="text-[10px] text-gray-500 mt-1">越用越准 — 置信度随时间增长</p>
            </div>
            <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-[10px] shrink-0">
              <span class="flex items-center gap-1.5"><span class="w-3 h-0.5 rounded bg-[var(--color-chart-1)] inline-block" /> 置信度</span>
              <span class="flex items-center gap-1.5"><span class="w-3 h-0.5 rounded bg-[var(--color-chart-2)] inline-block" /> 已确认</span>
              <span class="flex items-center gap-1.5"><span class="w-3 h-0.5 bg-gray-400 inline-block rounded border-dashed" style="border-top:1px dashed #9ca3af;height:0" /> 总数</span>
            </div>
          </div>
          <div v-if="flywheelTrend.length >= 2" ref="flywheelChartRef" class="w-full min-h-[148px]" style="height:148px" />
          <div v-else class="flex items-center justify-center min-h-[5.5rem] py-4 text-[10px] text-gray-600">
            数据积累中，至少需要 2 天数据
          </div>
          <div class="grid grid-cols-3 gap-3 text-center mt-4 pt-4 border-t border-surface-3">
            <div>
              <div class="text-lg font-bold text-gray-200">{{ flywheelStats.total }}</div>
              <div class="text-[10px] text-gray-500">规范总数</div>
            </div>
            <div>
              <div class="text-lg font-bold text-emerald-400">{{ flywheelStats.confirmed }}</div>
              <div class="text-[10px] text-gray-500">已确认</div>
            </div>
            <div>
              <div class="text-lg font-bold text-[var(--color-chart-1)]">{{ flywheelStats.avgConfidence }}<span class="text-xs">%</span></div>
              <div class="text-[10px] text-gray-500">平均置信度</div>
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
          <div v-for="p in timelinePatterns" :key="p.id">
            <div class="flex items-start gap-3 group">
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
              <div class="flex-1 bg-surface-2 rounded-lg px-3 py-2 hover:bg-surface-3 transition-colors cursor-pointer border"
                :class="selectedTimelineId === p.id ? 'border-emerald-500/30' : 'border-transparent group-hover:border-accent/20'"
                @click="toggleEvolution(p.id)">
                <div class="flex items-center justify-between">
                  <span class="text-xs text-gray-200 truncate flex-1">{{ p.name }}</span>
                  <div class="flex items-center gap-2 ml-2 shrink-0">
                    <span v-if="p.evolution && p.evolution.length > 1" class="text-[9px] text-gray-600">{{ p.evolution.length }} 次演化</span>
                    <span class="text-[10px]" :class="statusColor(p.status)">
                      {{ p.status === 'confirmed' ? 'confirmed' : p.status === 'learning' ? 'learning' : p.status }}
                    </span>
                    <div class="w-16 h-1 bg-surface-3 rounded-full overflow-hidden">
                      <div class="h-full rounded-full" :class="confidenceColor(p.confidence)" :style="{ width: confidenceBarWidth(p.confidence) }" />
                    </div>
                    <span class="text-[10px] text-gray-600 tabular-nums">{{ p.confidence }}%</span>
                  </div>
                </div>
                <div class="text-[10px] text-gray-500 mt-0.5">{{ p.category }} · {{ p.source || 'auto' }}</div>
              </div>
            </div>
            <!-- evolution mini chart -->
            <div v-if="selectedTimelineId === p.id && p.evolution && p.evolution.length >= 2"
              class="ml-[4.75rem] mt-1.5 bg-surface-2 rounded-lg border border-emerald-500/10 p-3">
              <div class="flex items-center justify-between mb-1">
                <span class="text-[10px] text-gray-500">置信度演化轨迹</span>
                <button class="text-[10px] text-gray-600 hover:text-gray-300" @click.stop="router.push(`/patterns/${p.id}`)">详情 →</button>
              </div>
              <div ref="evolutionChartRef" class="w-full" style="height:80px" />
              <div class="mt-2 space-y-1 max-h-20 overflow-y-auto">
                <div v-for="(evo, i) in p.evolution.slice(-5)" :key="i" class="flex items-center gap-2 text-[9px]">
                  <span class="text-gray-600 w-12 shrink-0">{{ evo.date }}</span>
                  <span class="font-mono w-6 text-right" :class="evo.confidence >= 70 ? 'text-emerald-400' : 'text-amber-400'">{{ evo.confidence }}</span>
                  <span class="text-gray-500 truncate">{{ evo.event_description }}</span>
                </div>
              </div>
            </div>
            <div v-else-if="selectedTimelineId === p.id && (!p.evolution || p.evolution.length < 2)"
              class="ml-[4.75rem] mt-1.5 bg-surface-2 rounded-lg p-3 text-[10px] text-gray-600 text-center">
              演化数据不足（至少需要 2 个快照）
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
        <div class="text-xs text-gray-500">{{ beforeAfter.message || '暂无对比数据' }}</div>
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

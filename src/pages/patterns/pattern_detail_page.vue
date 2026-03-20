<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import type { BehaviorPattern } from '@/types'
import { dayjs } from '@/libs/dayjs'
import { getPatternApi } from '@/http_api/patterns'

const route = useRoute()
const router = useRouter()
const pattern = ref<BehaviorPattern | null>(null)
const loading = ref(false)
const loadError = ref<string | null>(null)
const notFound = ref(false)
let activeRequestId = 0

const loadPattern = async (rawId: unknown) => {
  const id = Number(rawId)
  const requestId = ++activeRequestId

  pattern.value = null
  loadError.value = null
  notFound.value = false
  loading.value = false

  if (!Number.isFinite(id) || id <= 0) {
    notFound.value = true
    return
  }

  loading.value = true
  const { data, error } = await getPatternApi(id)

  if (requestId !== activeRequestId) return

  if (data) pattern.value = data
  else if (error?.startsWith('404')) notFound.value = true
  else loadError.value = error ?? '行为模式加载失败，请稍后重试'

  loading.value = false
}

const retryLoad = () => void loadPattern(route.params.id)

watch(() => route.params.id, id => {
  void loadPattern(id)
}, { immediate: true })

const statusColorMap: Record<string, string> = {
  learning: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  confirmed: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  exportable: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
}

const statusLabel: Record<string, string> = {
  learning: '学习中', confirmed: '已确认', exportable: '可导出',
}

const categoryLabel: Record<string, string> = {
  git: 'Git 规范', coding: '编码习惯', review: '代码审查',
  devops: '运维部署', collaboration: '协作模式',
}

const confidenceColor = (c: number): string => {
  if (c > 60) return 'text-emerald-400'
  if (c >= 30) return 'text-yellow-400'
  return 'text-red-400'
}

const confidenceBg = (c: number): string => {
  if (c > 60) return 'bg-emerald-400'
  if (c >= 30) return 'bg-yellow-400'
  return 'bg-red-400'
}

const resultColorMap: Record<string, string> = {
  success: 'bg-emerald-500/20 text-emerald-400',
  skipped: 'bg-gray-500/20 text-gray-400',
  modified: 'bg-yellow-500/20 text-yellow-400',
}

const resultLabel: Record<string, string> = {
  success: '成功', skipped: '跳过', modified: '已调整',
}

const formatTime = (ts: number) => dayjs(ts * 1000).format('YYYY-MM-DD HH:mm:ss')

const goBack = () => router.push('/patterns')

// 置信度演化曲线 SVG 计算
const chartPadding = { top: 20, right: 20, bottom: 30, left: 40 }
const chartHeight = 200
const chartInnerHeight = chartHeight - chartPadding.top - chartPadding.bottom
const chartInnerWidth = computed(() => {
  const points = pattern.value?.evolution ?? []
  return Math.max(points.length * 80, 300)
})
const chartWidth = computed(() => chartInnerWidth.value + chartPadding.left + chartPadding.right)

const svgPoints = computed(() => {
  const evo = pattern.value?.evolution ?? []
  if (evo.length === 0) return []
  const w = chartInnerWidth.value
  const h = chartInnerHeight
  return evo.map((snap, i) => ({
    x: chartPadding.left + (evo.length === 1 ? w / 2 : (i / (evo.length - 1)) * w),
    y: chartPadding.top + h - (snap.confidence / 100) * h,
    confidence: snap.confidence,
    date: snap.date,
  }))
})

const linePath = computed(() => {
  const pts = svgPoints.value
  if (pts.length === 0) return ''
  return pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')
})

const areaPath = computed(() => {
  const pts = svgPoints.value
  if (pts.length === 0) return ''
  const baseline = chartPadding.top + chartInnerHeight
  return `${linePath.value} L${pts[pts.length - 1].x},${baseline} L${pts[0].x},${baseline} Z`
})

const gridLines = computed(() => {
  const w = chartWidth.value
  return [25, 50, 75].map(pct => ({
    y: chartPadding.top + chartInnerHeight - (pct / 100) * chartInnerHeight,
    label: `${pct}%`,
    x1: chartPadding.left,
    x2: w - chartPadding.right,
  }))
})

const finalConfidence = computed(() => {
  const evo = pattern.value?.evolution ?? []
  return evo.length > 0 ? evo[evo.length - 1].confidence : 0
})
</script>

<template>
  <div class="p-6 space-y-6 overflow-y-auto h-full">
    <!-- 返回按钮 -->
    <button class="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors cursor-pointer" @click="goBack">
      <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
      返回行为模式列表
    </button>

    <div v-if="loading" class="bg-surface-1 rounded-xl border border-surface-3 py-20 text-center text-gray-500">
      <div class="text-lg mb-2">正在加载行为模式...</div>
      <div class="text-sm text-gray-600">请稍候</div>
    </div>

    <div v-else-if="loadError" class="bg-surface-1 rounded-xl border border-red-500/20 py-20 text-center text-gray-400">
      <div class="text-lg mb-2 text-gray-200">行为模式加载失败</div>
      <div class="text-sm text-red-300 mb-4">{{ loadError }}</div>
      <button class="text-sm text-accent hover:text-accent-glow cursor-pointer" @click="retryLoad">重试</button>
    </div>

    <!-- 未找到 -->
    <div v-else-if="notFound" class="text-center text-gray-500 py-20">
      <div class="text-lg mb-2">未找到该行为模式</div>
      <button class="text-sm text-accent hover:text-accent-glow cursor-pointer" @click="goBack">返回列表</button>
    </div>

    <template v-else-if="pattern">
      <!-- 顶部信息 -->
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-6">
        <div class="flex items-start justify-between">
          <div class="space-y-2">
            <div class="flex items-center gap-3">
              <h1 class="text-xl font-semibold text-gray-100">{{ pattern.name }}</h1>
              <span class="text-[11px] px-2.5 py-0.5 rounded border" :class="statusColorMap[pattern.status]">{{ statusLabel[pattern.status] }}</span>
            </div>
            <div class="text-sm text-gray-400">{{ pattern.description }}</div>
            <div class="flex items-center gap-4 text-xs text-gray-500">
              <span>{{ categoryLabel[pattern.category] }}</span>
              <span>{{ pattern.evidence_count }} 条证据</span>
              <span>数据来源: {{ pattern.learned_from }}</span>
            </div>
          </div>
          <div class="text-right shrink-0 ml-6">
            <div class="text-[10px] text-gray-500 mb-1">置信度</div>
            <div class="text-4xl font-bold" :class="confidenceColor(pattern.confidence)">{{ pattern.confidence }}%</div>
          </div>
        </div>
        <div class="mt-4 bg-surface-2 rounded-lg p-3">
          <div class="text-[10px] text-gray-500 mb-1">可执行规则</div>
          <div class="text-sm text-gray-300 font-mono">{{ pattern.rule }}</div>
        </div>
        <!-- trigger 详情 -->
        <div v-if="pattern.trigger" class="mt-3 bg-surface-2 rounded-lg p-3">
          <div class="text-[10px] text-gray-500 mb-1">触发条件</div>
          <template v-if="typeof pattern.trigger === 'object'">
            <div class="text-sm text-gray-300">{{ (pattern.trigger as any).when }}</div>
            <div v-if="(pattern.trigger as any).event" class="text-xs text-gray-500 mt-1">事件: {{ (pattern.trigger as any).event }}</div>
            <div v-if="(pattern.trigger as any).globs" class="flex flex-wrap gap-1.5 mt-1.5">
              <span v-for="g in (pattern.trigger as any).globs" :key="g" class="text-[10px] px-2 py-0.5 rounded bg-surface-3 text-gray-400 font-mono">{{ g }}</span>
            </div>
            <div v-if="(pattern.trigger as any).context" class="flex flex-wrap gap-1.5 mt-1.5">
              <span v-for="c in (pattern.trigger as any).context" :key="c" class="text-[10px] px-2 py-0.5 rounded bg-accent/10 text-accent">{{ c }}</span>
            </div>
          </template>
          <div v-else class="text-sm text-gray-300">{{ pattern.trigger }}</div>
        </div>
      </div>

      <!-- Prompt 正文 (body) -->
      <div v-if="pattern.body" class="bg-surface-1 rounded-xl border border-surface-3 p-6">
        <div class="text-sm font-medium text-gray-300 mb-3">Prompt 正文</div>
        <div class="text-sm text-gray-400 whitespace-pre-wrap leading-relaxed font-mono bg-surface-2 rounded-lg p-4 max-h-80 overflow-y-auto">{{ pattern.body }}</div>
      </div>

      <!-- 经验洞察 (learned_from_data) -->
      <div v-if="pattern.learned_from_data && pattern.learned_from_data.length > 0" class="bg-surface-1 rounded-xl border border-surface-3 p-6">
        <div class="text-sm font-medium text-gray-300 mb-4">经验洞察 ({{ pattern.learned_from_data.length }})</div>
        <div class="space-y-3">
          <div v-for="(item, idx) in pattern.learned_from_data" :key="idx" class="bg-surface-2 rounded-lg p-3 space-y-1.5">
            <div class="flex items-center justify-between">
              <div class="text-xs text-gray-500">{{ item.context }}</div>
              <div class="text-[10px] px-2 py-0.5 rounded" :class="item.confidence >= 70 ? 'bg-emerald-500/20 text-emerald-400' : item.confidence >= 40 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'">{{ item.confidence }}%</div>
            </div>
            <div class="text-xs text-gray-300">{{ item.insight }}</div>
          </div>
        </div>
      </div>

      <!-- 置信度演化曲线 -->
      <div v-if="pattern.evolution.length > 1" class="bg-surface-1 rounded-xl border border-surface-3 p-6">
        <div class="flex items-center justify-between mb-4">
          <div class="text-sm font-medium text-gray-300">置信度演化曲线</div>
          <div class="flex items-baseline gap-1">
            <span class="text-3xl font-bold" :class="confidenceColor(finalConfidence)">{{ finalConfidence }}</span>
            <span class="text-xs text-gray-500">%</span>
          </div>
        </div>
        <div class="overflow-x-auto">
          <svg :viewBox="`0 0 ${chartWidth} ${chartHeight}`" :width="chartWidth" :height="chartHeight" class="w-full" preserveAspectRatio="xMidYMid meet">
            <defs>
              <!-- 线条渐变: 红到绿 -->
              <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#ef4444" />
                <stop offset="50%" stop-color="#eab308" />
                <stop offset="100%" stop-color="#22c55e" />
              </linearGradient>
              <!-- 填充渐变: 半透明 -->
              <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#22c55e" stop-opacity="0.25" />
                <stop offset="100%" stop-color="#22c55e" stop-opacity="0.02" />
              </linearGradient>
            </defs>
            <!-- 网格线 -->
            <template v-for="line in gridLines" :key="line.label">
              <line :x1="line.x1" :y1="line.y" :x2="line.x2" :y2="line.y" stroke="#374151" stroke-width="0.5" stroke-dasharray="4 3" />
              <text :x="line.x1 - 4" :y="line.y + 3" text-anchor="end" fill="#6b7280" font-size="10">{{ line.label }}</text>
            </template>
            <!-- 底部基线 -->
            <line :x1="chartPadding.left" :y1="chartPadding.top + chartInnerHeight" :x2="chartWidth - chartPadding.right" :y2="chartPadding.top + chartInnerHeight" stroke="#374151" stroke-width="0.5" />
            <!-- 填充区域 -->
            <path :d="areaPath" fill="url(#areaGradient)" />
            <!-- 曲线 -->
            <path :d="linePath" fill="none" stroke="url(#lineGradient)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            <!-- 数据点 + 标签 -->
            <template v-for="(pt, idx) in svgPoints" :key="idx">
              <circle :cx="pt.x" :cy="pt.y" r="4" fill="#1e1e2e" stroke="url(#lineGradient)" stroke-width="2" />
              <circle :cx="pt.x" :cy="pt.y" r="2" fill="#22c55e" />
              <!-- 置信度数值 -->
              <text :x="pt.x" :y="pt.y - 10" text-anchor="middle" fill="#d1d5db" font-size="10" font-weight="500">{{ pt.confidence }}%</text>
              <!-- 日期 -->
              <text :x="pt.x" :y="chartPadding.top + chartInnerHeight + 16" text-anchor="middle" fill="#6b7280" font-size="9">{{ pt.date }}</text>
            </template>
          </svg>
        </div>
      </div>

      <!-- 学习过程时间线 -->
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-6">
        <div class="text-sm font-medium text-gray-300 mb-5">学习过程</div>
        <div class="relative pl-6">
          <!-- 垂直连接线 -->
          <div class="absolute left-[7px] top-2 bottom-2 w-0.5 bg-gradient-to-b from-red-500 via-yellow-500 to-emerald-500 rounded-full" />
          <!-- 时间线节点 -->
          <div v-for="(snap, idx) in pattern.evolution" :key="idx" class="relative pb-5 last:pb-0">
            <!-- 节点圆点 -->
            <div class="absolute -left-6 top-0.5 w-3.5 h-3.5 rounded-full border-2 border-surface-1" :class="confidenceBg(snap.confidence)" />
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="text-xs text-gray-300">{{ snap.event_description }}</div>
                <div class="text-[10px] text-gray-500 mt-0.5">{{ snap.date }}</div>
              </div>
              <div class="shrink-0 text-sm font-medium" :class="confidenceColor(snap.confidence)">{{ snap.confidence }}%</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 子规则列表 -->
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-6">
        <div class="text-sm font-medium text-gray-300 mb-4">子规则 ({{ pattern.rules.length }})</div>
        <div class="grid grid-cols-1 gap-3">
          <div v-for="rule in pattern.rules" :key="rule.id" class="bg-surface-2 rounded-lg p-4 space-y-2">
            <div class="text-sm font-medium text-gray-200">{{ rule.name }}</div>
            <div class="text-xs text-gray-400">{{ rule.description }}</div>
            <div class="grid grid-cols-2 gap-3 mt-2">
              <div>
                <div class="text-[10px] text-gray-500 mb-0.5">触发条件</div>
                <div class="text-xs text-gray-300 font-mono bg-surface-3 rounded px-2 py-1">{{ rule.trigger }}</div>
              </div>
              <div>
                <div class="text-[10px] text-gray-500 mb-0.5">执行动作</div>
                <div class="text-xs text-gray-300 font-mono bg-surface-3 rounded px-2 py-1">{{ rule.action }}</div>
              </div>
            </div>
            <div>
              <div class="text-[10px] text-gray-500 mb-0.5">示例</div>
              <div class="text-xs text-gray-400 italic">{{ rule.example }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 执行日志 -->
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-6">
        <div class="text-sm font-medium text-gray-300 mb-4">执行日志 ({{ pattern.executions.length }})</div>
        <div class="space-y-2">
          <div v-for="exec in pattern.executions" :key="exec.id" class="bg-surface-2 rounded-lg p-3 flex items-center gap-4">
            <div class="text-[10px] text-gray-500 shrink-0 w-32">{{ formatTime(exec.timestamp) }}</div>
            <div class="flex-1 min-w-0">
              <div class="text-xs text-gray-300 truncate">{{ exec.trigger_event }}</div>
              <div class="text-[10px] text-gray-500 mt-0.5 truncate">{{ exec.action_taken }}</div>
            </div>
            <span class="text-[10px] px-2 py-0.5 rounded shrink-0" :class="resultColorMap[exec.result]">{{ resultLabel[exec.result] }}</span>
          </div>
        </div>
      </div>

      <!-- 适用场景 -->
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-6">
        <div class="text-sm font-medium text-gray-300 mb-3">适用场景</div>
        <div class="flex flex-wrap gap-2">
          <span v-for="scenario in pattern.applicable_scenarios" :key="scenario" class="text-xs px-3 py-1 rounded-full bg-surface-3 text-gray-400 border border-surface-3">
            {{ scenario }}
          </span>
        </div>
      </div>

      <!-- 底部操作按钮 -->
      <div class="flex items-center gap-3">
        <button class="px-4 py-2 rounded-lg text-xs font-medium bg-accent/20 text-accent hover:bg-accent/30 transition-colors cursor-pointer">
          编辑规则
        </button>
        <button class="px-4 py-2 rounded-lg text-xs font-medium bg-openclaw/20 text-openclaw hover:bg-openclaw/30 transition-colors cursor-pointer">
          重新计算置信度
        </button>
        <button class="px-4 py-2 rounded-lg text-xs font-medium bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors cursor-pointer">
          导出
        </button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import { useEventsStore } from '@/stores/events'
import { useSkillsStore } from '@/stores/skills'
import { mockStats, mockPatterns } from '@/mock/data'

const eventsStore = useEventsStore()
const skillsStore = useSkillsStore()

const now = Math.floor(Date.now() / 1000)
const DAY = 86400

// 开发者类型分析
const devType = computed(() => {
  const counts = { research: 0, engineering: 0, ops: 0 }
  for (const e of eventsStore.events) {
    if (e.source === 'openclaw' || e.tags.some(t => ['paper', 'experiment', 'learning'].includes(t))) counts.research++
    else if (e.source === 'git' || e.source === 'claude_code' || e.tags.some(t => ['feature', 'bugfix', 'refactor'].includes(t))) counts.engineering++
    else counts.ops++
  }
  const total = counts.research + counts.engineering + counts.ops
  return {
    research: Math.round(counts.research / total * 100),
    engineering: Math.round(counts.engineering / total * 100),
    ops: Math.round(counts.ops / total * 100),
    primary: counts.research >= counts.engineering && counts.research >= counts.ops ? '研究型'
      : counts.engineering >= counts.ops ? '工程型' : '运维型',
  }
})

// AI 依赖度
const aiDependency = computed(() => {
  const ocEvents = eventsStore.events.filter(e => e.source === 'openclaw' || e.source === 'claude_code').length
  return Math.round(ocEvents / eventsStore.events.length * 100)
})

// 工作节奏分析
const workRhythm = computed(() => {
  const hourCounts = new Array(24).fill(0)
  for (const e of eventsStore.events) {
    const h = new Date(e.timestamp * 1000).getHours()
    hourCounts[h]++
  }
  const maxHour = hourCounts.indexOf(Math.max(...hourCounts))
  const morningEvents = hourCounts.slice(6, 12).reduce((a, b) => a + b, 0)
  const nightEvents = hourCounts.slice(20, 24).reduce((a, b) => a + b, 0) + hourCounts.slice(0, 4).reduce((a, b) => a + b, 0)
  const type = morningEvents > nightEvents ? '早鸟型' : '夜猫子型'

  // 集中度分析
  const sorted = [...hourCounts].sort((a, b) => b - a)
  const top4 = sorted.slice(0, 4).reduce((a, b) => a + b, 0)
  const total = hourCounts.reduce((a, b) => a + b, 0)
  const concentration = Math.round(top4 / total * 100)
  const style = concentration > 60 ? '集中爆发' : '均匀分布'

  return { hourCounts, maxHour, type, style, concentration }
})

// 核心技能雷达图数据
const radarSkills = computed(() => {
  const categories = ['language', 'framework', 'devops', 'vcs', 'tool', 'openclaw']
  const labels = ['编程语言', '框架', '运维', '版本控制', '工具', 'AI']
  return categories.map((cat, i) => {
    const skills = skillsStore.skills.filter(s => s.category === cat)
    const avgLevel = skills.length ? Math.round(skills.reduce((a, b) => a + b.level, 0) / skills.length) : 0
    return { category: cat, label: labels[i], level: avgLevel }
  })
})

// 周对比数据
const weekComparison = computed(() => {
  const thisWeek = eventsStore.events.filter(e => e.timestamp > now - 7 * DAY)
  const lastWeek = eventsStore.events.filter(e => e.timestamp > now - 14 * DAY && e.timestamp <= now - 7 * DAY)
  const thisAI = thisWeek.filter(e => e.source === 'openclaw' || e.source === 'claude_code').length
  const lastAI = lastWeek.filter(e => e.source === 'openclaw' || e.source === 'claude_code').length
  const calcDelta = (a: number, b: number) => b === 0 ? 100 : Math.round((a - b) / b * 100)
  return {
    thisEvents: thisWeek.length,
    lastEvents: lastWeek.length,
    eventsDelta: calcDelta(thisWeek.length, lastWeek.length),
    thisAI,
    lastAI,
    aiDelta: calcDelta(thisAI, lastAI),
  }
})
</script>

<template>
  <div class="p-6 space-y-6 overflow-y-auto h-full">
    <div>
      <h1 class="text-2xl font-semibold">开发者画像</h1>
      <p class="text-sm text-gray-400 mt-1">你的 AI 开发者数字孪生名片</p>
    </div>

    <!-- 名片卡 -->
    <div class="bg-surface-1 rounded-2xl border border-surface-3 p-6 gradient-border">
      <div class="flex items-start gap-6">
        <!-- 头像区 -->
        <div class="relative">
          <div class="w-20 h-20 rounded-2xl bg-accent/20 flex items-center justify-center">
            <span class="text-3xl font-bold text-accent">LY</span>
          </div>
          <div class="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-emerald-500 border-2 border-surface-1" />
        </div>
        <!-- 基本信息 -->
        <div class="flex-1">
          <div class="text-xl font-semibold">李宇峰</div>
          <div class="text-sm text-gray-400 mt-0.5">具身智能方向 博士研究生</div>
          <div class="flex items-center gap-3 mt-3">
            <span class="text-xs px-2.5 py-1 rounded-full bg-accent/15 text-accent">{{ devType.primary }}</span>
            <span class="text-xs px-2.5 py-1 rounded-full bg-openclaw/15 text-openclaw">AI 依赖度 {{ aiDependency }}%</span>
            <span class="text-xs px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-400">连续活跃 {{ mockStats.streak_days }} 天</span>
          </div>
        </div>
        <!-- 统计 -->
        <div class="flex gap-6 text-center">
          <div>
            <div class="text-2xl font-bold">{{ mockStats.total_events.toLocaleString() }}</div>
            <div class="text-[10px] text-gray-500 mt-0.5">总事件</div>
          </div>
          <div>
            <div class="text-2xl font-bold text-openclaw">{{ mockStats.total_openclaw_sessions }}</div>
            <div class="text-[10px] text-gray-500 mt-0.5">AI 交互</div>
          </div>
          <div>
            <div class="text-2xl font-bold">{{ mockStats.total_skills }}</div>
            <div class="text-[10px] text-gray-500 mt-0.5">技能</div>
          </div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-3 gap-4">
      <!-- 开发者类型 -->
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
        <div class="text-sm font-medium mb-4">开发者类型</div>
        <div class="space-y-3">
          <div class="flex items-center gap-3">
            <span class="text-xs text-gray-400 w-14">研究型</span>
            <div class="flex-1 h-2.5 bg-surface-3 rounded-full overflow-hidden">
              <div class="h-full bg-purple-500 rounded-full transition-all" :style="{ width: `${devType.research}%` }" />
            </div>
            <span class="text-xs text-gray-400 w-10 text-right">{{ devType.research }}%</span>
          </div>
          <div class="flex items-center gap-3">
            <span class="text-xs text-gray-400 w-14">工程型</span>
            <div class="flex-1 h-2.5 bg-surface-3 rounded-full overflow-hidden">
              <div class="h-full bg-accent rounded-full transition-all" :style="{ width: `${devType.engineering}%` }" />
            </div>
            <span class="text-xs text-gray-400 w-10 text-right">{{ devType.engineering }}%</span>
          </div>
          <div class="flex items-center gap-3">
            <span class="text-xs text-gray-400 w-14">运维型</span>
            <div class="flex-1 h-2.5 bg-surface-3 rounded-full overflow-hidden">
              <div class="h-full bg-terminal rounded-full transition-all" :style="{ width: `${devType.ops}%` }" />
            </div>
            <span class="text-xs text-gray-400 w-10 text-right">{{ devType.ops }}%</span>
          </div>
        </div>
      </div>

      <!-- 工作节奏 -->
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
        <div class="text-sm font-medium mb-4">工作节奏</div>
        <div class="flex items-center gap-2 mb-3">
          <span class="text-xs px-2 py-0.5 rounded-full bg-openclaw/15 text-openclaw">{{ workRhythm.type }}</span>
          <span class="text-xs px-2 py-0.5 rounded-full bg-accent/15 text-accent">{{ workRhythm.style }}</span>
        </div>
        <!-- 24h 活跃度条形图 -->
        <div class="flex items-end gap-px h-16">
          <div
            v-for="(count, hour) in workRhythm.hourCounts"
            :key="hour"
            class="flex-1 rounded-t-sm transition-all"
            :class="hour === workRhythm.maxHour ? 'bg-accent' : count > 0 ? 'bg-accent/40' : 'bg-surface-3/50'"
            :style="{ height: `${Math.max(count / Math.max(...workRhythm.hourCounts) * 100, 2)}%` }"
          />
        </div>
        <div class="flex justify-between mt-1">
          <span class="text-[9px] text-gray-600">0h</span>
          <span class="text-[9px] text-gray-600">6h</span>
          <span class="text-[9px] text-gray-600">12h</span>
          <span class="text-[9px] text-gray-600">18h</span>
          <span class="text-[9px] text-gray-600">24h</span>
        </div>
        <div class="text-[10px] text-gray-500 mt-2">高峰时段: {{ workRhythm.maxHour }}:00 · 集中度 {{ workRhythm.concentration }}%</div>
      </div>

      <!-- 技能雷达图 -->
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
        <div class="text-sm font-medium mb-4">核心技能雷达</div>
        <div class="flex justify-center">
          <svg viewBox="0 0 200 200" class="w-40 h-40">
            <!-- 背景网格 -->
            <polygon v-for="level in [20, 40, 60, 80, 100]" :key="level"
              :points="radarSkills.map((_, i) => {
                const angle = (Math.PI * 2 * i / radarSkills.length) - Math.PI / 2
                const r = level * 0.8
                return `${100 + r * Math.cos(angle)},${100 + r * Math.sin(angle)}`
              }).join(' ')"
              fill="none" stroke="#242438" stroke-width="0.5"
            />
            <!-- 数据区域 -->
            <polygon
              :points="radarSkills.map((s, i) => {
                const angle = (Math.PI * 2 * i / radarSkills.length) - Math.PI / 2
                const r = s.level * 0.8
                return `${100 + r * Math.cos(angle)},${100 + r * Math.sin(angle)}`
              }).join(' ')"
              fill="rgba(124, 92, 252, 0.15)" stroke="#7c5cfc" stroke-width="1.5"
            />
            <!-- 标签 -->
            <text v-for="(s, i) in radarSkills" :key="s.category"
              :x="100 + 90 * Math.cos((Math.PI * 2 * i / radarSkills.length) - Math.PI / 2)"
              :y="100 + 90 * Math.sin((Math.PI * 2 * i / radarSkills.length) - Math.PI / 2)"
              text-anchor="middle" dominant-baseline="middle"
              fill="#9ca3af" font-size="9"
            >{{ s.label }}</text>
          </svg>
        </div>
      </div>
    </div>

    <!-- 周对比 -->
    <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
      <div class="text-sm font-medium mb-4">本周 vs 上周</div>
      <div class="grid grid-cols-2 gap-6">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-xs text-gray-400">总事件数</div>
            <div class="text-2xl font-bold mt-1">{{ weekComparison.thisEvents }}</div>
            <div class="text-xs text-gray-500">上周 {{ weekComparison.lastEvents }}</div>
          </div>
          <div class="text-right">
            <span class="text-lg font-bold" :class="weekComparison.eventsDelta >= 0 ? 'text-emerald-400' : 'text-red-400'">
              {{ weekComparison.eventsDelta >= 0 ? '+' : '' }}{{ weekComparison.eventsDelta }}%
            </span>
            <div class="text-[10px] text-gray-500 mt-0.5">变化率</div>
          </div>
        </div>
        <div class="flex items-center justify-between">
          <div>
            <div class="text-xs text-openclaw">AI 交互次数</div>
            <div class="text-2xl font-bold mt-1 text-openclaw">{{ weekComparison.thisAI }}</div>
            <div class="text-xs text-gray-500">上周 {{ weekComparison.lastAI }}</div>
          </div>
          <div class="text-right">
            <span class="text-lg font-bold" :class="weekComparison.aiDelta >= 0 ? 'text-emerald-400' : 'text-red-400'">
              {{ weekComparison.aiDelta >= 0 ? '+' : '' }}{{ weekComparison.aiDelta }}%
            </span>
            <div class="text-[10px] text-gray-500 mt-0.5">变化率</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 核心行为模式 -->
    <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
      <div class="text-sm font-medium mb-4">核心行为模式</div>
      <div class="grid grid-cols-2 gap-3">
        <div v-for="p in mockPatterns.filter(p => p.confidence >= 70).slice(0, 6)" :key="p.id"
          class="bg-surface-2 rounded-lg p-3 border border-surface-3"
        >
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-xs text-gray-200">{{ p.name }}</span>
            <span class="text-[10px] text-gray-500">{{ p.confidence }}%</span>
          </div>
          <div class="h-1.5 bg-surface-3 rounded-full overflow-hidden">
            <div class="h-full rounded-full" :class="p.confidence >= 85 ? 'bg-emerald-500' : 'bg-accent'" :style="{ width: `${p.confidence}%` }" />
          </div>
          <div class="text-[10px] text-gray-500 mt-1.5">{{ p.description.slice(0, 40) }}...</div>
        </div>
      </div>
    </div>
  </div>
</template>

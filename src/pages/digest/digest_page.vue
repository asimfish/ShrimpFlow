<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import type { BehaviorPattern } from '@/types'
import { useEventsStore } from '@/stores/events'
import { useDigestStore } from '@/stores/digest'
import { useOpenClawStore } from '@/stores/openclaw'
import { useSkillsStore } from '@/stores/skills'
import { getPatternsApi } from '@/http_api/patterns'
import { dayjs } from '@/libs/dayjs'

const router = useRouter()
const eventsStore = useEventsStore()
const digestStore = useDigestStore()
const openclawStore = useOpenClawStore()
const skillsStore = useSkillsStore()

const patterns = ref<BehaviorPattern[]>([])

onMounted(async () => {
  const pRes = await getPatternsApi()
  if (pRes.data) patterns.value = pRes.data
})

const DAY = 86400

// 视图模式
const viewMode = ref<'daily' | 'weekly' | 'monthly'>('daily')
const currentMonth = ref(dayjs())
const selectedDate = ref('')

const monthLabel = computed(() => currentMonth.value.format('YYYY年 M月'))
const prevMonth = () => { currentMonth.value = currentMonth.value.subtract(1, 'month') }
const nextMonth = () => { currentMonth.value = currentMonth.value.add(1, 'month') }

// 按来源主导色着色
const getDominantSource = (events: any[]) => {
  if (!events?.length) return ''
  const counts: Record<string, number> = {}
  events.forEach(e => { counts[e.source] = (counts[e.source] ?? 0) + 1 })
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0]
}

const heatColorBySource: Record<string, string[]> = {
  openclaw: ['bg-openclaw/15', 'bg-openclaw/30', 'bg-openclaw/50', 'bg-openclaw/70'],
  terminal: ['bg-terminal/15', 'bg-terminal/30', 'bg-terminal/50', 'bg-terminal/70'],
  git: ['bg-git/15', 'bg-git/30', 'bg-git/50', 'bg-git/70'],
  claude_code: ['bg-claude/15', 'bg-claude/30', 'bg-claude/50', 'bg-claude/70'],
  env: ['bg-env/15', 'bg-env/30', 'bg-env/50', 'bg-env/70'],
}

const heatColor = (count: number, source: string) => {
  if (count === 0) return 'bg-surface-3/30'
  const colors = heatColorBySource[source]
  if (!colors) return 'bg-accent/20'
  if (count < 10) return colors[0]
  if (count < 25) return colors[1]
  if (count < 40) return colors[2]
  return colors[3]
}

// 日历网格
const calendarDays = computed(() => {
  const start = currentMonth.value.startOf('month')
  const end = currentMonth.value.endOf('month')
  const startDay = start.day()
  const days: { date: string; day: number; inMonth: boolean; eventCount: number; dominantSource: string }[] = []
  for (let i = 0; i < startDay; i++) {
    const d = start.subtract(startDay - i, 'day')
    days.push({ date: d.format('YYYY-MM-DD'), day: d.date(), inMonth: false, eventCount: 0, dominantSource: '' })
  }
  for (let d = start; d.isBefore(end) || d.isSame(end, 'day'); d = d.add(1, 'day')) {
    const dateStr = d.format('YYYY-MM-DD')
    const events = eventsStore.eventsByDate.get(dateStr)
    const dominantSource = getDominantSource(events ?? [])
    days.push({ date: dateStr, day: d.date(), inMonth: true, eventCount: events?.length ?? 0, dominantSource })
  }
  const remaining = 42 - days.length
  for (let i = 1; i <= remaining; i++) {
    const d = end.add(i, 'day')
    days.push({ date: d.format('YYYY-MM-DD'), day: d.date(), inMonth: false, eventCount: 0, dominantSource: '' })
  }
  return days
})

const selectDay = (date: string) => { selectedDate.value = date; digestStore.selectedDate = date }
const selectedSummary = computed(() => digestStore.getSummary(selectedDate.value))
const selectedDayEvents = computed(() => selectedDate.value ? (eventsStore.eventsByDate.get(selectedDate.value) ?? []) : [])
const selectedSourceCounts = computed(() => {
  const counts: Record<string, number> = {}
  for (const e of selectedDayEvents.value) { counts[e.source] = (counts[e.source] ?? 0) + 1 }
  return Object.entries(counts).sort((a, b) => b[1] - a[1])
})

const sourceColorMap: Record<string, string> = { openclaw: 'bg-openclaw', terminal: 'bg-terminal', git: 'bg-git', claude_code: 'bg-claude', env: 'bg-env' }
const sourceNameMap: Record<string, string> = { openclaw: 'OpenClaw', terminal: '终端', git: 'Git', claude_code: 'Claude Code', env: '环境' }
const weekDays = ['日', '一', '二', '三', '四', '五', '六']

const selectedDayOpenClawSessions = computed(() => {
  if (!selectedDate.value) return []
  const dayOC = selectedDayEvents.value.filter(e => e.source === 'openclaw' && e.openclaw_session_id)
  const ids = [...new Set(dayOC.map(e => e.openclaw_session_id))]
  return ids.map(id => openclawStore.sessions.find(s => s.id === id)).filter(Boolean)
})

const dailyPatternProgress = computed(() => {
  if (!selectedDate.value) return []
  return patterns.value.filter(p => p.evolution.some(e => e.date === `${selectedDate.value.slice(5, 7)}-${selectedDate.value.slice(8, 10)}`))
    .map(p => {
      const key = `${selectedDate.value.slice(5, 7)}-${selectedDate.value.slice(8, 10)}`
      const snap = p.evolution.find(e => e.date === key)!
      const idx = p.evolution.indexOf(snap)
      const prev = idx > 0 ? p.evolution[idx - 1].confidence : 0
      return { name: p.name, before: prev, after: snap.confidence, delta: snap.confidence - prev }
    })
})

const dailyGitStats = computed(() => {
  const gitEvents = selectedDayEvents.value.filter(e => e.source === 'git')
  const projects = new Set(gitEvents.map(e => e.project))
  return { commits: gitEvents.length, projects: projects.size, projectNames: [...projects] }
})

// ===== 周报数据 =====
const currentWeekStart = computed(() => dayjs().startOf('week'))
const weekEvents = computed(() => {
  const start = currentWeekStart.value.unix()
  const end = start + 7 * DAY
  return eventsStore.events.filter(e => e.timestamp >= start && e.timestamp < end)
})
const lastWeekEvents = computed(() => {
  const start = currentWeekStart.value.unix() - 7 * DAY
  const end = currentWeekStart.value.unix()
  return eventsStore.events.filter(e => e.timestamp >= start && e.timestamp < end)
})

const weeklyStats = computed(() => {
  const thisAI = weekEvents.value.filter(e => e.source === 'openclaw' || e.source === 'claude_code').length
  const lastAI = lastWeekEvents.value.filter(e => e.source === 'openclaw' || e.source === 'claude_code').length
  const thisGit = weekEvents.value.filter(e => e.source === 'git').length
  const lastGit = lastWeekEvents.value.filter(e => e.source === 'git').length
  const delta = (a: number, b: number) => b === 0 ? (a > 0 ? 100 : 0) : Math.round((a - b) / b * 100)
  return {
    total: weekEvents.value.length, lastTotal: lastWeekEvents.value.length,
    totalDelta: delta(weekEvents.value.length, lastWeekEvents.value.length),
    ai: thisAI, lastAI, aiDelta: delta(thisAI, lastAI),
    git: thisGit, lastGit, gitDelta: delta(thisGit, lastGit),
  }
})

// 周每日事件趋势
const weekDailyTrend = computed(() => {
  const labels = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return labels.map((label, i) => {
    const dayStart = currentWeekStart.value.add(i, 'day').unix()
    const dayEnd = dayStart + DAY
    const count = eventsStore.events.filter(e => e.timestamp >= dayStart && e.timestamp < dayEnd).length
    return { label, count }
  })
})

// 周来源分布
const weekSourceDist = computed(() => {
  const counts: Record<string, number> = { openclaw: 0, terminal: 0, git: 0, claude_code: 0, env: 0 }
  weekEvents.value.forEach(e => { counts[e.source]++ })
  return counts
})

// ===== 月报数据 =====
const monthEvents = computed(() => {
  const start = currentMonth.value.startOf('month').unix()
  const end = currentMonth.value.endOf('month').unix()
  return eventsStore.events.filter(e => e.timestamp >= start && e.timestamp <= end)
})

const monthlyStats = computed(() => {
  const ai = monthEvents.value.filter(e => e.source === 'openclaw' || e.source === 'claude_code').length
  const git = monthEvents.value.filter(e => e.source === 'git').length
  const projects = new Set(monthEvents.value.map(e => e.project))
  const activeDays = new Set(monthEvents.value.map(e => {
    const d = new Date(e.timestamp * 1000)
    return `${d.getMonth()}-${d.getDate()}`
  }))
  return { total: monthEvents.value.length, ai, git, projects: projects.size, activeDays: activeDays.size }
})

// 月每周趋势
const monthWeeklyTrend = computed(() => {
  const start = currentMonth.value.startOf('month')
  const weeks: { label: string; count: number }[] = []
  for (let w = 0; w < 5; w++) {
    const wStart = start.add(w * 7, 'day').unix()
    const wEnd = wStart + 7 * DAY
    const count = monthEvents.value.filter(e => e.timestamp >= wStart && e.timestamp < wEnd).length
    weeks.push({ label: `第${w + 1}周`, count })
  }
  return weeks
})

// 月来源趋势（按周）
const monthSourceTrend = computed(() => {
  const start = currentMonth.value.startOf('month')
  const sources = ['openclaw', 'terminal', 'git', 'claude_code', 'env'] as const
  return sources.map(s => {
    const weeks = Array.from({ length: 5 }, (_, w) => {
      const wStart = start.add(w * 7, 'day').unix()
      const wEnd = wStart + 7 * DAY
      return monthEvents.value.filter(e => e.source === s && e.timestamp >= wStart && e.timestamp < wEnd).length
    })
    return { source: s, weeks }
  })
})

// 月技能成长
const monthSkillGrowth = computed(() =>
  [...skillsStore.skills].sort((a, b) => b.level - a.level).slice(0, 8)
)
</script>

<template>
  <div class="p-6 h-full overflow-y-auto">
    <!-- Header + Tabs -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-semibold">开发报告</h1>
        <p class="text-sm text-gray-400 mt-1">回顾你的 OpenClaw 开发旅程</p>
      </div>
      <div class="flex items-center bg-surface-2 rounded-lg border border-surface-3 overflow-hidden">
        <button v-for="m in [{ v: 'daily', l: '日报' }, { v: 'weekly', l: '周报' }, { v: 'monthly', l: '月报' }]" :key="m.v"
          @click="viewMode = m.v as any"
          class="px-4 py-2 text-xs transition-colors"
          :class="viewMode === m.v ? 'bg-accent text-white' : 'text-gray-400 hover:text-white'"
        >{{ m.l }}</button>
      </div>
    </div>

    <!-- ===== 日报视图 ===== -->
    <div v-if="viewMode === 'daily'" class="flex gap-6">
      <div class="flex-1 space-y-4">
        <div class="flex items-center gap-4">
          <button @click="prevMonth" class="px-3 py-1.5 rounded-lg bg-surface-2 hover:bg-surface-3 text-sm transition">&lt;</button>
          <span class="text-sm font-medium w-32 text-center">{{ monthLabel }}</span>
          <button @click="nextMonth" class="px-3 py-1.5 rounded-lg bg-surface-2 hover:bg-surface-3 text-sm transition">&gt;</button>
        </div>
        <div class="bg-surface-1 rounded-xl border border-surface-3 p-4">
          <div class="grid grid-cols-7 gap-1 mb-2">
            <div v-for="d in weekDays" :key="d" class="text-center text-xs text-gray-500 py-1">{{ d }}</div>
          </div>
          <div class="grid grid-cols-7 gap-1">
            <button v-for="day in calendarDays" :key="day.date" @click="day.inMonth && selectDay(day.date)"
              class="aspect-square rounded-lg flex flex-col items-center justify-center text-xs transition-all relative"
              :class="[
                day.inMonth ? 'hover:ring-1 hover:ring-accent/50 cursor-pointer' : 'opacity-20 cursor-default',
                selectedDate === day.date ? 'ring-2 ring-accent bg-accent/10' : '',
                heatColor(day.eventCount, day.dominantSource),
              ]"
            >
              <span :class="day.inMonth ? 'text-gray-300' : 'text-gray-600'">{{ day.day }}</span>
              <span v-if="day.eventCount > 0 && day.inMonth" class="text-[9px] text-gray-500 mt-0.5">{{ day.eventCount }}</span>
            </button>
          </div>
        </div>
        <div class="flex items-center gap-3 text-xs text-gray-500">
          <span>来源色:</span>
          <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded bg-openclaw/50" /> OpenClaw</span>
          <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded bg-terminal/50" /> 终端</span>
          <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded bg-git/50" /> Git</span>
          <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded bg-claude/50" /> Claude</span>
        </div>
      </div>

      <!-- 日报右侧详情 -->
      <div class="w-96 shrink-0 overflow-y-auto max-h-[calc(100vh-120px)]">
        <div v-if="!selectedDate" class="h-full flex items-center justify-center">
          <div class="text-center text-gray-500">
            <div class="text-4xl mb-3 opacity-30">&#9776;</div>
            <div class="text-sm">选择一天查看详情</div>
          </div>
        </div>
        <div v-else class="space-y-4">
          <div class="flex items-center justify-between">
            <div class="text-sm font-medium text-gray-400">{{ dayjs(selectedDate).format('YYYY年 M月 D日 dddd') }}</div>
            <button class="text-[10px] text-accent hover:text-accent/80 transition-colors" @click="router.push('/timeline')">在时间线中查看</button>
          </div>
          <div class="bg-surface-1 rounded-xl border border-surface-3 p-4">
            <div class="text-xs text-openclaw mb-2">OpenClaw AI 摘要</div>
            <p class="text-sm text-gray-300 leading-relaxed">{{ selectedSummary?.ai_summary ?? '当天无数据' }}</p>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="bg-surface-1 rounded-xl border border-surface-3 p-3">
              <div class="text-xs text-gray-400">事件数</div>
              <div class="text-xl font-bold mt-1">{{ selectedSummary?.event_count ?? 0 }}</div>
            </div>
            <div class="bg-surface-1 rounded-xl border border-surface-3 p-3">
              <div class="text-xs text-openclaw">OpenClaw</div>
              <div class="text-xl font-bold mt-1 text-openclaw">{{ selectedSummary?.openclaw_sessions ?? 0 }}</div>
            </div>
          </div>
          <!-- 来源分布 -->
          <div class="bg-surface-1 rounded-xl border border-surface-3 p-4">
            <div class="text-xs text-gray-400 mb-3">来源分布</div>
            <div class="space-y-2">
              <div v-for="[source, count] in selectedSourceCounts" :key="source" class="flex items-center gap-2">
                <div class="w-2 h-2 rounded-full" :class="sourceColorMap[source]" />
                <span class="text-xs text-gray-400 w-20">{{ sourceNameMap[source] ?? source }}</span>
                <div class="flex-1 h-1.5 bg-surface-3 rounded-full overflow-hidden">
                  <div class="h-full rounded-full" :class="sourceColorMap[source]" :style="{ width: `${(count / selectedDayEvents.length) * 100}%` }" />
                </div>
                <span class="text-xs text-gray-500 w-6 text-right">{{ count }}</span>
              </div>
            </div>
          </div>
          <div v-if="selectedSummary?.top_projects?.length" class="bg-surface-1 rounded-xl border border-surface-3 p-4">
            <div class="text-xs text-gray-400 mb-3">热门项目</div>
            <div class="space-y-1.5">
              <div v-for="p in selectedSummary.top_projects" :key="p.name" class="flex items-center justify-between">
                <span class="text-xs font-mono text-gray-300">{{ p.name }}</span>
                <span class="text-xs text-gray-500">{{ p.count }} 个事件</span>
              </div>
            </div>
          </div>
          <div v-if="selectedDayOpenClawSessions.length" class="bg-surface-1 rounded-xl border border-openclaw/20 p-4">
            <div class="text-xs text-openclaw mb-3">当日 OpenClaw 对话</div>
            <div class="space-y-2">
              <button v-for="session in selectedDayOpenClawSessions" :key="session!.id"
                class="w-full text-left bg-surface-2 rounded-lg p-2.5 hover:bg-surface-3/50 transition-colors cursor-pointer"
                @click="openclawStore.selectSession(session!.id); router.push('/openclaw')"
              >
                <div class="text-xs text-gray-200 truncate">{{ session!.title }}</div>
                <div class="text-[10px] text-gray-500 mt-0.5">{{ session!.messages.length }} 条消息 · {{ session!.project }}</div>
              </button>
            </div>
          </div>
          <div v-if="dailyPatternProgress.length" class="bg-surface-1 rounded-xl border border-purple-500/20 p-4">
            <div class="text-xs text-purple-400 mb-3">当日行为模式学习进度</div>
            <div class="space-y-2.5">
              <div v-for="p in dailyPatternProgress" :key="p.name" class="space-y-1">
                <div class="flex items-center justify-between">
                  <span class="text-xs text-gray-300">{{ p.name }}</span>
                  <span class="text-[10px]" :class="p.delta > 0 ? 'text-emerald-400' : 'text-gray-500'">{{ p.delta > 0 ? '+' : '' }}{{ p.delta }}%</span>
                </div>
                <div class="flex items-center gap-2">
                  <div class="flex-1 h-1.5 bg-surface-3 rounded-full overflow-hidden relative">
                    <div class="h-full rounded-full bg-gray-600 absolute" :style="{ width: `${p.before}%` }" />
                    <div class="h-full rounded-full bg-purple-500 absolute" :style="{ width: `${p.after}%` }" />
                  </div>
                  <span class="text-[10px] text-gray-500 w-16 text-right">{{ p.before }}% → {{ p.after }}%</span>
                </div>
              </div>
            </div>
          </div>
          <div v-if="dailyGitStats.commits > 0" class="bg-surface-1 rounded-xl border border-git/20 p-4">
            <div class="text-xs text-git mb-3">当日代码提交</div>
            <div class="grid grid-cols-2 gap-3">
              <div class="bg-surface-2 rounded-lg p-2.5">
                <div class="text-xs text-gray-400">提交数</div>
                <div class="text-lg font-bold text-git mt-0.5">{{ dailyGitStats.commits }}</div>
              </div>
              <div class="bg-surface-2 rounded-lg p-2.5">
                <div class="text-xs text-gray-400">涉及项目</div>
                <div class="text-lg font-bold mt-0.5">{{ dailyGitStats.projects }}</div>
              </div>
            </div>
            <div class="flex flex-wrap gap-1 mt-2">
              <span v-for="name in dailyGitStats.projectNames" :key="name" class="text-[10px] px-1.5 py-0.5 rounded-full bg-git/10 text-git/80">{{ name }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 周报视图 ===== -->
    <div v-if="viewMode === 'weekly'" class="space-y-6">
      <div class="text-sm text-gray-400">{{ currentWeekStart.format('M月D日') }} - {{ currentWeekStart.add(6, 'day').format('M月D日') }}</div>

      <!-- 周统计卡片 -->
      <div class="grid grid-cols-3 gap-4">
        <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
          <div class="text-xs text-gray-400">本周总事件</div>
          <div class="text-3xl font-bold mt-2">{{ weeklyStats.total }}</div>
          <div class="flex items-center gap-1 mt-2">
            <span class="text-xs" :class="weeklyStats.totalDelta >= 0 ? 'text-emerald-400' : 'text-red-400'">
              {{ weeklyStats.totalDelta >= 0 ? '+' : '' }}{{ weeklyStats.totalDelta }}%
            </span>
            <span class="text-[10px] text-gray-500">vs 上周 {{ weeklyStats.lastTotal }}</span>
          </div>
        </div>
        <div class="bg-surface-1 rounded-xl border border-openclaw/20 p-5">
          <div class="text-xs text-openclaw">AI 交互</div>
          <div class="text-3xl font-bold mt-2 text-openclaw">{{ weeklyStats.ai }}</div>
          <div class="flex items-center gap-1 mt-2">
            <span class="text-xs" :class="weeklyStats.aiDelta >= 0 ? 'text-emerald-400' : 'text-red-400'">
              {{ weeklyStats.aiDelta >= 0 ? '+' : '' }}{{ weeklyStats.aiDelta }}%
            </span>
            <span class="text-[10px] text-gray-500">vs 上周 {{ weeklyStats.lastAI }}</span>
          </div>
        </div>
        <div class="bg-surface-1 rounded-xl border border-git/20 p-5">
          <div class="text-xs text-git">Git 提交</div>
          <div class="text-3xl font-bold mt-2 text-git">{{ weeklyStats.git }}</div>
          <div class="flex items-center gap-1 mt-2">
            <span class="text-xs" :class="weeklyStats.gitDelta >= 0 ? 'text-emerald-400' : 'text-red-400'">
              {{ weeklyStats.gitDelta >= 0 ? '+' : '' }}{{ weeklyStats.gitDelta }}%
            </span>
            <span class="text-[10px] text-gray-500">vs 上周 {{ weeklyStats.lastGit }}</span>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <!-- 每日趋势 -->
        <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
          <div class="text-sm font-medium mb-4">每日事件趋势</div>
          <div class="flex items-end gap-2 h-32">
            <div v-for="d in weekDailyTrend" :key="d.label" class="flex-1 flex flex-col items-center gap-1">
              <span class="text-[10px] text-gray-500">{{ d.count }}</span>
              <div class="w-full bg-accent/60 rounded-t-md transition-all"
                :style="{ height: `${Math.max(d.count / Math.max(...weekDailyTrend.map(x => x.count), 1) * 100, 4)}%` }" />
              <span class="text-[10px] text-gray-500">{{ d.label.slice(1) }}</span>
            </div>
          </div>
        </div>

        <!-- 来源分布 -->
        <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
          <div class="text-sm font-medium mb-4">本周来源分布</div>
          <div class="space-y-3">
            <div v-for="(count, source) in weekSourceDist" :key="source" class="flex items-center gap-3">
              <span class="text-xs w-20" :class="'text-' + source">{{ sourceNameMap[source] }}</span>
              <div class="flex-1 h-2.5 bg-surface-3 rounded-full overflow-hidden">
                <div class="h-full rounded-full" :class="sourceColorMap[source]" :style="{ width: `${weeklyStats.total ? count / weeklyStats.total * 100 : 0}%` }" />
              </div>
              <span class="text-xs text-gray-400 w-10 text-right">{{ count }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 月报视图 ===== -->
    <div v-if="viewMode === 'monthly'" class="space-y-6">
      <div class="flex items-center gap-4">
        <button @click="prevMonth" class="px-3 py-1.5 rounded-lg bg-surface-2 hover:bg-surface-3 text-sm transition">&lt;</button>
        <span class="text-sm font-medium w-32 text-center">{{ monthLabel }}</span>
        <button @click="nextMonth" class="px-3 py-1.5 rounded-lg bg-surface-2 hover:bg-surface-3 text-sm transition">&gt;</button>
      </div>

      <!-- 月统计 -->
      <div class="grid grid-cols-5 gap-3">
        <div class="bg-surface-1 rounded-xl border border-surface-3 p-4 text-center">
          <div class="text-xs text-gray-400">总事件</div>
          <div class="text-2xl font-bold mt-1">{{ monthlyStats.total }}</div>
        </div>
        <div class="bg-surface-1 rounded-xl border border-surface-3 p-4 text-center">
          <div class="text-xs text-openclaw">AI 交互</div>
          <div class="text-2xl font-bold mt-1 text-openclaw">{{ monthlyStats.ai }}</div>
        </div>
        <div class="bg-surface-1 rounded-xl border border-surface-3 p-4 text-center">
          <div class="text-xs text-git">Git 提交</div>
          <div class="text-2xl font-bold mt-1 text-git">{{ monthlyStats.git }}</div>
        </div>
        <div class="bg-surface-1 rounded-xl border border-surface-3 p-4 text-center">
          <div class="text-xs text-gray-400">活跃项目</div>
          <div class="text-2xl font-bold mt-1">{{ monthlyStats.projects }}</div>
        </div>
        <div class="bg-surface-1 rounded-xl border border-surface-3 p-4 text-center">
          <div class="text-xs text-gray-400">活跃天数</div>
          <div class="text-2xl font-bold mt-1 text-emerald-400">{{ monthlyStats.activeDays }}</div>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <!-- 每周趋势 -->
        <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
          <div class="text-sm font-medium mb-4">每周事件趋势</div>
          <div class="flex items-end gap-3 h-32">
            <div v-for="w in monthWeeklyTrend" :key="w.label" class="flex-1 flex flex-col items-center gap-1">
              <span class="text-[10px] text-gray-500">{{ w.count }}</span>
              <div class="w-full bg-accent/60 rounded-t-md transition-all"
                :style="{ height: `${Math.max(w.count / Math.max(...monthWeeklyTrend.map(x => x.count), 1) * 100, 4)}%` }" />
              <span class="text-[10px] text-gray-500">{{ w.label }}</span>
            </div>
          </div>
        </div>

        <!-- 来源趋势（堆叠） -->
        <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
          <div class="text-sm font-medium mb-4">来源周趋势</div>
          <div class="space-y-2">
            <div v-for="st in monthSourceTrend" :key="st.source" class="flex items-center gap-2">
              <span class="text-[10px] w-16" :class="'text-' + st.source">{{ sourceNameMap[st.source] }}</span>
              <div class="flex-1 flex items-center gap-1">
                <div v-for="(count, i) in st.weeks" :key="i"
                  class="flex-1 h-3 rounded-sm" :class="sourceColorMap[st.source]"
                  :style="{ opacity: Math.max(count / Math.max(...st.weeks, 1), 0.1) }"
                />
              </div>
            </div>
          </div>
          <div class="flex justify-between mt-2 text-[9px] text-gray-600">
            <span>第1周</span><span>第2周</span><span>第3周</span><span>第4周</span><span>第5周</span>
          </div>
        </div>
      </div>

      <!-- 技能成长 -->
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
        <div class="text-sm font-medium mb-4">技能成长排行</div>
        <div class="grid grid-cols-4 gap-3">
          <div v-for="skill in monthSkillGrowth" :key="skill.id" class="bg-surface-2 rounded-lg p-3">
            <div class="text-xs font-mono text-gray-300">{{ skill.name }}</div>
            <div class="flex items-center gap-2 mt-2">
              <div class="flex-1 h-2 bg-surface-3 rounded-full overflow-hidden">
                <div class="h-full bg-accent rounded-full" :style="{ width: `${skill.level}%` }" />
              </div>
              <span class="text-[10px] text-gray-400">Lv{{ skill.level }}</span>
            </div>
            <div class="text-[10px] text-gray-500 mt-1">{{ skill.total_uses }} 次使用</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

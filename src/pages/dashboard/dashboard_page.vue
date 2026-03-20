<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'

import type { StatsOverview, BehaviorPattern } from '@/types'
import { useEventsStore } from '@/stores/events'
import { useSkillsStore } from '@/stores/skills'
import { useOpenClawStore } from '@/stores/openclaw'
import { useDigestStore } from '@/stores/digest'
import { getStatsApi } from '@/http_api/stats'
import { getPatternsApi } from '@/http_api/patterns'
import { collectAllAndAnalyzeApi } from '@/http_api/collect'

const router = useRouter()
const eventsStore = useEventsStore()
const skillsStore = useSkillsStore()
const openclawStore = useOpenClawStore()
const digestStore = useDigestStore()

const stats = ref<StatsOverview | null>(null)
const patterns = ref<BehaviorPattern[]>([])
const collecting = ref(false)
const collectResult = ref('')

const animatedValues = ref({
  total_events: 0,
  total_openclaw_sessions: 0,
  total_claude_sessions: 0,
  total_codex_sessions: 0,
  total_git_commits: 0,
  total_projects: 0,
  total_skills: 0,
  streak_days: 0,
})

const animateNumber = (key: keyof typeof animatedValues.value, target: number, duration: number) => {
  const start = performance.now()
  const step = (now: number) => {
    const progress = Math.min((now - start) / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    animatedValues.value[key] = Math.round(target * eased)
    if (progress < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

const loadStats = async () => {
  const sRes = await getStatsApi()
  if (sRes.data) {
    stats.value = sRes.data
    animateNumber('total_events', sRes.data.total_events ?? 0, 1200)
    animateNumber('total_openclaw_sessions', sRes.data.total_openclaw_sessions ?? 0, 1000)
    animateNumber('total_claude_sessions', sRes.data.total_claude_sessions ?? 0, 1000)
    animateNumber('total_codex_sessions', sRes.data.total_codex_sessions ?? 0, 1000)
    animateNumber('total_git_commits', sRes.data.total_git_commits ?? 0, 900)
    animateNumber('total_projects', sRes.data.total_projects ?? 0, 800)
    animateNumber('total_skills', sRes.data.total_skills ?? 0, 900)
    animateNumber('streak_days', sRes.data.streak_days ?? 0, 700)
  }
}

let statsRefreshTimer: ReturnType<typeof setTimeout> | null = null

const scheduleStatsRefresh = (delayMs = 600) => {
  if (statsRefreshTimer) clearTimeout(statsRefreshTimer)
  statsRefreshTimer = setTimeout(() => {
    statsRefreshTimer = null
    void loadStats()
  }, delayMs)
}

onMounted(async () => {
  const [, pRes] = await Promise.all([loadStats(), getPatternsApi()])
  if (pRes.data) patterns.value = pRes.data
  await Promise.all([
    eventsStore.fetchEvents(),
    skillsStore.fetchSkills(),
    openclawStore.fetchSessions(),
  ])
})

onUnmounted(() => {
  if (statsRefreshTimer) clearTimeout(statsRefreshTimer)
})

watch(() => eventsStore.lastRealtimeEventAt, timestamp => {
  if (!timestamp) return
  scheduleStatsRefresh()
})

const sourceDistribution = computed(() => {
  const counts = { openclaw: 0, terminal: 0, git: 0, claude_code: 0, codex: 0, env: 0 }
  for (const e of eventsStore.events) {
    counts[e.source]++
  }
  return counts
})

const topSkills = computed(() =>
  [...skillsStore.skills].sort((a, b) => b.level - a.level).slice(0, 5)
)

const recentEvents = computed(() =>
  [...eventsStore.events].sort((a, b) => b.timestamp - a.timestamp).slice(0, 8)
)

const topPatterns = computed(() =>
  [...patterns.value].sort((a, b) => b.confidence - a.confidence).slice(0, 3)
)

// AI 对话：OpenClaw + Claude Code sessions 合并，按时间排序取最近 3 条
const recentAiSessions = computed(() =>
  [...openclawStore.sessions].sort((a, b) => b.created_at - a.created_at).slice(0, 3)
)

const sessionAgent = (session: { tags: string[] }) =>
  session.tags.includes('codex') ? 'codex' : session.tags.includes('claude_code') ? 'claude_code' : 'openclaw'

const sourceColor: Record<string, string> = {
  openclaw: 'text-openclaw',
  terminal: 'text-terminal',
  git: 'text-git',
  claude_code: 'text-claude',
  codex: 'text-cyan-300',
  env: 'text-env',
}

const sourceNameMap: Record<string, string> = {
  openclaw: 'OpenClaw',
  terminal: '终端',
  git: 'Git',
  claude_code: 'Claude Code',
  codex: 'Codex',
  env: '环境',
}

const categoryColorMap: Record<string, string> = {
  git: 'bg-git/20 text-git',
  coding: 'bg-accent/20 text-accent',
  review: 'bg-openclaw/20 text-openclaw',
  devops: 'bg-terminal/20 text-terminal',
  collaboration: 'bg-purple-500/20 text-purple-400',
}

const formatTime = (ts: number) => {
  const d = new Date(ts * 1000)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const handleCollectAll = async () => {
  collecting.value = true
  collectResult.value = ''
  const res = await collectAllAndAnalyzeApi()
  collecting.value = false
  if (res.data) {
    const d = res.data as any
    const total = d.results ? d.results.reduce((s: number, r: any) => s + r.inserted, 0) : 0
    const mined = d.mining_count ?? 0
    collectResult.value = `采集完成: 新增 ${total} 条数据，挖掘 ${mined} 个模式${d.digest_updated ? '，已更新今日摘要' : ''}`
    // 刷新所有模块
    await Promise.all([
      loadStats(),
      eventsStore.fetchEvents(),
      skillsStore.fetchSkills(),
      openclawStore.fetchSessions(),
      digestStore.fetchSummaries(),
    ])
    const pRes = await getPatternsApi()
    if (pRes.data) patterns.value = pRes.data
    setTimeout(() => { collectResult.value = '' }, 6000)
  }
}
</script>

<template>
  <div class="p-6 space-y-6 overflow-y-auto h-full">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold">ShrimpFlow 总览</h1>
        <p class="text-sm text-gray-400 mt-1">Record - Visualize - Learn - Become You | 你的 AI 开发者数字孪生</p>
      </div>
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 cursor-pointer" @click="router.push('/security')">
          <div class="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <span class="text-[10px] text-emerald-400">本地模式 · 已脱敏</span>
        </div>
        <button
          class="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
          :class="collecting ? 'bg-surface-3 text-gray-500 cursor-wait' : 'bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 cursor-pointer'"
          :disabled="collecting"
          @click="handleCollectAll"
        >
          {{ collecting ? '采集分析中...' : '一键采集' }}
        </button>
      </div>
    </div>
    <div v-if="collectResult" class="text-xs text-cyan-400 bg-cyan-500/10 rounded-lg px-3 py-1.5 -mt-4">
      {{ collectResult }}
    </div>

    <!-- 四层架构步骤条 -->
    <div class="bg-surface-1 rounded-xl border border-surface-3 p-5 gradient-border">
      <div class="text-sm font-medium mb-4 text-gray-300">ShrimpFlow 四层架构</div>
      <div class="grid grid-cols-4 gap-3">
        <div class="relative bg-surface-2 rounded-xl p-4 border border-accent/30 cursor-pointer hover:scale-[1.02] hover:shadow-lg hover:shadow-accent/10 transition-all" @click="router.push('/layer/shadow')">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center">
              <svg class="w-4 h-4 text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" /></svg>
            </div>
            <span class="text-xs font-medium text-accent">Layer 1</span>
          </div>
          <div class="text-sm font-semibold text-gray-200">Shadow</div>
          <div class="text-xs text-gray-400 mt-1">全量记录开发行为</div>
          <div class="mt-3 h-1.5 bg-surface-3 rounded-full overflow-hidden">
            <div class="h-full bg-accent rounded-full" style="width: 95%" />
          </div>
          <div class="text-[10px] text-gray-500 mt-1">95% 完成</div>
        </div>
        <div class="relative bg-surface-2 rounded-xl p-4 border border-openclaw/30 cursor-pointer hover:scale-[1.02] hover:shadow-lg hover:shadow-openclaw/10 transition-all" @click="router.push('/layer/mirror')">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-8 h-8 rounded-lg bg-openclaw/20 flex items-center justify-center">
              <svg class="w-4 h-4 text-openclaw" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M9 21V9" /></svg>
            </div>
            <span class="text-xs font-medium text-openclaw">Layer 2</span>
          </div>
          <div class="text-sm font-semibold text-gray-200">Mirror</div>
          <div class="text-xs text-gray-400 mt-1">可视化开发画像</div>
          <div class="mt-3 h-1.5 bg-surface-3 rounded-full overflow-hidden">
            <div class="h-full bg-openclaw rounded-full" style="width: 80%" />
          </div>
          <div class="text-[10px] text-gray-500 mt-1">80% 完成</div>
        </div>
        <div class="relative bg-surface-2 rounded-xl p-4 border border-purple-500/30 cursor-pointer hover:scale-[1.02] hover:shadow-lg hover:shadow-purple-500/10 transition-all" @click="router.push('/layer/brain')">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
              <svg class="w-4 h-4 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-2.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7z" /><line x1="9" y1="21" x2="15" y2="21" /></svg>
            </div>
            <span class="text-xs font-medium text-purple-400">Layer 3</span>
          </div>
          <div class="text-sm font-semibold text-gray-200">Brain</div>
          <div class="text-xs text-gray-400 mt-1">学习行为模式</div>
          <div class="mt-3 h-1.5 bg-surface-3 rounded-full overflow-hidden">
            <div class="h-full bg-purple-500 rounded-full" style="width: 60%" />
          </div>
          <div class="text-[10px] text-gray-500 mt-1">60% 完成</div>
        </div>
        <div class="relative bg-surface-2 rounded-xl p-4 border border-emerald-500/30 cursor-pointer hover:scale-[1.02] hover:shadow-lg hover:shadow-emerald-500/10 transition-all" @click="router.push('/layer/autopilot')">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
              <svg class="w-4 h-4 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>
            </div>
            <span class="text-xs font-medium text-emerald-400">Layer 4</span>
          </div>
          <div class="text-sm font-semibold text-gray-200">Autopilot</div>
          <div class="text-xs text-gray-400 mt-1">团队 Workflow 下发</div>
          <div class="mt-3 h-1.5 bg-surface-3 rounded-full overflow-hidden">
            <div class="h-full bg-emerald-500 rounded-full" style="width: 35%" />
          </div>
          <div class="text-[10px] text-gray-500 mt-1">35% 完成</div>
        </div>
      </div>
    </div>

    <!-- 统计卡片：4 列 -->
    <div class="grid grid-cols-4 gap-4">
      <!-- 总事件数 -->
      <div class="bg-surface-1 rounded-xl p-4 border border-surface-3 cursor-pointer glow-card" @click="router.push('/timeline')">
        <div class="text-xs text-gray-400">总事件数</div>
        <div class="text-2xl font-bold mt-1 count-up">{{ animatedValues.total_events.toLocaleString() }}</div>
        <div class="text-xs text-gray-500 mt-1">跨越 {{ stats?.total_days }} 天</div>
      </div>
      <!-- AI 交互 -->
      <div class="bg-surface-1 rounded-xl p-4 border border-surface-3 cursor-pointer glow-card openclaw-pulse" @click="router.push('/openclaw')">
        <div class="text-xs text-openclaw">AI 交互</div>
        <div class="text-2xl font-bold mt-1 text-openclaw count-up">
          {{ (animatedValues.total_openclaw_sessions + animatedValues.total_claude_sessions + animatedValues.total_codex_sessions).toLocaleString() }}
        </div>
        <div class="flex items-center gap-3 mt-1">
          <span class="text-[10px] text-gray-500">OC {{ stats?.total_openclaw_sessions ?? 0 }}</span>
          <span class="text-[10px] text-blue-400">CC {{ stats?.total_claude_sessions ?? 0 }}</span>
          <span class="text-[10px] text-cyan-300">CX {{ stats?.total_codex_sessions ?? 0 }}</span>
        </div>
      </div>
      <!-- Git 提交 -->
      <div class="bg-surface-1 rounded-xl p-4 border border-surface-3 cursor-pointer glow-card" @click="router.push('/timeline')">
        <div class="text-xs text-git">Git 提交</div>
        <div class="text-2xl font-bold mt-1 text-git count-up">{{ animatedValues.total_git_commits.toLocaleString() }}</div>
        <div class="text-xs text-gray-500 mt-1">最活跃: {{ stats?.most_active_project }}</div>
      </div>
      <!-- 技能追踪 -->
      <div class="bg-surface-1 rounded-xl p-4 border border-surface-3 cursor-pointer glow-card" @click="router.push('/skills')">
        <div class="text-xs text-gray-400">技能追踪</div>
        <div class="text-2xl font-bold mt-1 count-up">{{ animatedValues.total_skills }}</div>
        <div class="text-xs text-success mt-1">连续 {{ animatedValues.streak_days }} 天</div>
      </div>
    </div>

    <div class="grid grid-cols-3 gap-4">
      <!-- 事件来源分布 -->
      <div class="bg-surface-1 rounded-xl p-4 border border-surface-3">
        <div class="text-sm font-medium mb-3">事件来源分布</div>
        <div class="space-y-2.5">
          <div v-for="(count, source) in sourceDistribution" :key="source" class="flex items-center gap-3">
            <div class="w-20 text-xs" :class="sourceColor[source]">{{ sourceNameMap[source] }}</div>
            <div class="flex-1 h-2 bg-surface-3 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all"
                :class="source === 'openclaw' ? 'bg-openclaw' : source === 'terminal' ? 'bg-terminal' : source === 'git' ? 'bg-git' : source === 'claude_code' ? 'bg-claude' : source === 'codex' ? 'bg-cyan-300' : 'bg-env'"
                :style="{ width: `${(count / (stats?.total_events ?? 1)) * 100}%` }"
              />
            </div>
            <div class="text-xs text-gray-400 w-10 text-right">{{ count }}</div>
          </div>
        </div>
      </div>

      <!-- 核心技能排行 -->
      <div class="bg-surface-1 rounded-xl p-4 border border-surface-3 cursor-pointer hover:border-accent/40 transition-colors" @click="router.push('/skills')">
        <div class="text-sm font-medium mb-3">核心技能排行</div>
        <div class="space-y-2.5">
          <div v-for="skill in topSkills" :key="skill.id" class="flex items-center gap-3">
            <div class="w-20 text-xs font-mono" :class="skill.category === 'openclaw' ? 'text-openclaw' : 'text-gray-300'">{{ skill.name }}</div>
            <div class="flex-1 h-2 bg-surface-3 rounded-full overflow-hidden">
              <div class="h-full bg-accent rounded-full" :style="{ width: `${skill.level}%` }" />
            </div>
            <div class="text-xs text-gray-400 w-8 text-right">Lv{{ skill.level }}</div>
          </div>
        </div>
      </div>

      <!-- 行为模式洞察 -->
      <div class="bg-surface-1 rounded-xl p-4 border border-surface-3 cursor-pointer hover:border-purple-500/40 transition-colors" @click="router.push('/patterns')">
        <div class="text-sm font-medium mb-3">行为模式洞察</div>
        <div class="space-y-3">
          <div v-for="pattern in topPatterns" :key="pattern.id" class="space-y-1.5">
            <div class="flex items-center gap-2">
              <span class="text-[10px] px-1.5 py-0.5 rounded" :class="categoryColorMap[pattern.category]">{{ pattern.category }}</span>
              <span class="text-xs text-gray-300 truncate">{{ pattern.name }}</span>
            </div>
            <div class="flex items-center gap-2">
              <div class="flex-1 h-1.5 bg-surface-3 rounded-full overflow-hidden">
                <div class="h-full bg-purple-500 rounded-full" :style="{ width: `${pattern.confidence}%` }" />
              </div>
              <span class="text-[10px] text-gray-500 w-8 text-right">{{ pattern.confidence }}%</span>
            </div>
            <div class="text-[10px] text-gray-500">{{ pattern.evidence_count }} 条证据</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 最近活动 + AI 对话 -->
    <div class="grid grid-cols-2 gap-4">
      <div class="bg-surface-1 rounded-xl p-4 border border-surface-3">
        <div class="text-sm font-medium mb-3">最近活动</div>
        <div class="space-y-2">
          <div v-for="event in recentEvents" :key="event.id" class="flex items-start gap-2">
            <div class="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0"
              :class="event.source === 'openclaw' ? 'bg-openclaw' : event.source === 'terminal' ? 'bg-terminal' : event.source === 'git' ? 'bg-git' : event.source === 'claude_code' ? 'bg-claude' : event.source === 'codex' ? 'bg-cyan-300' : 'bg-env'"
            />
            <div class="min-w-0 flex-1">
              <div class="text-xs font-mono truncate text-gray-300">{{ event.action }}</div>
              <div class="text-[10px] text-gray-500">{{ event.project }} · {{ formatTime(event.timestamp) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- AI 对话（OpenClaw + Claude Code） -->
      <div class="bg-surface-1 rounded-xl p-4 border border-surface-3">
        <div class="flex items-center justify-between mb-3">
          <div class="text-sm font-medium">AI 对话</div>
          <button class="text-[10px] text-openclaw hover:text-openclaw/80 transition-colors" @click="router.push('/openclaw')">查看全部</button>
        </div>
        <div class="space-y-3">
          <div
            v-for="session in recentAiSessions"
            :key="session.id"
            class="bg-surface-2 rounded-lg p-3 cursor-pointer hover:bg-surface-3/50 transition-colors"
            @click="openclawStore.selectSession(session.id); router.push('/openclaw')"
          >
            <div class="flex items-center gap-2 mb-1">
              <div
                class="w-5 h-5 rounded-full flex items-center justify-center shrink-0"
                :class="sessionAgent(session) === 'claude_code' ? 'bg-blue-500/20' : sessionAgent(session) === 'codex' ? 'bg-cyan-300/20' : 'bg-openclaw/20'"
              >
                <span
                  class="text-[8px] font-bold"
                  :class="sessionAgent(session) === 'claude_code' ? 'text-blue-400' : sessionAgent(session) === 'codex' ? 'text-cyan-300' : 'text-openclaw'"
                >
                  {{ sessionAgent(session) === 'claude_code' ? 'CC' : sessionAgent(session) === 'codex' ? 'CX' : 'OC' }}
                </span>
              </div>
              <span class="text-xs text-gray-200 truncate">{{ session.title }}</span>
            </div>
            <div class="text-[10px] text-gray-500 line-clamp-2">{{ session.summary }}</div>
            <div class="flex items-center gap-2 mt-1.5">
              <span class="text-[10px] text-gray-600">{{ session.project }}</span>
              <span class="text-[10px] text-gray-600">{{ session.messages.length }} 条消息</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

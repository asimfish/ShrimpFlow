<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'

import type { AIProviderStrategy, StatsOverview } from '@/types'
import { useEventsStore } from '@/stores/events'
import { useSkillsStore } from '@/stores/skills'
import { useOpenClawStore } from '@/stores/openclaw'
import { useDigestStore } from '@/stores/digest'
import { usePatternsStore } from '@/stores/patterns'
import { getStatsApi } from '@/http_api/stats'
import { collectAllAndAnalyzeApi } from '@/http_api/collect'
import { getAISettingsApi, getScheduleApi, updateAISettingsApi, updateScheduleApi } from '@/http_api/settings'
import { getTaskApi } from '@/http_api/tasks'
import { exportMarkdownApi } from '@/http_api/claw_gen'

const router = useRouter()
const eventsStore = useEventsStore()
const skillsStore = useSkillsStore()
const openclawStore = useOpenClawStore()
const digestStore = useDigestStore()
const patternsStore = usePatternsStore()
const workflowShowcaseUrl = `${import.meta.env.BASE_URL}shrimpflow_workflow.html`

const stats = ref<StatsOverview | null>(null)
const collecting = ref(false)
const collectResult = ref('')
const collectProgress = ref(0)
const collectStage = ref('')
const collectTaskId = ref<string | null>(null)
let collectPollTimer: ReturnType<typeof setInterval> | null = null

const stopCollectPoll = () => {
  if (collectPollTimer) { clearInterval(collectPollTimer); collectPollTimer = null }
}

const startCollectPoll = (taskId: string) => {
  stopCollectPoll()
  localStorage.setItem('collect_task_id', taskId)
  const poll = async () => {
    const res = await getTaskApi(taskId)
    if (!res.data) {
      stopCollectPoll()
      localStorage.removeItem('collect_task_id')
      collecting.value = false
      return
    }
    const t = res.data
    collectProgress.value = t.progress
    collectStage.value = t.stage ?? ''
    if (t.status === 'done') {
      stopCollectPoll()
      localStorage.removeItem('collect_task_id')
      collecting.value = false
      const d = t.result as any ?? {}
      const total = d.results ? d.results.reduce((s: number, r: any) => s + (r.inserted ?? 0), 0) : 0
      collectResult.value = `采集完成: +${total} 数据, ${d.mining_count ?? 0} 浅层, ${d.deep_mining_count ?? 0} 深层, ${d.session_mining_count ?? 0} 对话, ${d.atoms_extracted ?? 0} 原子, ${d.episodes_sliced ?? 0} 片段${(d.patterns_pushed ?? 0) > 0 ? `, ${d.patterns_pushed} 待确认` : ''}`
      await Promise.all([
        loadStats(),
        eventsStore.fetchEvents(true),
        skillsStore.fetchSkills(true),
        openclawStore.fetchSessions(true),
        digestStore.fetchSummaries(true),
        patternsStore.fetchPatterns(undefined, true),
      ])
      setTimeout(() => { collectResult.value = '' }, 8000)
    } else if (t.status === 'error') {
      stopCollectPoll()
      localStorage.removeItem('collect_task_id')
      collecting.value = false
      collectResult.value = `采集出错: ${t.error ?? '未知错误'}`
    }
  }
  poll()
  collectPollTimer = setInterval(poll, 1500)
}
const scheduleEnabled = ref(true)
const scheduleInterval = ref(3)
const scheduleLoading = ref(false)
const aiProviderStrategy = ref<AIProviderStrategy>('heuristic_only')
const aiDefaultModel = ref('')
const aiSelectorModel = ref('')
const aiLoading = ref(false)
const aiConfigMsg = ref('')
const aiProviders = ref<{ key: string; label: string; configured?: boolean; active?: boolean; preferred?: boolean; models?: { id: string; name: string }[] }[]>([])
const aiModels = ref<{ id: string; name: string }[]>([])

const selectedAIProvider = computed(() =>
  aiProviders.value.find(provider => provider.key === aiProviderStrategy.value) ?? null,
)

watch(selectedAIProvider, provider => {
  const models = provider?.models ?? []
  aiModels.value = models
  if (!models.length) return
  const modelIds = new Set(models.map(model => model.id))
  if (!modelIds.has(aiDefaultModel.value)) {
    aiDefaultModel.value = models[0].id
  }
  if (!modelIds.has(aiSelectorModel.value)) {
    aiSelectorModel.value = models[Math.min(1, models.length - 1)].id
  }
})

const intervalOptions = [
  { label: '1 小时', value: 1 },
  { label: '2 小时', value: 2 },
  { label: '3 小时', value: 3 },
  { label: '6 小时', value: 6 },
  { label: '12 小时', value: 12 },
  { label: '24 小时', value: 24 },
]

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
  // 恢复进行中的采集任务
  const savedTaskId = localStorage.getItem('collect_task_id')
  if (savedTaskId) {
    collecting.value = true
    collectTaskId.value = savedTaskId
    startCollectPoll(savedTaskId)
  }
  await Promise.all([
    loadStats(),
    loadSchedule(),
    loadAISettings(),
    eventsStore.ensureLoaded(),
    skillsStore.ensureLoaded(),
    openclawStore.ensureSessionsLoaded(),
    digestStore.ensureLoaded(),
    patternsStore.ensurePatternsLoaded(),
  ])
})

onUnmounted(() => {
  if (statsRefreshTimer) clearTimeout(statsRefreshTimer)
  stopCollectPoll()
})

watch(() => eventsStore.lastRealtimeEventAt, timestamp => {
  if (!timestamp) return
  scheduleStatsRefresh()
})

const sourceDistribution = computed(() => {
  const counts: Record<string, number> = {
    openclaw: 0,
    terminal: 0,
    git: 0,
    claude_code: 0,
    codex: 0,
    cursor: 0,
    vscode: 0,
    env: 0,
  }
  for (const e of eventsStore.events) {
    counts[e.source] = (counts[e.source] ?? 0) + 1
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
  [...patternsStore.patterns].sort((a, b) => b.confidence - a.confidence).slice(0, 3)
)

const heroSessionCount = computed(() => {
  const s = stats.value
  if (!s) return 0
  return (s.total_openclaw_sessions ?? 0) + (s.total_claude_sessions ?? 0) + (s.total_codex_sessions ?? 0)
})
const heroPatternCount = computed(() => patternsStore.patterns.length)
const heroTasteConfidence = computed(() => {
  const ps = patternsStore.patterns
  if (!ps.length) return 0
  return Math.round(ps.reduce((acc, p) => acc + p.confidence, 0) / ps.length)
})

const exportClaudeBusy = ref(false)
const handleExportClaudeMd = async () => {
  exportClaudeBusy.value = true
  const res = await exportMarkdownApi()
  exportClaudeBusy.value = false
  if (!res.data?.markdown) return
  const blob = new Blob([res.data.markdown], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'CLAUDE.md'
  a.click()
  URL.revokeObjectURL(url)
}

// AI 对话：OpenClaw + Claude Code sessions 合并，按时间排序取最近 3 条
const recentAiSessions = computed(() =>
  [...openclawStore.sessions].sort((a, b) => b.created_at - a.created_at).slice(0, 3)
)

const sourceColor: Record<string, string> = {
  openclaw: 'text-openclaw',
  terminal: 'text-terminal',
  git: 'text-git',
  claude_code: 'text-claude',
  codex: 'text-cyan-300',
  cursor: 'text-emerald-400',
  vscode: 'text-sky-400',
  env: 'text-env',
}

const sourceNameMap: Record<string, string> = {
  openclaw: 'OpenClaw',
  terminal: '终端',
  git: 'Git',
  claude_code: 'Claude Code',
  codex: 'Codex',
  cursor: 'Cursor',
  vscode: 'VS Code',
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
  collectProgress.value = 0
  collectStage.value = '提交任务…'
  const res = await collectAllAndAnalyzeApi()
  if (res.data?.task_id) {
    collectTaskId.value = res.data.task_id
    startCollectPoll(res.data.task_id)
  } else {
    collecting.value = false
    collectResult.value = res.error ?? '提交失败'
  }
}

const loadSchedule = async () => {
  const res = await getScheduleApi()
  if (res.data) {
    scheduleEnabled.value = res.data.enabled
    scheduleInterval.value = res.data.interval_hours
  }
}

const loadAISettings = async () => {
  const res = await getAISettingsApi()
  if (res.data) {
    aiProviderStrategy.value = res.data.selected_provider
    aiDefaultModel.value = res.data.default_model
    aiSelectorModel.value = res.data.selector_model
    aiProviders.value = res.data.providers
    aiModels.value = res.data.models
  }
}

const handleScheduleToggle = async () => {
  scheduleLoading.value = true
  const next = !scheduleEnabled.value
  const res = await updateScheduleApi({ enabled: next })
  if (res.data) {
    scheduleEnabled.value = res.data.enabled
    scheduleInterval.value = res.data.interval_hours
  }
  scheduleLoading.value = false
}

const handleIntervalChange = async (e: Event) => {
  const val = Number((e.target as HTMLSelectElement).value)
  scheduleLoading.value = true
  const res = await updateScheduleApi({ interval_hours: val })
  if (res.data) {
    scheduleEnabled.value = res.data.enabled
    scheduleInterval.value = res.data.interval_hours
  }
  scheduleLoading.value = false
}

const saveAISettings = async () => {
  aiLoading.value = true
  aiConfigMsg.value = ''
  const res = await updateAISettingsApi({
    selected_provider: aiProviderStrategy.value,
    default_model: aiDefaultModel.value,
    selector_model: aiSelectorModel.value,
  })
  if (res.data) {
    aiProviderStrategy.value = res.data.selected_provider
    aiDefaultModel.value = res.data.default_model
    aiSelectorModel.value = res.data.selector_model
    aiProviders.value = res.data.providers
    aiModels.value = res.data.models
    aiConfigMsg.value = 'AI 分析配置已保存'
    setTimeout(() => { aiConfigMsg.value = '' }, 2500)
  } else {
    aiConfigMsg.value = res.error ?? 'AI 分析配置保存失败'
  }
  aiLoading.value = false
}
</script>

<template>
  <div class="p-6 space-y-6 overflow-y-auto h-full">
    <section class="glass-card rounded-2xl p-6 md:p-8 space-y-4 border border-white/[0.08]">
      <div>
        <h2 class="text-2xl md:text-3xl font-semibold heading-tight text-gray-100">ShrimpFlow — 你的 AI 认知副驾</h2>
        <p class="text-sm md:text-base text-gray-400 mt-2">不是记住你做过什么，而是理解你怎么思考</p>
      </div>
      <p class="text-xs md:text-sm text-gray-500">
        已分析 {{ heroSessionCount.toLocaleString() }} 次对话 · 发现 {{ heroPatternCount.toLocaleString() }} 条行为模式 · 品味准确度 {{ heroTasteConfidence }}%
      </p>
      <div class="flex flex-wrap gap-2">
        <button
          type="button"
          class="px-4 py-2 rounded-full text-xs font-medium bg-accent text-white hover:bg-accent/90 transition-colors"
          @click="router.push('/twin')"
        >
          查看我的 AI Twin
        </button>
        <button
          type="button"
          class="px-4 py-2 rounded-full text-xs font-medium border border-accent/50 text-accent hover:bg-accent/10 transition-colors disabled:opacity-50"
          :disabled="exportClaudeBusy"
          @click="handleExportClaudeMd"
        >
          {{ exportClaudeBusy ? '导出中…' : '导出 CLAUDE.md' }}
        </button>
      </div>
    </section>
    <section class="relative overflow-hidden rounded-2xl border border-emerald-400/25 bg-gradient-to-br from-emerald-500/[0.14] via-cyan-500/[0.08] to-violet-500/[0.12] p-5 md:p-6">
      <div class="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-emerald-400/10 blur-3xl" />
      <div class="relative grid gap-5 lg:grid-cols-[1.35fr_0.65fr]">
        <div class="space-y-4">
          <div class="inline-flex items-center gap-2 rounded-full border border-emerald-400/25 bg-emerald-400/10 px-3 py-1 text-[11px] font-medium text-emerald-200">
            核心贡献展示
          </div>
          <div>
            <h2 class="text-xl md:text-2xl font-semibold text-white">一个使用 ShrimpFlow 学到的超长工作流</h2>
            <p class="mt-2 max-w-2xl text-sm leading-6 text-gray-300">
              ShrimpFlow 不只是列出零散 pattern，而是把真实开发事件、AI 会话、技能调用和反馈证据串成一条可执行的长链路 workflow：从目标澄清、影响面扫描、实现验证，到发布证据回收，展示“学会你怎么工作”后的完整产物。
            </p>
          </div>
          <div class="grid gap-2 sm:grid-cols-4">
            <div class="rounded-xl border border-white/10 bg-black/20 p-3">
              <div class="text-lg font-semibold text-emerald-300">32</div>
              <div class="mt-1 text-[10px] text-gray-400">行为事件</div>
            </div>
            <div class="rounded-xl border border-white/10 bg-black/20 p-3">
              <div class="text-lg font-semibold text-cyan-300">8</div>
              <div class="mt-1 text-[10px] text-gray-400">AI 会话</div>
            </div>
            <div class="rounded-xl border border-white/10 bg-black/20 p-3">
              <div class="text-lg font-semibold text-violet-300">10</div>
              <div class="mt-1 text-[10px] text-gray-400">行为模式</div>
            </div>
            <div class="rounded-xl border border-white/10 bg-black/20 p-3">
              <div class="text-lg font-semibold text-amber-300">1</div>
              <div class="mt-1 text-[10px] text-gray-400">超长 workflow</div>
            </div>
          </div>
          <div class="flex flex-wrap items-center gap-3">
            <a
              :href="workflowShowcaseUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-2 rounded-full bg-emerald-400 px-4 py-2 text-xs font-semibold text-black transition-colors hover:bg-emerald-300"
            >
              查看超长工作流 →
            </a>
            <button
              type="button"
              class="rounded-full border border-emerald-400/30 px-4 py-2 text-xs font-medium text-emerald-200 transition-colors hover:bg-emerald-400/10"
              @click="router.push('/patterns')"
            >
              看它由哪些 Pattern 组成
            </button>
          </div>
        </div>
        <div class="rounded-2xl border border-white/10 bg-black/25 p-4">
          <div class="text-xs font-medium text-gray-300">学习到的执行链路</div>
          <div class="mt-4 space-y-3">
            <div class="flex items-center gap-3">
              <div class="h-7 w-7 rounded-full bg-emerald-400/20 text-center text-xs leading-7 text-emerald-200">1</div>
              <div class="text-xs text-gray-300">从行为和 AI 会话抽取证据</div>
            </div>
            <div class="flex items-center gap-3">
              <div class="h-7 w-7 rounded-full bg-cyan-400/20 text-center text-xs leading-7 text-cyan-200">2</div>
              <div class="text-xs text-gray-300">把重复策略聚合为 pattern</div>
            </div>
            <div class="flex items-center gap-3">
              <div class="h-7 w-7 rounded-full bg-violet-400/20 text-center text-xs leading-7 text-violet-200">3</div>
              <div class="text-xs text-gray-300">组合成可复用超长 workflow</div>
            </div>
            <div class="flex items-center gap-3">
              <div class="h-7 w-7 rounded-full bg-amber-400/20 text-center text-xs leading-7 text-amber-200">4</div>
              <div class="text-xs text-gray-300">导出为 ClawProfile / Claude Code 技能</div>
            </div>
          </div>
        </div>
      </div>
    </section>
    <!-- 演示数据提示 banner（仅当 stats.is_demo_data 为真） -->
    <div
      v-if="stats?.is_demo_data"
      class="bg-violet-500/10 border border-violet-500/25 rounded-xl px-4 py-3 flex items-start gap-3"
    >
      <div class="w-6 h-6 rounded-full bg-violet-500/25 flex items-center justify-center text-violet-300 text-xs font-semibold shrink-0 mt-0.5">i</div>
      <div class="flex-1 text-xs">
        <div class="font-medium text-violet-200">你正在看演示数据（{{ stats.demo_event_count }} 条事件 · {{ stats.demo_session_count }} 次对话）</div>
        <div class="mt-1 text-violet-200/70">这些是 seed 数据用来让你看懂界面。开始用 Claude Code / Cursor / 终端后，你自己的事件会把演示数据比下去，界面会自动反映真实使用。</div>
        <div class="mt-2 flex items-center gap-3">
          <button class="text-[11px] text-violet-300 hover:text-violet-200 underline" @click="router.push('/openclaw')">打开 OpenClaw 开始对话 →</button>
          <router-link to="/architecture" class="text-[11px] text-violet-300/70 hover:text-violet-200 underline">看看系统怎么跑 →</router-link>
        </div>
      </div>
    </div>

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
        <!-- 定时采集配置 -->
        <div class="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-surface-2 border border-surface-3">
          <button
            class="w-7 h-4 rounded-full transition-colors relative"
            :class="scheduleEnabled ? 'bg-cyan-500' : 'bg-surface-3'"
            :disabled="scheduleLoading"
            @click="handleScheduleToggle"
          >
            <div
              class="absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform"
              :class="scheduleEnabled ? 'translate-x-3.5' : 'translate-x-0.5'"
            />
          </button>
          <select
            class="bg-transparent text-[10px] text-gray-400 outline-none cursor-pointer appearance-none pr-3"
            :value="scheduleInterval"
            :disabled="scheduleLoading"
            @change="handleIntervalChange"
          >
            <option v-for="opt in intervalOptions" :key="opt.value" :value="opt.value" class="bg-surface-2">
              {{ opt.label }}
            </option>
          </select>
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
    <!-- 采集进度条 -->
    <div v-if="collecting" class="bg-surface-1 rounded-lg border border-cyan-500/20 px-4 py-3 -mt-4 space-y-2">
      <div class="flex items-center justify-between">
        <span class="text-xs text-cyan-400">{{ collectStage }}</span>
        <span class="text-[10px] text-gray-500">{{ Math.round(collectProgress) }}%</span>
      </div>
      <div class="h-2 bg-surface-3 rounded-full overflow-hidden">
        <div
          class="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full transition-all duration-200"
          :style="{ width: `${collectProgress}%` }"
        />
      </div>
      <div class="text-[10px] text-gray-500">
        流水线: 采集 → 统计挖掘 → AI增强 → 日报 → Atom → Episode → 深层挖掘 → 对话挖掘 → 图谱 → 证据 → 过滤 → 推送
      </div>
    </div>
    <div v-if="collectResult" class="text-xs text-cyan-400 bg-cyan-500/10 rounded-lg px-3 py-1.5 -mt-4">
      {{ collectResult }}
    </div>
    <div class="grid grid-cols-[1.4fr_1fr] gap-4">
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-4">
        <div class="flex items-center justify-between gap-3 mb-3">
          <div>
            <div class="text-sm font-medium text-gray-200">AI 分析配置</div>
            <div class="text-xs text-gray-500 mt-1">控制会话分析、摘要生成和语义聚合的供应商与模型</div>
          </div>
          <div v-if="aiConfigMsg" class="text-[11px] text-cyan-400">{{ aiConfigMsg }}</div>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <label class="space-y-1">
            <div class="text-[11px] text-gray-500">分析供应商</div>
            <select v-model="aiProviderStrategy" class="w-full bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-sm text-gray-200">
              <option v-for="provider in aiProviders" :key="provider.key" :value="provider.key">
                {{ provider.label }}
              </option>
            </select>
          </label>
          <label class="space-y-1">
            <div class="text-[11px] text-gray-500">默认模型</div>
            <select
              v-model="aiDefaultModel"
              class="w-full bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-sm text-gray-200"
              :disabled="!aiModels.length"
            >
              <option v-if="!aiModels.length" value="">当前供应商无模型候选</option>
              <option v-for="model in aiModels" :key="model.id" :value="model.id">{{ model.name }}</option>
            </select>
          </label>
          <label class="space-y-1">
            <div class="text-[11px] text-gray-500">分析模型</div>
            <select
              v-model="aiSelectorModel"
              class="w-full bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-sm text-gray-200"
              :disabled="!aiModels.length"
            >
              <option v-if="!aiModels.length" value="">当前供应商无模型候选</option>
              <option v-for="model in aiModels" :key="`selector-${model.id}`" :value="model.id">{{ model.name }}</option>
            </select>
          </label>
        </div>
        <div class="flex items-center justify-between gap-3 mt-3">
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="provider in aiProviders"
              :key="provider.key"
              class="text-[10px] px-2 py-0.5 rounded-full"
              :class="provider.key === aiProviderStrategy ? 'bg-openclaw/15 text-openclaw' : provider.active ? 'bg-emerald-500/10 text-emerald-400' : provider.preferred ? 'bg-cyan-500/10 text-cyan-400' : 'bg-surface-2 text-gray-500'"
            >
              {{ provider.label }}
            </span>
          </div>
          <button
            class="px-3 py-1.5 rounded-lg text-xs font-medium"
            :class="aiLoading ? 'bg-surface-3 text-gray-500' : 'bg-openclaw/15 text-openclaw hover:bg-openclaw/25'"
            :disabled="aiLoading"
            @click="saveAISettings"
          >
            {{ aiLoading ? '保存中...' : '保存 AI 配置' }}
          </button>
        </div>
      </div>
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-4">
        <div class="text-sm font-medium text-gray-200 mb-2">本轮采集策略</div>
        <div class="space-y-2 text-xs text-gray-400 leading-relaxed">
          <div>统计挖掘先生成候选模式，再交给 AI 做语义聚合和过滤。</div>
          <div>如果选择 `仅本地启发式`，会退回规则聚合，不会调用外部模型。</div>
          <div>会话分析按钮和日报摘要会统一走这里的 provider/model 配置。</div>
        </div>
      </div>
    </div>

    <!-- 四层架构步骤条 -->
    <div class="bg-surface-1 rounded-xl border border-surface-3 p-5 gradient-border">
      <div class="text-sm font-medium mb-4 text-gray-300">ShrimpFlow 四层架构 · 四大战略方向</div>
      <div class="grid grid-cols-4 gap-3">
        <div class="relative bg-surface-2 rounded-xl p-4 border border-accent/30 cursor-pointer hover:scale-[1.02] hover:shadow-lg hover:shadow-accent/10 transition-all" @click="router.push('/layer/shadow')">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center">
              <svg class="w-4 h-4 text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" /></svg>
            </div>
            <span class="text-xs font-medium text-accent">Layer 1</span>
          </div>
          <div class="text-[11px] font-medium text-accent/90 leading-tight">方向1 · Skill Workflow 挖掘</div>
          <div class="text-sm font-semibold text-gray-200 mt-1">Shadow</div>
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
          <div class="text-[11px] font-medium text-openclaw/90 leading-tight">方向2 · Skill 发掘推荐</div>
          <div class="text-sm font-semibold text-gray-200 mt-1">Mirror</div>
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
          <div class="text-[11px] font-medium text-purple-300/90 leading-tight">方向3 · 人参与行为建模</div>
          <div class="text-sm font-semibold text-gray-200 mt-1">Brain</div>
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
          <div class="text-[11px] font-medium text-emerald-300/90 leading-tight">方向4 · Claw the Claw 自主体</div>
          <div class="text-sm font-semibold text-gray-200 mt-1">Autopilot</div>
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
                :class="source === 'openclaw' ? 'bg-openclaw' : source === 'terminal' ? 'bg-terminal' : source === 'git' ? 'bg-git' : source === 'claude_code' ? 'bg-claude' : source === 'codex' ? 'bg-cyan-300' : source === 'cursor' ? 'bg-emerald-400' : source === 'vscode' ? 'bg-sky-400' : 'bg-env'"
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
              :class="event.source === 'openclaw' ? 'bg-openclaw' : event.source === 'terminal' ? 'bg-terminal' : event.source === 'git' ? 'bg-git' : event.source === 'claude_code' ? 'bg-claude' : event.source === 'codex' ? 'bg-cyan-300' : event.source === 'cursor' ? 'bg-emerald-400' : event.source === 'vscode' ? 'bg-sky-400' : 'bg-env'"
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
                :class="(session.origin ?? 'openclaw') === 'claude_code' ? 'bg-blue-500/20' : (session.origin ?? 'openclaw') === 'codex' ? 'bg-cyan-300/20' : (session.origin ?? 'openclaw') === 'cursor' ? 'bg-emerald-500/20' : (session.origin ?? 'openclaw') === 'vscode' ? 'bg-sky-500/20' : 'bg-openclaw/20'"
              >
                <span
                  class="text-[8px] font-bold"
                  :class="(session.origin ?? 'openclaw') === 'claude_code' ? 'text-blue-400' : (session.origin ?? 'openclaw') === 'codex' ? 'text-cyan-300' : (session.origin ?? 'openclaw') === 'cursor' ? 'text-emerald-400' : (session.origin ?? 'openclaw') === 'vscode' ? 'text-sky-400' : 'text-openclaw'"
                >
                  {{ (session.origin ?? 'openclaw') === 'claude_code' ? 'CC' : (session.origin ?? 'openclaw') === 'codex' ? 'CX' : (session.origin ?? 'openclaw') === 'cursor' ? 'CU' : (session.origin ?? 'openclaw') === 'vscode' ? 'VS' : 'OC' }}
                </span>
              </div>
              <span class="text-xs text-gray-200 truncate">{{ session.display_title ?? session.title }}</span>
            </div>
            <div class="text-[10px] text-gray-500 line-clamp-2">{{ session.display_summary ?? session.summary }}</div>
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

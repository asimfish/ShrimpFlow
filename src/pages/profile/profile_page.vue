<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

import type { StatsOverview, BehaviorPattern, ClawProfile } from '@/types'
import { useEventsStore } from '@/stores/events'
import { useSkillsStore } from '@/stores/skills'
import { getStatsApi } from '@/http_api/stats'
import { getPatternsApi } from '@/http_api/patterns'
import { activateProfileApi, getActiveProfileApi, getProfilesApi } from '@/http_api/profiles'

const eventsStore = useEventsStore()
const skillsStore = useSkillsStore()

const stats = ref<StatsOverview | null>(null)
const patterns = ref<BehaviorPattern[]>([])
const profiles = ref<ClawProfile[]>([])
const activeProfile = ref<ClawProfile | null>(null)
const profilesLoading = ref(false)
const profilesError = ref<string | null>(null)
const activatingProfileId = ref<number | null>(null)

onMounted(async () => {
  const [sRes, pRes] = await Promise.all([getStatsApi(), getPatternsApi()])
  if (sRes.data) stats.value = sRes.data
  if (pRes.data) patterns.value = pRes.data
  await loadProfiles()
})

const loadProfiles = async () => {
  profilesLoading.value = true
  profilesError.value = null
  const [profilesRes, activeRes] = await Promise.all([getProfilesApi(), getActiveProfileApi()])
  if (profilesRes.data) profiles.value = profilesRes.data
  else profilesError.value = profilesRes.error ?? 'ClawProfile 列表加载失败'
  if (activeRes.data) activeProfile.value = activeRes.data
  else if (!profilesError.value) profilesError.value = activeRes.error ?? 'Active ClawProfile 加载失败'
  profilesLoading.value = false
}

const activateProfile = async (profileId: number) => {
  activatingProfileId.value = profileId
  const result = await activateProfileApi(profileId)
  activatingProfileId.value = null
  if (result.data) {
    activeProfile.value = result.data
    profiles.value = profiles.value.map(profile => ({
      ...profile,
      is_active: profile.id === result.data!.id,
    }))
  } else {
    profilesError.value = result.error ?? '激活 ClawProfile 失败'
  }
}

const now = Math.floor(Date.now() / 1000)
const DAY = 86400

// 开发者类型分析
const devType = computed(() => {
  const counts = { research: 0, engineering: 0, ops: 0 }
  for (const e of eventsStore.events) {
    if (e.source === 'openclaw' || e.tags.some(t => ['paper', 'experiment', 'learning'].includes(t))) counts.research++
    else if (e.source === 'git' || e.source === 'claude_code' || e.source === 'codex' || e.tags.some(t => ['feature', 'bugfix', 'refactor'].includes(t))) counts.engineering++
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
  const ocEvents = eventsStore.events.filter(e => e.source === 'openclaw' || e.source === 'claude_code' || e.source === 'codex').length
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
  const thisAI = thisWeek.filter(e => e.source === 'openclaw' || e.source === 'claude_code' || e.source === 'codex').length
  const lastAI = lastWeek.filter(e => e.source === 'openclaw' || e.source === 'claude_code' || e.source === 'codex').length
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

    <div class="bg-surface-1 rounded-2xl border border-openclaw/20 p-6 space-y-4">
      <div class="flex items-start justify-between gap-6">
        <div>
          <div class="text-sm font-medium text-gray-200">Active ClawProfile</div>
          <div class="text-xs text-gray-500 mt-1">当前系统用于 OpenClaw/Claude 会话分析与模式注入的核心档案</div>
        </div>
        <button class="text-xs text-accent hover:text-accent-glow" @click="loadProfiles">刷新</button>
      </div>

      <div v-if="profilesLoading" class="text-sm text-gray-500">正在加载 ClawProfile...</div>
      <div v-else-if="profilesError" class="text-sm text-red-300">{{ profilesError }}</div>
      <div v-else-if="activeProfile" class="grid grid-cols-[1.4fr_1fr] gap-4">
        <div class="bg-surface-2 rounded-xl border border-surface-3 p-4">
          <div class="flex items-center gap-2 mb-2">
            <span class="text-xs px-2 py-0.5 rounded-full bg-openclaw/15 text-openclaw">{{ activeProfile.trust || 'local' }}</span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400">active</span>
          </div>
          <div class="text-lg font-semibold text-gray-100">{{ activeProfile.display }}</div>
          <div class="text-xs text-gray-500 mt-1 font-mono">{{ activeProfile.name }}</div>
          <div class="text-sm text-gray-400 mt-3 leading-relaxed">{{ activeProfile.description || '暂无描述' }}</div>
          <div class="flex flex-wrap gap-2 mt-3">
            <span v-for="tag in activeProfile.tags" :key="tag" class="text-[10px] px-2 py-0.5 rounded-full bg-surface-3 text-gray-400">
              {{ tag }}
            </span>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div class="bg-surface-2 rounded-xl border border-surface-3 p-4">
            <div class="text-[11px] text-gray-500">模式数</div>
            <div class="text-2xl font-semibold text-accent mt-1">{{ activeProfile.pattern_count }}</div>
          </div>
          <div class="bg-surface-2 rounded-xl border border-surface-3 p-4">
            <div class="text-[11px] text-gray-500">工作流数</div>
            <div class="text-2xl font-semibold text-openclaw mt-1">{{ activeProfile.workflow_count }}</div>
          </div>
          <div class="bg-surface-2 rounded-xl border border-surface-3 p-4 col-span-2">
            <div class="text-[11px] text-gray-500 mb-1">注入策略</div>
            <div class="text-sm text-gray-300">
              mode={{ activeProfile.injection?.mode || 'proactive' }} · budget={{ activeProfile.injection?.budget ?? 'unlimited' }}
            </div>
          </div>
        </div>
      </div>

      <div class="space-y-2">
        <div class="text-xs text-gray-500">可切换的 ClawProfile</div>
        <div class="grid grid-cols-2 gap-3">
          <div
            v-for="profile in profiles"
            :key="profile.id"
            class="bg-surface-2 rounded-xl border p-4"
            :class="profile.is_active ? 'border-emerald-500/30' : 'border-surface-3'"
          >
            <div class="flex items-center justify-between gap-3">
              <div>
                <div class="text-sm font-medium text-gray-200">{{ profile.display }}</div>
                <div class="text-[10px] text-gray-500 font-mono mt-1">{{ profile.name }}</div>
              </div>
              <button
                class="px-2.5 py-1 rounded-lg text-[10px] font-medium"
                :class="profile.is_active ? 'bg-emerald-500/15 text-emerald-400 cursor-default' : 'bg-accent/15 text-accent hover:bg-accent/25'"
                :disabled="profile.is_active || activatingProfileId === profile.id"
                @click="activateProfile(profile.id)"
              >
                {{ profile.is_active ? '已激活' : activatingProfileId === profile.id ? '切换中...' : '设为 Active' }}
              </button>
            </div>
            <div class="text-xs text-gray-400 mt-2 line-clamp-2">{{ profile.description || '暂无描述' }}</div>
          </div>
        </div>
      </div>
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
            <span class="text-xs px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-400">连续活跃 {{ stats?.streak_days }} 天</span>
          </div>
        </div>
        <!-- 统计 -->
        <div class="flex gap-6 text-center">
          <div>
            <div class="text-2xl font-bold">{{ stats?.total_events.toLocaleString() }}</div>
            <div class="text-[10px] text-gray-500 mt-0.5">总事件</div>
          </div>
          <div>
            <div class="text-2xl font-bold text-openclaw">{{ stats?.total_openclaw_sessions }}</div>
            <div class="text-[10px] text-gray-500 mt-0.5">AI 交互</div>
          </div>
          <div>
            <div class="text-2xl font-bold">{{ stats?.total_skills }}</div>
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
        <div v-for="p in patterns.filter(p => p.confidence >= 70).slice(0, 6)" :key="p.id"
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

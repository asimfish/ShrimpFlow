<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import type { StatsOverview } from '@/types'
import { getStatsApi } from '@/http_api/stats'

import { useEventsStore } from '@/stores/events'
import { useSkillsStore } from '@/stores/skills'

const eventsStore = useEventsStore()
const skillsStore = useSkillsStore()
const stats = ref<StatsOverview | null>(null)

onMounted(async () => {
  const res = await getStatsApi()
  if (res.data) stats.value = res.data
})

// 开发者画像数据
const profile = {
  direction: '具身智能',
  skills: 'Python / PyTorch / ROS2',
  activeHours: '9:00 - 22:00',
}

// 每周每小时活跃热力图数据 (7天 x 24小时)
const weekDays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const heatmapData = computed(() => {
  const grid: number[][] = Array.from({ length: 7 }, () => Array(24).fill(0))
  for (const e of eventsStore.events) {
    const d = new Date(e.timestamp * 1000)
    const day = (d.getDay() + 6) % 7
    const hour = d.getHours()
    grid[day][hour]++
  }
  return grid
})

const maxHeatValue = computed(() => {
  let max = 1
  for (const row of heatmapData.value) {
    for (const v of row) {
      if (v > max) max = v
    }
  }
  return max
})

const heatColor = (value: number) => {
  if (value === 0) return 'bg-surface-3'
  const ratio = value / maxHeatValue.value
  if (ratio < 0.25) return 'bg-[#22d3ee]/20'
  if (ratio < 0.5) return 'bg-[#22d3ee]/40'
  if (ratio < 0.75) return 'bg-[#22d3ee]/70'
  return 'bg-[#22d3ee]'
}

// 项目参与度雷达图 (5个项目, 正五边形)
const radarProjects = computed(() => {
  const projectNames = ['embodied-nav', 'grasp-policy', 'ros2-workspace', 'paper-reproduce', 'sim2real-transfer']
  const projectLabels = ['导航策略', '抓取策略', 'ROS2工作区', '论文复现', 'Sim2Real']
  const counts = projectNames.map(p => eventsStore.events.filter(e => e.project === p).length)
  const maxCount = Math.max(...counts, 1)
  return projectNames.map((name, i) => ({
    name,
    label: projectLabels[i],
    value: counts[i] / maxCount,
    count: counts[i],
  }))
})

// 正五边形顶点坐标 (中心150,150 半径110)
const radarPoints = (radius: number) => {
  const cx = 150
  const cy = 150
  return Array.from({ length: 5 }, (_, i) => {
    const angle = (Math.PI * 2 * i) / 5 - Math.PI / 2
    return { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) }
  })
}

const radarPolygon = (radius: number) =>
  radarPoints(radius).map(p => `${p.x},${p.y}`).join(' ')

const dataPolygon = computed(() => {
  const cx = 150
  const cy = 150
  const maxR = 110
  return radarProjects.value.map((p, i) => {
    const angle = (Math.PI * 2 * i) / 5 - Math.PI / 2
    const r = maxR * p.value
    return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`
  }).join(' ')
})

const labelPositions = computed(() => {
  const cx = 150
  const cy = 150
  const r = 130
  return radarProjects.value.map((p, i) => {
    const angle = (Math.PI * 2 * i) / 5 - Math.PI / 2
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle), label: p.label, count: p.count }
  })
})

// 技能分类分组
const categoryLabels: Record<string, string> = {
  language: '编程语言',
  framework: '框架/库',
  tool: '工具',
  openclaw: 'AI 辅助',
  vcs: '版本控制',
  devops: '运维',
  network: '网络',
}

const skillsByCategory = computed(() => {
  const map = new Map<string, typeof skillsStore.skills>()
  for (const s of skillsStore.skills) {
    const cat = s.category
    if (!map.has(cat)) map.set(cat, [])
    map.get(cat)!.push(s)
  }
  // 按类别内最高 level 排序
  const entries = [...map.entries()].sort((a, b) => {
    const maxA = Math.max(...a[1].map(s => s.level))
    const maxB = Math.max(...b[1].map(s => s.level))
    return maxB - maxA
  })
  return entries
})

const levelColor = (level: number) => {
  if (level >= 80) return 'bg-[#22d3ee]'
  if (level >= 60) return 'bg-[#22d3ee]/70'
  if (level >= 40) return 'bg-[#22d3ee]/50'
  return 'bg-[#22d3ee]/30'
}

const levelLabel = (level: number) => {
  if (level >= 80) return '精通'
  if (level >= 60) return '熟练'
  if (level >= 40) return '掌握'
  return '了解'
}

// 编码习惯统计
const codingStats = computed(() => {
  const events = eventsStore.events
  const totalDays = 30
  const avgPerDay = Math.round(events.length / totalDays)
  const openclawCount = events.filter(e => e.source === 'openclaw').length
  const openclawRatio = ((openclawCount / events.length) * 100).toFixed(1)
  // 最活跃时段
  const hourCounts = Array(24).fill(0)
  for (const e of events) {
    const h = new Date(e.timestamp * 1000).getHours()
    hourCounts[h]++
  }
  const peakHour = hourCounts.indexOf(Math.max(...hourCounts))
  return { avgPerDay, openclawRatio, peakHour: `${peakHour}:00` }
})
</script>

<template>
  <div class="p-6 space-y-6 overflow-y-auto h-full">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-semibold">Layer 2: Mirror</h1>
      <p class="text-sm text-gray-400 mt-1">可视化开发画像</p>
    </div>

    <!-- 开发者画像卡片 -->
    <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
      <div class="text-sm font-medium mb-4 text-[#22d3ee]">开发者画像</div>
      <div class="grid grid-cols-3 gap-4">
        <div class="bg-surface-2 rounded-lg p-4">
          <div class="text-xs text-gray-500 mb-1">研究方向</div>
          <div class="text-sm font-medium text-gray-200">{{ profile.direction }}</div>
        </div>
        <div class="bg-surface-2 rounded-lg p-4">
          <div class="text-xs text-gray-500 mb-1">主要技能</div>
          <div class="text-sm font-medium text-gray-200">{{ profile.skills }}</div>
        </div>
        <div class="bg-surface-2 rounded-lg p-4">
          <div class="text-xs text-gray-500 mb-1">活跃时段</div>
          <div class="text-sm font-medium text-gray-200">{{ profile.activeHours }}</div>
        </div>
      </div>
      <div class="grid grid-cols-3 gap-4 mt-3">
        <div class="bg-surface-2 rounded-lg p-4">
          <div class="text-xs text-gray-500 mb-1">日均事件</div>
          <div class="text-lg font-bold text-[#22d3ee]">{{ codingStats.avgPerDay }}</div>
        </div>
        <div class="bg-surface-2 rounded-lg p-4">
          <div class="text-xs text-gray-500 mb-1">AI 辅助占比</div>
          <div class="text-lg font-bold text-[#22d3ee]">{{ codingStats.openclawRatio }}%</div>
        </div>
        <div class="bg-surface-2 rounded-lg p-4">
          <div class="text-xs text-gray-500 mb-1">连续活跃</div>
          <div class="text-lg font-bold text-[#22d3ee]">{{ stats?.streak_days }}</div>
        </div>
      </div>
    </div>

    <!-- 编码习惯分析: 每周活跃热力图 -->
    <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
      <div class="text-sm font-medium mb-4">编码习惯 - 每周活跃热力图</div>
      <div class="overflow-x-auto">
        <!-- 小时标签 -->
        <div class="flex items-center gap-0 mb-1 ml-12">
          <div
            v-for="h in 24"
            :key="'h-' + h"
            class="text-[10px] text-gray-600 text-center"
            style="width: 28px; min-width: 28px;"
          >
            {{ h - 1 }}
          </div>
        </div>
        <!-- 热力图网格 -->
        <div v-for="(row, dayIdx) in heatmapData" :key="'day-' + dayIdx" class="flex items-center gap-0">
          <div class="text-[10px] text-gray-500 w-12 shrink-0 text-right pr-2">{{ weekDays[dayIdx] }}</div>
          <div
            v-for="(val, hourIdx) in row"
            :key="'cell-' + dayIdx + '-' + hourIdx"
            class="rounded-sm transition-colors"
            :class="heatColor(val)"
            :title="`${weekDays[dayIdx]} ${hourIdx}:00 - ${val} 个事件`"
            style="width: 26px; height: 26px; min-width: 26px; margin: 1px;"
          />
        </div>
        <!-- 图例 -->
        <div class="flex items-center gap-2 mt-3 ml-12">
          <span class="text-[10px] text-gray-500">少</span>
          <div class="w-4 h-4 rounded-sm bg-surface-3" />
          <div class="w-4 h-4 rounded-sm bg-[#22d3ee]/20" />
          <div class="w-4 h-4 rounded-sm bg-[#22d3ee]/40" />
          <div class="w-4 h-4 rounded-sm bg-[#22d3ee]/70" />
          <div class="w-4 h-4 rounded-sm bg-[#22d3ee]" />
          <span class="text-[10px] text-gray-500">多</span>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <!-- 项目参与度雷达图 -->
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
        <div class="text-sm font-medium mb-4">项目参与度</div>
        <div class="flex justify-center">
          <svg viewBox="0 0 300 300" class="w-72 h-72">
            <!-- 背景网格 -->
            <polygon :points="radarPolygon(110)" fill="none" stroke="#242438" stroke-width="1" />
            <polygon :points="radarPolygon(82)" fill="none" stroke="#242438" stroke-width="1" />
            <polygon :points="radarPolygon(55)" fill="none" stroke="#242438" stroke-width="1" />
            <polygon :points="radarPolygon(27)" fill="none" stroke="#242438" stroke-width="1" />
            <!-- 轴线 -->
            <line
              v-for="(pt, i) in radarPoints(110)"
              :key="'axis-' + i"
              x1="150" y1="150"
              :x2="pt.x" :y2="pt.y"
              stroke="#242438" stroke-width="1"
            />
            <!-- 数据区域 -->
            <polygon
              :points="dataPolygon"
              fill="rgba(34, 211, 238, 0.15)"
              stroke="#22d3ee"
              stroke-width="2"
            />
            <!-- 数据点 -->
            <circle
              v-for="(pt, i) in radarPoints(110).map((p, idx) => {
                const val = radarProjects[idx].value
                return {
                  x: 150 + (p.x - 150) * val,
                  y: 150 + (p.y - 150) * val,
                }
              })"
              :key="'dot-' + i"
              :cx="pt.x" :cy="pt.y" r="4"
              fill="#22d3ee"
            />
            <!-- 标签 -->
            <text
              v-for="(lp, i) in labelPositions"
              :key="'label-' + i"
              :x="lp.x" :y="lp.y"
              text-anchor="middle"
              dominant-baseline="middle"
              class="text-[11px] fill-gray-400"
            >
              {{ lp.label }}
            </text>
          </svg>
        </div>
        <!-- 项目事件数列表 -->
        <div class="space-y-2 mt-2">
          <div v-for="p in radarProjects" :key="p.name" class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full bg-[#22d3ee]" />
            <span class="text-xs text-gray-300 flex-1">{{ p.label }}</span>
            <span class="text-xs text-gray-500 font-mono">{{ p.count }} 事件</span>
          </div>
        </div>
      </div>

      <!-- 技术栈分布 -->
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
        <div class="text-sm font-medium mb-4">技术栈分布</div>
        <div class="space-y-5">
          <div v-for="[category, skills] in skillsByCategory" :key="category">
            <div class="text-xs text-[#22d3ee] mb-2">{{ categoryLabels[category] ?? category }}</div>
            <div class="space-y-2">
              <div v-for="skill in skills" :key="skill.id" class="flex items-center gap-3">
                <div class="w-20 text-xs text-gray-300 font-mono truncate">{{ skill.name }}</div>
                <div class="flex-1 h-2 bg-surface-3 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all"
                    :class="levelColor(skill.level)"
                    :style="{ width: `${skill.level}%` }"
                  />
                </div>
                <div class="text-[10px] text-gray-500 w-8 text-right">{{ skill.level }}</div>
                <div class="text-[10px] w-8 text-right" :class="skill.level >= 80 ? 'text-[#22d3ee]' : 'text-gray-500'">
                  {{ levelLabel(skill.level) }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

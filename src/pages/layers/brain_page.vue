<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useEventsStore } from '@/stores/events'
import { mockPatterns } from '@/mock/data'
import { mineAllPatterns } from '@/utils/pattern_mining'
import type { BehaviorPattern } from '@/types'
import type { MinedPattern } from '@/utils/pattern_mining'

const router = useRouter()
const eventsStore = useEventsStore()

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

const statusColorMap: Record<string, string> = {
  learning: 'bg-yellow-500/20 text-yellow-400',
  confirmed: 'bg-blue-500/20 text-blue-400',
  exportable: 'bg-emerald-500/20 text-emerald-400',
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
  mockPatterns.filter((p: BehaviorPattern) => p.status === 'learning')
)

const confirmedPatterns = computed(() =>
  mockPatterns.filter((p: BehaviorPattern) => p.status === 'confirmed')
)

const exportablePatterns = computed(() =>
  mockPatterns.filter((p: BehaviorPattern) => p.status === 'exportable')
)

const handleClickPattern = (pattern: BehaviorPattern) => {
  router.push(`/patterns/${pattern.id}`)
}
</script>

<template>
  <div class="p-6 space-y-6 overflow-y-auto h-full">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-semibold">Layer 3: Brain</h1>
      <p class="text-sm text-gray-400 mt-1">从开发行为中自动学习模式 · 已分析 {{ eventsStore.events.length }} 个事件</p>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import type { BehaviorPattern, MemoryHealth } from '@/types'
import { getMemoryHealthApi, runFullCycleApi } from '@/http_api/stats'
import type { FullCycleReport } from '@/http_api/stats'
import { recallPatternsApi, getPatternRelationsApi } from '@/http_api/patterns'
import type { RecallResult, PatternRelationItem } from '@/http_api/patterns'
import { usePatternsStore } from '@/stores/patterns'

const router = useRouter()
const patternsStore = usePatternsStore()

const health = ref<MemoryHealth | null>(null)
const healthLoading = ref(false)
const cycleRunning = ref(false)
const cycleReport = ref<FullCycleReport | null>(null)
const recallQuery = ref('')
const recalling = ref(false)
const recallResult = ref<RecallResult | null>(null)
const activeTab = ref<'overview' | 'recall' | 'patterns'>('overview')
const selectedPattern = ref<BehaviorPattern | null>(null)
const selectedRelations = ref<PatternRelationItem[]>([])
const relationsLoading = ref(false)
const sortBy = ref<'heat' | 'confidence' | 'access'>('heat')
const lifecycleFilter = ref<string>('')
const terminalLines = ref<{ text: string; cls: string }[]>([])
const terminalVisible = ref(false)

// Terminal log helpers
const tPush = (text: string, cls = 'dim') => { terminalLines.value.push({ text, cls }) }
const tHeader = (text: string) => tPush(`\n  ${text}`, 'header')
const tRow = (label: string, before: string | number, after: string | number, change: string) => {
  const pad = (s: string, n: number) => s.length >= n ? s : s + ' '.repeat(n - s.length)
  tPush(`  ${pad(String(label), 10)} ${pad(String(before), 8)} ${pad(String(after), 8)} ${change}`, change.startsWith('+') ? 'green' : change.startsWith('-') ? 'red' : 'dim')
}
const tTable = (label: string, value: string, cls = 'white') => {
  const pad = (s: string, n: number) => s.length >= n ? s : s + ' '.repeat(n - s.length)
  tPush(`  ${pad(label, 12)} ${value}`, cls)
}

const loadHealth = async () => {
  healthLoading.value = true
  const res = await getMemoryHealthApi()
  healthLoading.value = false
  if (res.data) health.value = res.data
}

const handleFullCycle = async () => {
  cycleRunning.value = true
  cycleReport.value = null
  terminalLines.value = []
  terminalVisible.value = true

  tPush('neural-memory - full_cycle(action: "consolidate")', 'accent')
  tPush('  running...', 'dim')

  const res = await runFullCycleApi()
  cycleRunning.value = false

  if (!res.data) {
    tPush('  [ERROR] cycle failed', 'red')
    return
  }

  const r = res.data
  cycleReport.value = r
  terminalLines.value = []

  // Header
  tPush(`neural-memory - full_cycle completed in ${r.elapsed_seconds}s`, 'accent')

  // Health Report
  tHeader('健康报告')
  tPush('  ' + '─'.repeat(44), 'dim')
  tPush(`  ${'指标'.padEnd(10)} ${'之前'.padEnd(8)} ${'之后'.padEnd(8)} 变化`, 'label')
  tPush('  ' + '─'.repeat(44), 'dim')
  for (const [key, diff] of Object.entries(r.health_diff)) {
    const labels: Record<string, string> = { grade: '评级', score: '分数', avg_heat: '平均热度', total: '模式总数', confirmed: '已确认' }
    tRow(labels[key] ?? key, diff.before, diff.after, diff.change)
  }
  tPush('  ' + '─'.repeat(44), 'dim')

  // Lifecycle diff
  tHeader('生命周期变迁')
  tPush('  ' + '─'.repeat(44), 'dim')
  tPush(`  ${'状态'.padEnd(10)} ${'之前'.padEnd(8)} ${'之后'.padEnd(8)} 变化`, 'label')
  tPush('  ' + '─'.repeat(44), 'dim')
  const lcLabels: Record<string, string> = { active: '活跃', warm: '温热', cool: '冷却', compressed: '压缩', archived: '归档' }
  for (const [state, diff] of Object.entries(r.lifecycle_diff)) {
    tRow(lcLabels[state] ?? state, diff.before, diff.after, diff.change)
  }
  tPush('  ' + '─'.repeat(44), 'dim')

  // Consolidation summary
  tHeader('巩固执行摘要')
  tPush('  ' + '─'.repeat(50), 'dim')
  tPush(`  ${'策略'.padEnd(12)} 效果`, 'label')
  tPush('  ' + '─'.repeat(50), 'dim')
  const pruned = r.consolidation.prune.pruned
  tTable('prune', pruned > 0 ? `修剪 ${pruned} 个低质量模式` : '无需修剪', pruned > 0 ? 'yellow' : 'dim')
  const merged = r.consolidation.merge.merged
  const mergeDetail = r.consolidation.merge.pairs.map(p => `#${p.winner}<-#${p.loser}`).join(', ')
  tTable('merge', merged > 0 ? `合并 ${merged} 对重复模式 (${mergeDetail})` : '无重复模式', merged > 0 ? 'cyan' : 'dim')
  const matured = r.consolidation.mature.matured
  tTable('mature', matured > 0 ? `晋升 ${matured} 个高质量模式为 confirmed` : '暂无可晋升的模式', matured > 0 ? 'green' : 'dim')
  tPush('  ' + '─'.repeat(50), 'dim')

  // Relations
  tHeader('关系发现')
  const rl = r.relations
  tTable('similar', `${rl.similar} 条相似关系`, rl.similar > 0 ? 'purple' : 'dim')
  tTable('temporal', `${rl.temporal} 条时序关系`, rl.temporal > 0 ? 'cyan' : 'dim')
  tTable('confirmation', `${rl.confirmation} 条确认链`, rl.confirmation > 0 ? 'blue' : 'dim')
  tTable('co_occurrence', `${rl.co_occurrence} 条共现关系`, rl.co_occurrence > 0 ? 'green' : 'dim')

  // Compression
  if (r.compression.total_compressed > 0) {
    tHeader('证据压缩')
    tPush(`  压缩 ${r.compression.total_compressed} 条旧证据 (${r.compression.patterns_processed} 个模式)`, 'yellow')
  }

  // Decay
  tHeader('衰减')
  tPush(`  ${r.decay.decayed} 个模式热度变更, ${r.decay.lifecycle_changes} 个状态迁移`, r.decay.lifecycle_changes > 0 ? 'yellow' : 'dim')

  // Bottlenecks
  if (r.bottlenecks.length) {
    tHeader('主要瓶颈')
    r.bottlenecks.forEach((b, i) => {
      const cls = b.metric === 'clean' ? 'green' : 'yellow'
      tPush(`  ${i + 1}. ${b.metric} = ${b.value} — ${b.desc}`, cls)
    })
  }

  tPush('', 'dim')

  await loadHealth()
  await patternsStore.fetchPatterns(undefined, true)
}

const handleRecall = async () => {
  if (!recallQuery.value.trim()) return
  recalling.value = true
  recallResult.value = null
  const res = await recallPatternsApi(recallQuery.value.trim())
  recalling.value = false
  if (res.data) recallResult.value = res.data
}

const selectPattern = async (p: BehaviorPattern) => {
  selectedPattern.value = p
  relationsLoading.value = true
  const res = await getPatternRelationsApi(p.id)
  relationsLoading.value = false
  selectedRelations.value = res.data ?? []
}

const goToPattern = (id: number) => router.push(`/patterns/${id}`)

const sortedPatterns = computed(() => {
  let list = [...patternsStore.patterns]
  if (lifecycleFilter.value) list = list.filter(p => (p as any).lifecycle_state === lifecycleFilter.value)
  if (sortBy.value === 'heat') list.sort((a, b) => ((b as any).heat_score ?? 0) - ((a as any).heat_score ?? 0))
  else if (sortBy.value === 'confidence') list.sort((a, b) => b.confidence - a.confidence)
  else list.sort((a, b) => ((b as any).access_count ?? 0) - ((a as any).access_count ?? 0))
  return list.slice(0, 50)
})

const lifecycleStats = computed(() => {
  const s: Record<string, number> = { active: 0, warm: 0, cool: 0, compressed: 0, archived: 0 }
  for (const p of patternsStore.patterns) { const st = (p as any).lifecycle_state ?? 'active'; s[st] = (s[st] ?? 0) + 1 }
  return s
})

const totalPatterns = computed(() => patternsStore.patterns.length)
const gradeColor = (g: string) => ({ A: 'text-emerald-400', B: 'text-blue-400', C: 'text-amber-400', D: 'text-orange-400' }[g] ?? 'text-red-400')

const lcfg: Record<string, { label: string; color: string; bg: string }> = {
  active: { label: '活跃', color: 'text-emerald-400', bg: 'bg-emerald-500' },
  warm: { label: '温热', color: 'text-amber-400', bg: 'bg-amber-400' },
  cool: { label: '冷却', color: 'text-blue-400', bg: 'bg-blue-400' },
  compressed: { label: '压缩', color: 'text-gray-400', bg: 'bg-gray-400' },
  archived: { label: '归档', color: 'text-gray-600', bg: 'bg-gray-600' },
}

const relTypeStyle: Record<string, { label: string; cls: string }> = {
  CAUSED_BY: { label: '因果', cls: 'text-red-400 bg-red-500/10' },
  LEADS_TO: { label: '导致', cls: 'text-blue-400 bg-blue-500/10' },
  FOLLOWS: { label: '跟随', cls: 'text-cyan-400 bg-cyan-500/10' },
  CONTRADICTS: { label: '冲突', cls: 'text-orange-400 bg-orange-500/10' },
  SIMILAR_TO: { label: '相似', cls: 'text-purple-400 bg-purple-500/10' },
  REINFORCES: { label: '强化', cls: 'text-emerald-400 bg-emerald-500/10' },
}

const heatBarColor = (h: number) => h >= 60 ? 'bg-emerald-500' : h >= 30 ? 'bg-amber-400' : 'bg-gray-500'

onMounted(async () => {
  await patternsStore.ensurePatternsLoaded()
  await loadHealth()
})
</script>

<template>
  <div class="flex h-full overflow-hidden">
    <!-- Left Main -->
    <div class="flex-1 overflow-y-auto p-6 space-y-5">
      <!-- Header + Tabs -->
      <div class="flex items-end justify-between">
        <div>
          <h1 class="text-xl font-semibold">Memory System</h1>
          <p class="text-xs text-gray-500 mt-0.5">{{ totalPatterns }} 模式 · NeuralMemory</p>
        </div>
        <div class="flex items-center gap-3">
          <div class="flex gap-1 bg-surface-2 rounded-lg p-0.5">
            <button v-for="t in ([{ key: 'overview', label: '总览' }, { key: 'recall', label: '召回' }, { key: 'patterns', label: '模式' }] as const)" :key="t.key" class="px-3 py-1.5 text-xs rounded-md transition-all" :class="activeTab === t.key ? 'bg-surface-1 text-white shadow-sm' : 'text-gray-500 hover:text-gray-300'" @click="activeTab = t.key">{{ t.label }}</button>
          </div>
          <button class="px-4 py-2 text-xs font-medium rounded-lg transition-all shrink-0" :class="cycleRunning ? 'bg-surface-2 text-gray-500' : 'bg-accent/20 text-accent hover:bg-accent/30 active:scale-95'" :disabled="cycleRunning" @click="handleFullCycle">
            {{ cycleRunning ? '巩固中...' : '每日巩固' }}
          </button>
        </div>
      </div>

      <!-- Tab: Overview -->
      <template v-if="activeTab === 'overview'">
        <!-- Health Hero -->
        <div v-if="health" class="relative overflow-hidden rounded-xl border border-surface-3 bg-gradient-to-br from-surface-1 to-surface-2 p-6">
          <div class="flex items-center gap-8">
            <div class="relative w-28 h-28 shrink-0">
              <svg viewBox="0 0 120 120" class="w-full h-full -rotate-90">
                <circle cx="60" cy="60" r="52" fill="none" stroke-width="6" class="stroke-surface-3" />
                <circle cx="60" cy="60" r="52" fill="none" stroke-width="6" stroke-linecap="round" :stroke-dasharray="`${health.score * 3.267} 326.7`" :class="{ 'stroke-emerald-400': health.grade === 'A', 'stroke-blue-400': health.grade === 'B', 'stroke-amber-400': health.grade === 'C', 'stroke-orange-400': health.grade === 'D', 'stroke-red-400': health.grade === 'F' }" class="transition-all duration-1000" />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span :class="gradeColor(health.grade)" class="text-3xl font-bold leading-none">{{ health.grade }}</span>
                <span class="text-xs text-gray-500 mt-0.5">{{ health.score }}pts</span>
              </div>
            </div>
            <div class="flex-1 space-y-2.5">
              <div v-for="dim in [
                { key: 'heat', label: '热度', max: 30, color: 'bg-red-400', desc: '模式活跃程度' },
                { key: 'vitality', label: '活力', max: 25, color: 'bg-emerald-400', desc: '活跃模式占比' },
                { key: 'evidence', label: '证据', max: 20, color: 'bg-blue-400', desc: '证据支撑覆盖' },
                { key: 'freshness', label: '新鲜', max: 15, color: 'bg-cyan-400', desc: '近期访问率' },
                { key: 'confirmation', label: '确认', max: 10, color: 'bg-amber-400', desc: '用户确认率' },
              ]" :key="dim.key" class="group flex items-center gap-3">
                <span class="text-[11px] text-gray-400 w-8 shrink-0">{{ dim.label }}</span>
                <div class="flex-1 h-2.5 bg-surface-3/60 rounded-full overflow-hidden">
                  <div class="h-full rounded-full transition-all duration-700" :class="dim.color" :style="{ width: `${((health.breakdown as any)[dim.key] / dim.max) * 100}%` }" />
                </div>
                <span class="text-[10px] text-gray-500 w-12 text-right tabular-nums">{{ (health.breakdown as any)[dim.key] }}/{{ dim.max }}</span>
                <span class="text-[10px] text-gray-600 w-20 opacity-0 group-hover:opacity-100 transition-opacity">{{ dim.desc }}</span>
              </div>
            </div>
          </div>
          <div v-if="health.issues.length" class="mt-4 pt-3 border-t border-surface-3/50 flex flex-wrap gap-2">
            <span v-for="(issue, i) in health.issues" :key="i" class="px-2 py-1 rounded text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/20">{{ issue }}</span>
          </div>
        </div>

        <!-- Lifecycle cards -->
        <div class="grid grid-cols-5 gap-3">
          <button v-for="state in (['active', 'warm', 'cool', 'compressed', 'archived'] as const)" :key="state" class="relative bg-surface-1 rounded-lg border border-surface-3 p-4 text-center hover:border-accent/30 transition-all cursor-pointer" :class="lifecycleFilter === state ? 'ring-1 ring-accent/40' : ''" @click="lifecycleFilter = lifecycleFilter === state ? '' : state; activeTab = 'patterns'">
            <div class="text-2xl font-bold tabular-nums" :class="lcfg[state]?.color ?? 'text-gray-400'">{{ lifecycleStats[state] ?? 0 }}</div>
            <div class="text-[10px] text-gray-500 mt-0.5">{{ lcfg[state]?.label ?? state }}</div>
            <div class="absolute top-2 right-2 w-1.5 h-1.5 rounded-full opacity-60" :class="lcfg[state]?.bg ?? 'bg-gray-500'" />
          </button>
        </div>

        <!-- Terminal Log -->
        <div v-if="terminalVisible" class="terminal-panel rounded-xl border border-surface-3 overflow-hidden">
          <div class="flex items-center justify-between px-4 py-2 bg-[#1a1a2e] border-b border-surface-3">
            <div class="flex items-center gap-2">
              <div class="flex gap-1.5">
                <div class="w-3 h-3 rounded-full bg-red-500/80" />
                <div class="w-3 h-3 rounded-full bg-amber-500/80" />
                <div class="w-3 h-3 rounded-full bg-emerald-500/80" />
              </div>
              <span class="text-[11px] text-gray-500 ml-2 font-mono">memory-consolidation</span>
            </div>
            <button class="text-gray-600 hover:text-gray-400 text-xs" @click="terminalVisible = false">关闭</button>
          </div>
          <div class="bg-[#0d0d1a] px-4 py-3 max-h-[420px] overflow-y-auto font-mono text-[12px] leading-[1.7] terminal-scroll">
            <div v-if="cycleRunning" class="text-gray-500 animate-pulse">running consolidation cycle...</div>
            <div v-for="(line, i) in terminalLines" :key="i" :class="{ 'text-gray-600': line.cls === 'dim', 'text-gray-200': line.cls === 'white', 'text-emerald-400': line.cls === 'green', 'text-red-400': line.cls === 'red', 'text-amber-400': line.cls === 'yellow', 'text-cyan-400': line.cls === 'cyan', 'text-purple-400': line.cls === 'purple', 'text-blue-400': line.cls === 'blue', 'text-accent': line.cls === 'accent', 'text-gray-400 font-semibold': line.cls === 'header', 'text-gray-500': line.cls === 'label' }" class="whitespace-pre">{{ line.text }}</div>
          </div>
        </div>
        <div v-else-if="!terminalVisible && !cycleReport" class="text-center py-8">
          <p class="text-sm text-gray-600">点击右上角"每日巩固"执行完整记忆维护周期</p>
          <p class="text-[10px] text-gray-700 mt-1">衰减 + 修剪 + 去重 + 晋升 + 关系发现 + 证据压缩</p>
        </div>
      </template>

      <!-- Tab: Recall -->
      <template v-if="activeTab === 'recall'">
        <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
          <div class="flex gap-2 mb-5">
            <div class="relative flex-1">
              <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
              <input v-model="recallQuery" type="text" placeholder="输入关键词，沿关系图谱扩散搜索..." class="w-full bg-surface-2 border border-surface-3 rounded-lg pl-10 pr-3 py-2.5 text-sm text-gray-200 placeholder-gray-600 outline-none focus:border-accent/40 transition-colors" @keydown.enter="handleRecall" />
            </div>
            <button class="px-5 py-2.5 text-xs font-medium rounded-lg bg-accent/20 text-accent hover:bg-accent/30 active:scale-95 transition-all shrink-0 disabled:opacity-40" :disabled="recalling || !recallQuery.trim()" @click="handleRecall">{{ recalling ? '...' : 'Recall' }}</button>
          </div>
          <div v-if="!recallResult" class="text-center py-12">
            <svg class="w-12 h-12 mx-auto text-gray-700 mb-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-2.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7z" /><line x1="9" y1="21" x2="15" y2="21" /></svg>
            <p class="text-sm text-gray-600">输入关键词触发扩散激活</p>
          </div>
          <div v-if="recallResult" class="space-y-4">
            <div>
              <div class="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Seeds ({{ recallResult.seeds.length }})</div>
              <div class="flex flex-wrap gap-2">
                <button v-for="s in recallResult.seeds" :key="s.pattern_id" class="px-3 py-1.5 rounded-lg text-xs bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20 transition-colors" @click="goToPattern(s.pattern_id)">{{ s.name }} <span class="opacity-50">{{ s.confidence }}%</span></button>
              </div>
            </div>
            <div v-if="recallResult.activated.length">
              <div class="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Activated ({{ recallResult.total }})</div>
              <div class="space-y-1.5">
                <button v-for="a in recallResult.activated" :key="a.pattern_id" class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-surface-2 hover:bg-surface-3 transition-colors text-left" @click="goToPattern(a.pattern_id)">
                  <div class="w-2 h-2 rounded-full shrink-0" :class="lcfg[a.lifecycle_state]?.bg ?? 'bg-gray-500'" />
                  <span class="text-xs text-gray-200 flex-1 truncate">{{ a.name }}</span>
                  <div class="w-14 h-1.5 bg-surface-3 rounded-full overflow-hidden"><div class="h-full bg-amber-400 rounded-full" :style="{ width: `${a.activation * 100}%` }" /></div>
                  <span class="text-[10px] text-amber-400/70 tabular-nums w-8">{{ (a.activation * 100).toFixed(0) }}%</span>
                  <span class="text-[10px] text-gray-700">hop{{ a.hop }}</span>
                </button>
              </div>
            </div>
            <div v-else-if="recallResult.seeds.length" class="text-center py-6 text-xs text-gray-500">未发现扩散关联。先执行"每日巩固"建立关系。</div>
          </div>
        </div>
      </template>

      <!-- Tab: Patterns -->
      <template v-if="activeTab === 'patterns'">
        <div class="flex items-center gap-3">
          <div class="flex gap-1 bg-surface-2 rounded-lg p-0.5">
            <button v-for="s in ([{ key: 'heat', label: '热度' }, { key: 'confidence', label: '置信度' }, { key: 'access', label: '访问量' }] as const)" :key="s.key" class="px-2.5 py-1 text-[10px] rounded-md transition-all" :class="sortBy === s.key ? 'bg-surface-1 text-white' : 'text-gray-500 hover:text-gray-300'" @click="sortBy = s.key">{{ s.label }}</button>
          </div>
          <div class="flex gap-1">
            <button class="px-2 py-1 text-[10px] rounded-md transition-all" :class="!lifecycleFilter ? 'bg-surface-2 text-white' : 'text-gray-600 hover:text-gray-400'" @click="lifecycleFilter = ''">全部</button>
            <button v-for="state in (['active', 'warm', 'cool', 'compressed', 'archived'] as const)" :key="state" class="px-2 py-1 text-[10px] rounded-md transition-all" :class="lifecycleFilter === state ? 'bg-surface-2 ' + (lcfg[state]?.color ?? '') : 'text-gray-600 hover:text-gray-400'" @click="lifecycleFilter = lifecycleFilter === state ? '' : state">{{ lcfg[state]?.label }}</button>
          </div>
          <span class="text-[10px] text-gray-600 ml-auto tabular-nums">{{ sortedPatterns.length }}/{{ totalPatterns }}</span>
        </div>
        <div class="space-y-1">
          <button v-for="p in sortedPatterns" :key="p.id" class="w-full flex items-center gap-3 px-4 py-3 rounded-lg bg-surface-1 border border-surface-3 hover:border-accent/20 transition-all text-left group" @click="selectPattern(p)">
            <div class="w-2 h-2 rounded-full shrink-0" :class="lcfg[(p as any).lifecycle_state ?? 'active']?.bg ?? 'bg-gray-500'" />
            <span class="text-xs text-gray-200 flex-1 truncate group-hover:text-white transition-colors">{{ p.name }}</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-surface-2" :class="p.status === 'confirmed' ? 'text-emerald-400' : 'text-gray-500'">{{ p.status === 'confirmed' ? 'confirmed' : p.status }}</span>
            <span class="text-[10px] text-gray-600 w-10 tabular-nums">{{ p.confidence }}%</span>
            <div class="w-16 h-1.5 bg-surface-3 rounded-full overflow-hidden shrink-0"><div class="h-full rounded-full transition-all" :class="heatBarColor((p as any).heat_score ?? 0)" :style="{ width: `${Math.min(100, (p as any).heat_score ?? 0)}%` }" /></div>
            <span class="text-[10px] text-gray-600 w-6 tabular-nums">{{ (p as any).access_count ?? 0 }}x</span>
          </button>
        </div>
      </template>
    </div>

    <!-- Right Detail Panel -->
    <transition name="panel-slide">
      <div v-if="selectedPattern" class="w-80 border-l border-surface-3 bg-surface-1 overflow-y-auto shrink-0">
        <div class="p-4 border-b border-surface-3 flex items-center justify-between">
          <span class="text-sm font-medium text-gray-200 truncate">{{ selectedPattern.name }}</span>
          <button class="text-gray-500 hover:text-gray-300 p-1" @click="selectedPattern = null; selectedRelations = []">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>
        <div class="p-4 space-y-4">
          <div class="grid grid-cols-2 gap-2">
            <div class="bg-surface-2 rounded-lg p-2.5 text-center">
              <div class="text-lg font-semibold" :class="lcfg[(selectedPattern as any).lifecycle_state ?? 'active']?.color ?? 'text-gray-400'">{{ ((selectedPattern as any).heat_score ?? 0).toFixed(1) }}</div>
              <div class="text-[10px] text-gray-500">热度</div>
            </div>
            <div class="bg-surface-2 rounded-lg p-2.5 text-center">
              <div class="text-lg font-semibold text-gray-200">{{ selectedPattern.confidence }}%</div>
              <div class="text-[10px] text-gray-500">置信度</div>
            </div>
            <div class="bg-surface-2 rounded-lg p-2.5 text-center">
              <div class="text-lg font-semibold text-gray-200">{{ (selectedPattern as any).access_count ?? 0 }}</div>
              <div class="text-[10px] text-gray-500">访问</div>
            </div>
            <div class="bg-surface-2 rounded-lg p-2.5 text-center">
              <div class="text-lg font-semibold text-gray-200">{{ selectedPattern.evidence_count }}</div>
              <div class="text-[10px] text-gray-500">证据</div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-2.5 h-2.5 rounded-full" :class="lcfg[(selectedPattern as any).lifecycle_state ?? 'active']?.bg ?? 'bg-gray-500'" />
            <span class="text-xs" :class="lcfg[(selectedPattern as any).lifecycle_state ?? 'active']?.color ?? 'text-gray-400'">{{ lcfg[(selectedPattern as any).lifecycle_state ?? 'active']?.label }}</span>
            <span class="text-[10px] text-gray-600">{{ selectedPattern.category }}</span>
          </div>
          <div v-if="selectedPattern.description" class="text-xs text-gray-400 leading-relaxed">{{ selectedPattern.description }}</div>
          <div>
            <div class="text-xs font-medium text-gray-400 mb-2">关系 ({{ selectedRelations.length }})</div>
            <div v-if="relationsLoading" class="text-[10px] text-gray-600">加载中...</div>
            <div v-else-if="selectedRelations.length" class="space-y-1.5">
              <button v-for="rel in selectedRelations" :key="rel.id" class="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-surface-2 hover:bg-surface-3 text-left transition-colors" @click="goToPattern(rel.other_pattern_id)">
                <span class="text-[10px] px-1.5 py-0.5 rounded" :class="relTypeStyle[rel.relation_type]?.cls ?? 'text-gray-400 bg-surface-3'">{{ relTypeStyle[rel.relation_type]?.label ?? rel.relation_type }}</span>
                <span class="text-xs text-gray-300 flex-1 truncate">{{ rel.other_pattern_name }}</span>
                <span class="text-[10px] text-gray-600 tabular-nums">{{ (rel.weight * 100).toFixed(0) }}%</span>
              </button>
            </div>
            <div v-else class="text-[10px] text-gray-600">暂无关系</div>
          </div>
          <button class="w-full px-3 py-2 text-xs rounded-lg bg-accent/10 text-accent hover:bg-accent/20 transition-colors" @click="goToPattern(selectedPattern.id)">查看详情</button>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.panel-slide-enter-active { transition: all 0.25s ease-out; }
.panel-slide-leave-active { transition: all 0.2s ease-in; }
.panel-slide-enter-from { transform: translateX(100%); opacity: 0; }
.panel-slide-leave-to { transform: translateX(100%); opacity: 0; }

.terminal-panel {
  background: #0d0d1a;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

.terminal-scroll::-webkit-scrollbar { width: 4px; }
.terminal-scroll::-webkit-scrollbar-track { background: transparent; }
.terminal-scroll::-webkit-scrollbar-thumb { background: #333; border-radius: 2px; }
.terminal-scroll::-webkit-scrollbar-thumb:hover { background: #555; }
</style>

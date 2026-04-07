<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'

interface TopPattern {
  id: number
  name: string
  heat_score: number
  confidence: number
  confidence_level: string
  lifecycle_state: string
  evidence_count: number
}

interface Preview {
  total_patterns: number
  by_category: Record<string, number>
  by_confidence: { high: number; medium: number; low: number }
  by_lifecycle: Record<string, number>
  top_patterns: TopPattern[]
}

interface MentorInfo {
  key: string
  name: string
  repo: string
  tagline: string
  focus: string[]
  cached: boolean
}

interface MentorPattern {
  name: string
  description: string
  evidence: string[]
  confidence: string
  category: string
}

interface MentorResult {
  key: string
  name: string
  tagline: string
  repo: string
  commits_analyzed: number
  error: string
  patterns: MentorPattern[]
}

const preview = ref<Preview | null>(null)
const loading = ref(false)
const exporting = ref(false)
const exportedMd = ref('')
const copied = ref(false)
const showMd = ref(false)
const error = ref('')

// 导出配置
const minConfidence = ref(30)
const lifecycle = ref('active,warm')
const includeBody = ref(true)
const exportName = ref('me')

// 向大牛学习
const mentorCatalog = ref<MentorInfo[]>([])
const selectedMentors = ref<Set<string>>(new Set(['yyx990803', 'antirez', 'sindresorhus']))
const learnLoading = ref(false)
const learnResults = ref<MentorResult[]>([])
const learnError = ref('')
const learnMd = ref('')
const learnMdCopied = ref(false)
const showLearnMd = ref(false)

const fetchPreview = async () => {
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams({
      min_confidence: String(minConfidence.value),
      lifecycle: lifecycle.value,
    })
    const res = await fetch(`/api/workprint/preview?${params}`)
    if (!res.ok) throw new Error(await res.text())
    preview.value = await res.json()
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

const exportSkill = async () => {
  exporting.value = true
  error.value = ''
  try {
    const params = new URLSearchParams({
      name: exportName.value,
      min_confidence: String(minConfidence.value),
      lifecycle: lifecycle.value,
      include_body: String(includeBody.value),
    })
    const res = await fetch(`/api/workprint/export?${params}`)
    if (!res.ok) throw new Error(await res.text())
    exportedMd.value = await res.text()
    showMd.value = true
  } catch (e: any) {
    error.value = e.message
  } finally {
    exporting.value = false
  }
}

const downloadMd = () => {
  const blob = new Blob([exportedMd.value], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${exportName.value}_workprint.md`
  a.click()
  URL.revokeObjectURL(url)
}

const copyMd = async () => {
  await navigator.clipboard.writeText(exportedMd.value)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

const confidenceColor = (level: string) => {
  if (level === 'very_high' || level === 'high') return 'text-emerald-400'
  if (level === 'medium') return 'text-amber-400'
  return 'text-gray-400'
}

const lifecycleColor = (state: string) => {
  if (state === 'active') return 'bg-emerald-500/20 text-emerald-300'
  if (state === 'warm') return 'bg-amber-500/20 text-amber-300'
  if (state === 'cool') return 'bg-blue-500/20 text-blue-300'
  return 'bg-gray-500/20 text-gray-400'
}

const topCategories = computed(() => {
  if (!preview.value) return []
  return Object.entries(preview.value.by_category)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
})

const fetchMentorCatalog = async () => {
  try {
    const res = await fetch('/api/workprint/mentors')
    if (res.ok) mentorCatalog.value = await res.json()
  } catch {}
}

const toggleMentor = (key: string) => {
  const s = new Set(selectedMentors.value)
  if (s.has(key)) s.delete(key)
  else s.add(key)
  selectedMentors.value = s
}

const learnFromMentors = async () => {
  if (selectedMentors.value.size === 0) return
  learnLoading.value = true
  learnError.value = ''
  learnResults.value = []
  showLearnMd.value = false
  try {
    const keys = [...selectedMentors.value].join(',')
    const res = await fetch(`/api/workprint/learn-from?mentors=${keys}&max_commits=60`)
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    learnResults.value = data.mentors
  } catch (e: any) {
    learnError.value = e.message
  } finally {
    learnLoading.value = false
  }
}

const generateLearnSkillMd = async () => {
  learnLoading.value = true
  try {
    const keys = [...selectedMentors.value].join(',')
    const res = await fetch(`/api/workprint/learn-from/skill-md?mentors=${keys}&your_name=${exportName.value}`)
    if (!res.ok) throw new Error(await res.text())
    learnMd.value = await res.text()
    showLearnMd.value = true
  } catch (e: any) {
    learnError.value = e.message
  } finally {
    learnLoading.value = false
  }
}

const copyLearnMd = async () => {
  await navigator.clipboard.writeText(learnMd.value)
  learnMdCopied.value = true
  setTimeout(() => { learnMdCopied.value = false }, 2000)
}

const downloadLearnMd = () => {
  const blob = new Blob([learnMd.value], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${exportName.value}_learned_from_giants.md`
  a.click()
  URL.revokeObjectURL(url)
}

const confIcon = (level: string) => ({ high: '●', medium: '◑', low: '○' }[level] ?? '○')
const confColor = (level: string) => {
  if (level === 'high') return 'text-emerald-400'
  if (level === 'medium') return 'text-amber-400'
  return 'text-gray-500'
}
const categoryColor = (cat: string): string => ({
  style: 'bg-violet-500/20 text-violet-300',
  workflow: 'bg-cyan-500/20 text-cyan-300',
  decision: 'bg-amber-500/20 text-amber-300',
  tool: 'bg-emerald-500/20 text-emerald-300',
} as Record<string, string>)[cat] ?? 'bg-gray-500/20 text-gray-400'

onMounted(() => {
  fetchPreview()
  fetchMentorCatalog()
})
</script>

<template>
  <div class="flex flex-col h-full overflow-y-auto">
    <div class="max-w-5xl mx-auto w-full px-6 py-6 space-y-6">

      <!-- Header -->
      <div class="flex items-start justify-between">
        <div>
          <div class="flex items-center gap-2 mb-1">
            <svg class="w-5 h-5 text-violet-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
            </svg>
            <h1 class="text-xl font-semibold text-white">Workprint</h1>
          </div>
          <p class="text-sm text-gray-400">
            Distill your DevTwin behavior patterns into an executable Claude ​Code skill
          </p>
        </div>
        <button
          class="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white text-sm rounded-lg transition-colors font-medium"
          :disabled="loading"
          @click="fetchPreview"
        >
          <svg class="w-3.5 h-3.5" :class="loading ? 'animate-spin' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
          </svg>
          刷新
        </button>
      </div>

      <div v-if="error" class="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">
        {{ error }}
      </div>

      <!-- Stats Cards -->
      <div v-if="preview" class="grid grid-cols-4 gap-4">
        <div class="bg-[#12121a] border border-[#252535] rounded-xl p-4">
          <div class="text-2xl font-bold text-violet-400">{{ preview.total_patterns }}</div>
          <div class="text-xs text-gray-500 mt-1">活跃 Pattern</div>
        </div>
        <div class="bg-[#12121a] border border-[#252535] rounded-xl p-4">
          <div class="text-2xl font-bold text-emerald-400">{{ preview.by_confidence.high }}</div>
          <div class="text-xs text-gray-500 mt-1">高置信度</div>
        </div>
        <div class="bg-[#12121a] border border-[#252535] rounded-xl p-4">
          <div class="text-2xl font-bold text-amber-400">{{ preview.by_confidence.medium }}</div>
          <div class="text-xs text-gray-500 mt-1">中置信度</div>
        </div>
        <div class="bg-[#12121a] border border-[#252535] rounded-xl p-4">
          <div class="text-2xl font-bold text-gray-300">{{ preview.by_lifecycle?.active ?? 0 }}</div>
          <div class="text-xs text-gray-500 mt-1">Active 状态</div>
        </div>
      </div>

      <div v-if="preview" class="grid grid-cols-3 gap-6">
        <!-- 左：Top Patterns 热榜 -->
        <div class="col-span-2 bg-[#12121a] border border-[#252535] rounded-xl p-5">
          <h2 class="text-sm font-medium text-gray-300 mb-4">热度最高的 Pattern（将出现在 SKILL.md 首位）</h2>
          <div class="space-y-2">
            <div
              v-for="(p, i) in preview.top_patterns"
              :key="p.id"
              class="flex items-center gap-3 py-2 border-b border-[#1e1e2e] last:border-0"
            >
              <span class="text-xs text-gray-600 w-4 text-right">{{ i + 1 }}</span>
              <div class="flex-1 min-w-0">
                <div class="text-sm text-gray-200 truncate">{{ p.name }}</div>
                <div class="flex items-center gap-2 mt-0.5">
                  <span class="text-[10px]" :class="confidenceColor(p.confidence_level)">
                    {{ p.confidence }}% {{ p.confidence_level }}
                  </span>
                  <span class="text-[10px] text-gray-600">{{ p.evidence_count }} evidence</span>
                </div>
              </div>
              <div class="flex items-center gap-1.5">
                <span class="text-[10px] px-1.5 py-0.5 rounded-full" :class="lifecycleColor(p.lifecycle_state)">
                  {{ p.lifecycle_state }}
                </span>
                <span class="text-xs text-gray-500">🔥 {{ p.heat_score }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 右：分类分布 + 导出设置 -->
        <div class="space-y-4">
          <!-- 分类分布 -->
          <div class="bg-[#12121a] border border-[#252535] rounded-xl p-4">
            <h2 class="text-xs font-medium text-gray-400 mb-3">Pattern 分类</h2>
            <div class="space-y-2">
              <div v-for="[cat, count] in topCategories" :key="cat" class="flex items-center gap-2">
                <div class="flex-1 text-xs text-gray-400 truncate">{{ cat }}</div>
                <div class="text-xs text-gray-300 font-mono">{{ count }}</div>
                <div class="w-16 h-1 bg-[#1e1e2e] rounded-full overflow-hidden">
                  <div
                    class="h-full bg-violet-500/60 rounded-full"
                    :style="{ width: `${Math.min(100, count / (preview?.total_patterns ?? 1) * 100 * 3)}%` }"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- 导出设置 -->
          <div class="bg-[#12121a] border border-[#252535] rounded-xl p-4 space-y-3">
            <h2 class="text-xs font-medium text-gray-400">导出设置</h2>

            <div>
              <label class="text-[11px] text-gray-500 block mb-1">Skill 标识符（slug）</label>
              <input
                v-model="exportName"
                class="w-full bg-[#0e0e18] border border-[#252535] rounded px-2.5 py-1.5 text-xs text-gray-200 outline-none focus:border-violet-500/50"
                placeholder="me"
              />
            </div>

            <div>
              <label class="text-[11px] text-gray-500 block mb-1">最低置信度</label>
              <input
                v-model.number="minConfidence"
                type="range" min="0" max="90" step="5"
                class="w-full accent-violet-500"
              />
              <div class="text-[10px] text-gray-600 text-right">{{ minConfidence }}%</div>
            </div>

            <div>
              <label class="text-[11px] text-gray-500 block mb-1">生命周期范围</label>
              <select
                v-model="lifecycle"
                class="w-full bg-[#0e0e18] border border-[#252535] rounded px-2 py-1.5 text-xs text-gray-200 outline-none"
              >
                <option value="active">仅 Active</option>
                <option value="active,warm">Active + Warm</option>
                <option value="active,warm,cool">Active + Warm + Cool</option>
                <option value="active,warm,cool,compressed,archived">全部</option>
              </select>
            </div>

            <div class="flex items-center justify-between">
              <label class="text-[11px] text-gray-500">包含可执行规则 (body)</label>
              <button
                class="w-8 h-4 rounded-full transition-colors relative"
                :class="includeBody ? 'bg-violet-600' : 'bg-[#252535]'"
                @click="includeBody = !includeBody"
              >
                <div class="absolute top-0.5 w-3 h-3 bg-white rounded-full transition-all"
                  :class="includeBody ? 'left-4.5' : 'left-0.5'" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 导出按钮 -->
      <div v-if="preview" class="flex items-center gap-3">
        <button
          class="flex items-center gap-2 px-5 py-2.5 bg-violet-600 hover:bg-violet-500 text-white text-sm rounded-lg transition-colors font-medium disabled:opacity-50"
          :disabled="exporting"
          @click="exportSkill"
        >
          <svg class="w-4 h-4" :class="exporting ? 'animate-spin' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path v-if="!exporting" d="M12 2L2 7l10 5 10-5-10-5z"/><path v-if="!exporting" d="M2 17l10 5 10-5"/><path v-if="!exporting" d="M2 12l10 5 10-5"/>
            <polyline v-if="exporting" points="23 4 23 10 17 10"/><path v-if="exporting" d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
          </svg>
          {{ exporting ? '生成中…' : '生成 SKILL.md' }}
        </button>
        <p class="text-xs text-gray-500">
          将 DevTwin 挖掘的 {{ preview.total_patterns }} 个 pattern 导出为 Claude ​Code 可读的行为技能文件
        </p>
      </div>

      <!-- SKILL.md 预览 -->
      <div v-if="showMd && exportedMd" class="bg-[#0e0e18] border border-[#252535] rounded-xl overflow-hidden">
        <div class="flex items-center justify-between px-4 py-3 border-b border-[#252535]">
          <div class="flex items-center gap-2">
            <svg class="w-4 h-4 text-violet-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
            </svg>
            <span class="text-sm text-gray-300 font-mono">{{ exportName }}_workprint.md</span>
            <span class="text-xs text-gray-600">{{ exportedMd.length.toLocaleString() }} chars</span>
          </div>
          <div class="flex items-center gap-2">
            <button
              class="flex items-center gap-1.5 px-3 py-1 text-xs text-gray-400 hover:text-gray-200 border border-[#252535] rounded-md transition-colors"
              @click="copyMd"
            >
              <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
              {{ copied ? '已复制' : '复制' }}
            </button>
            <button
              class="flex items-center gap-1.5 px-3 py-1 text-xs bg-violet-600 hover:bg-violet-500 text-white rounded-md transition-colors"
              @click="downloadMd"
            >
              <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              下载
            </button>
          </div>
        </div>
        <pre class="p-4 text-xs text-gray-300 font-mono overflow-x-auto max-h-[500px] overflow-y-auto leading-relaxed">{{ exportedMd }}</pre>
      </div>

      <!-- ============================================================ -->
      <!-- 向大牛学习 -->
      <!-- ============================================================ -->
      <div class="border-t border-[#252535] pt-6">
        <div class="flex items-center gap-2 mb-1">
          <svg class="w-5 h-5 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
          </svg>
          <h2 class="text-lg font-semibold text-white">向开源大牛学习</h2>
        </div>
        <p class="text-sm text-gray-400 mb-5">
          分析顶尖开源工程师的真实 GitHub commit 行为，提取可学习的工作模式。
          不是读他们写的书，而是看他们<strong class="text-gray-200">真正怎么做事</strong>。
        </p>

        <!-- 大牛选择器 -->
        <div v-if="mentorCatalog.length" class="grid grid-cols-2 gap-2 mb-5">
          <button
            v-for="m in mentorCatalog"
            :key="m.key"
            class="flex items-start gap-3 p-3 rounded-lg border transition-all text-left"
            :class="selectedMentors.has(m.key)
              ? 'border-amber-500/50 bg-amber-500/[0.07]'
              : 'border-[#252535] bg-[#12121a] hover:border-[#353545]'"
            @click="toggleMentor(m.key)"
          >
            <div class="mt-0.5 w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-colors"
              :class="selectedMentors.has(m.key) ? 'border-amber-400 bg-amber-400' : 'border-gray-600'">
              <svg v-if="selectedMentors.has(m.key)" class="w-2.5 h-2.5 text-black" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </div>
            <div class="min-w-0">
              <div class="text-sm font-medium text-gray-200 truncate">{{ m.name }}</div>
              <div class="text-[10px] text-gray-500 truncate">{{ m.repo }}</div>
              <div class="flex flex-wrap gap-1 mt-1">
                <span v-for="f in m.focus.slice(0, 3)" :key="f"
                  class="text-[9px] px-1.5 py-0.5 bg-[#1e1e2e] text-gray-500 rounded-full">{{ f }}</span>
              </div>
            </div>
          </button>
        </div>
        <div v-else class="text-sm text-gray-600 mb-5">加载大牛名录中…</div>

        <!-- 操作按钮 -->
        <div class="flex items-center gap-3 mb-5">
          <button
            class="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-sm rounded-lg transition-colors font-medium disabled:opacity-50"
            :disabled="learnLoading || selectedMentors.size === 0"
            @click="learnFromMentors"
          >
            <svg class="w-3.5 h-3.5" :class="learnLoading ? 'animate-spin' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
            </svg>
            {{ learnLoading ? '分析中（需要几秒）…' : `分析 ${selectedMentors.size} 位大牛` }}
          </button>
          <button
            v-if="learnResults.length"
            class="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white text-sm rounded-lg transition-colors font-medium"
            @click="generateLearnSkillMd"
          >
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
            </svg>
            生成师承 SKILL.md
          </button>
        </div>

        <div v-if="learnError" class="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400 mb-4">
          {{ learnError }}
        </div>

        <!-- 结果卡片 -->
        <div v-if="learnResults.length" class="space-y-4">
          <div
            v-for="mentor in learnResults"
            :key="mentor.key"
            class="bg-[#12121a] border border-[#252535] rounded-xl overflow-hidden"
          >
            <!-- 大牛 header -->
            <div class="flex items-start justify-between px-5 py-4 border-b border-[#1e1e2e]">
              <div>
                <div class="flex items-center gap-2">
                  <svg class="w-4 h-4 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                  </svg>
                  <span class="font-medium text-gray-100">{{ mentor.name }}</span>
                  <span v-if="mentor.error" class="text-xs text-red-400">— {{ mentor.error }}</span>
                </div>
                <div class="text-xs text-gray-500 mt-0.5 italic">{{ mentor.tagline }}</div>
              </div>
              <div class="text-right shrink-0 ml-4">
                <div class="text-sm font-mono text-amber-400">{{ mentor.commits_analyzed }}</div>
                <div class="text-[10px] text-gray-600">commits 分析</div>
                <a :href="`https://github.com/${mentor.repo}`" target="_blank"
                  class="text-[10px] text-violet-400 hover:underline">{{ mentor.repo }}</a>
              </div>
            </div>

            <!-- 挖掘到的模式 -->
            <div v-if="mentor.patterns.length" class="divide-y divide-[#1e1e2e]">
              <div v-for="p in mentor.patterns" :key="p.name" class="px-5 py-3">
                <div class="flex items-start gap-2 mb-1">
                  <span :class="confColor(p.confidence)" class="text-xs font-mono mt-0.5 shrink-0">{{ confIcon(p.confidence) }}</span>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 flex-wrap">
                      <span class="text-sm text-gray-200">{{ p.name }}</span>
                      <span class="text-[10px] px-1.5 py-0.5 rounded-full" :class="categoryColor(p.category)">{{ p.category }}</span>
                    </div>
                    <p class="text-xs text-gray-400 mt-1 leading-relaxed">{{ p.description }}</p>
                    <div v-if="p.evidence.length" class="mt-2 space-y-1">
                      <div v-for="ev in p.evidence.slice(0, 3)" :key="ev"
                        class="text-[10px] font-mono text-gray-500 bg-[#0e0e18] px-2 py-1 rounded truncate">
                        {{ ev }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-else-if="!mentor.error" class="px-5 py-4 text-xs text-gray-600">
              未能提取到有效模式（可能是 GitHub API 限速，请稍后再试）
            </div>
          </div>
        </div>

        <!-- 师承 SKILL.md 预览 -->
        <div v-if="showLearnMd && learnMd" class="mt-4 bg-[#0e0e18] border border-[#252535] rounded-xl overflow-hidden">
          <div class="flex items-center justify-between px-4 py-3 border-b border-[#252535]">
            <span class="text-sm text-gray-300 font-mono">{{ exportName }}_learned_from_giants.md</span>
            <div class="flex items-center gap-2">
              <button class="flex items-center gap-1.5 px-3 py-1 text-xs text-gray-400 hover:text-gray-200 border border-[#252535] rounded-md" @click="copyLearnMd">
                {{ learnMdCopied ? '已复制' : '复制' }}
              </button>
              <button class="flex items-center gap-1.5 px-3 py-1 text-xs bg-violet-600 hover:bg-violet-500 text-white rounded-md" @click="downloadLearnMd">
                下载
              </button>
            </div>
          </div>
          <pre class="p-4 text-xs text-gray-300 font-mono overflow-x-auto max-h-[400px] overflow-y-auto leading-relaxed">{{ learnMd }}</pre>
        </div>
      </div>

      <!-- 使用说明 -->
      <div class="bg-[#12121a] border border-[#252535] rounded-xl p-5">
        <h2 class="text-sm font-medium text-gray-300 mb-3">导出后如何使用</h2>
        <div class="space-y-3 text-sm text-gray-400">
          <div class="flex gap-3">
            <span class="text-violet-400 font-mono text-xs mt-0.5 shrink-0">1</span>
            <div>
              <div class="text-gray-300 mb-0.5">下载 SKILL.md 到你的项目</div>
              <code class="text-xs text-violet-300 bg-[#0e0e18] px-2 py-0.5 rounded">cp ~/Downloads/me_workprint.md ./SKILL.md</code>
            </div>
          </div>
          <div class="flex gap-3">
            <span class="text-violet-400 font-mono text-xs mt-0.5 shrink-0">2</span>
            <div>
              <div class="text-gray-300 mb-0.5">在 Claude ​Code 里激活</div>
              <code class="text-xs text-violet-300 bg-[#0e0e18] px-2 py-0.5 rounded">/workprint {{ exportName }} 帮我 review 这个 PR</code>
            </div>
          </div>
          <div class="flex gap-3">
            <span class="text-violet-400 font-mono text-xs mt-0.5 shrink-0">3</span>
            <div>
              <div class="text-gray-300 mb-0.5">持续更新（每次 DevTwin 挖到新 pattern 就重新导出）</div>
              <code class="text-xs text-violet-300 bg-[#0e0e18] px-2 py-0.5 rounded">curl http://localhost:7891/api/workprint/export > SKILL.md</code>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

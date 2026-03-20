<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'

import type { SharedClawProfile, BehaviorPattern, ClawProfile } from '@/types'
import type { ClawProfileExchangeWorkflow } from '@/http_api/patterns'
import { createSharedClawProfileApi, downloadSharedClawProfileApi, getSharedClawProfileApi, getSharedClawProfilesApi, starSharedClawProfileApi } from '@/http_api/community'
import { importPatternsApi } from '@/http_api/patterns'
import { usePatternsStore } from '@/stores/patterns'
import { getActiveProfileApi } from '@/http_api/profiles'

const searchQuery = ref('')
const categoryFilter = ref('all')
const expandedPackId = ref<number | null>(null)
const importSuccess = ref<number | null>(null)
const importingPackId = ref<number | null>(null)
const loading = ref(false)
const packsError = ref<string | null>(null)
const patternsError = ref<string | null>(null)
const actionError = ref<string | null>(null)

const publishName = ref('')
const publishDesc = ref('')
const publishCategory = ref('coding')
const publishTags = ref('')
const selectedPatternIds = ref<Set<number>>(new Set())
const publishing = ref(false)
const publishSuccess = ref(false)
const selectedPack = ref<SharedClawProfile | null>(null)
const previewPack = computed(() => selectedPack.value as SharedClawProfile)
const previewLoading = ref(false)
const starringPackId = ref<number | null>(null)
const downloadingPackId = ref<number | null>(null)

const packs = ref<SharedClawProfile[]>([])
const patternsStore = usePatternsStore()
const myPatterns = computed<BehaviorPattern[]>(() => patternsStore.patterns)
const activeProfile = ref<ClawProfile | null>(null)

const loadCommunityData = async () => {
  loading.value = true
  packsError.value = null
  patternsError.value = null
  actionError.value = null

  const [packRes, patternRes, workflowRes, activeProfileRes] = await Promise.all([
    getSharedClawProfilesApi(),
    patternsStore.ensurePatternsLoaded(),
    patternsStore.ensureWorkflowsLoaded(),
    getActiveProfileApi(),
  ])

  if (packRes.data) packs.value = packRes.data
  else packsError.value = packRes.error ?? '社区 ClawProfile 加载失败'

  if (!patternRes.data) patternsError.value = patternRes.error ?? '本地模式加载失败'
  if (!workflowRes.data && !patternsError.value) patternsError.value = workflowRes.error ?? '本地工作流加载失败'
  if (activeProfileRes.data) activeProfile.value = activeProfileRes.data

  loading.value = false
}

onMounted(() => {
  void loadCommunityData()
})

const categories = [
  { key: 'all', label: '全部' },
  { key: 'coding', label: '编码习惯' },
  { key: 'git', label: 'Git 规范' },
  { key: 'devops', label: '运维部署' },
  { key: 'review', label: '代码审查' },
  { key: 'collaboration', label: '协作模式' },
]

const categoryColorMap: Record<string, string> = {
  git: 'bg-git/20 text-git border-git/30',
  coding: 'bg-accent/20 text-accent border-accent/30',
  review: 'bg-openclaw/20 text-openclaw border-openclaw/30',
  devops: 'bg-terminal/20 text-terminal border-terminal/30',
  collaboration: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
}

const categoryBtnColor: Record<string, string> = {
  all: 'bg-accent text-white',
  coding: 'bg-accent text-white',
  git: 'bg-git text-white',
  review: 'bg-openclaw text-white',
  devops: 'bg-terminal text-white',
  collaboration: 'bg-purple-500 text-white',
}

const getPrimaryCategory = (tags: string[]) =>
  categories.find(category => tags.some(tag => tag.toLowerCase().includes(category.key)))?.key ?? 'coding'

const filteredPacks = computed(() => {
  let result: SharedClawProfile[] = packs.value
  if (categoryFilter.value !== 'all') {
    result = result.filter(p => p.tags.some(tag => tag.toLowerCase().includes(categoryFilter.value)))
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(p =>
      p.name.toLowerCase().includes(q)
      || p.display.toLowerCase().includes(q)
      || p.description.toLowerCase().includes(q)
      || p.tags.some(t => t.toLowerCase().includes(q))
      || p.author.username.toLowerCase().includes(q)
    )
  }
  return result
})

const communityStats = computed(() => ({
  profiles: filteredPacks.value.length,
  patterns: filteredPacks.value.reduce((sum, pack) => sum + pack.patterns.length, 0),
  workflows: filteredPacks.value.reduce((sum, pack) => sum + pack.workflows.length, 0),
  creators: new Set(filteredPacks.value.map(pack => pack.author.username)).size,
}))

const highlightedAuthors = computed(() =>
  [...filteredPacks.value]
    .sort((a, b) => b.stars + b.downloads - (a.stars + a.downloads))
    .slice(0, 5),
)

const communityTracks = computed(() => [
  {
    name: '具身与机器人',
    tone: 'from-cyan-500/20 to-sky-500/5 border-cyan-500/20',
    match: (pack: SharedClawProfile) => pack.tags.some(tag => ['embodied', 'robot', 'motionplan', 'ros', 'softrobot'].includes(tag.toLowerCase())),
  },
  {
    name: '长程与记忆',
    tone: 'from-purple-500/20 to-fuchsia-500/5 border-purple-500/20',
    match: (pack: SharedClawProfile) => pack.tags.some(tag => ['memory', 'longhorizon', 'vla', 'planning', 'structure'].includes(tag.toLowerCase())),
  },
  {
    name: '开源与交付',
    tone: 'from-emerald-500/20 to-lime-500/5 border-emerald-500/20',
    match: (pack: SharedClawProfile) => pack.tags.some(tag => ['opensource', 'operations', 'release', 'deployment', 'community'].includes(tag.toLowerCase())),
  },
])

// 只显示已确认或可导出的模式供发布选择
const publishablePatterns = computed(() =>
  myPatterns.value.filter(p => p.status === 'confirmed' || p.status === 'exportable')
)

const canPublish = computed(() =>
  Boolean(publishName.value.trim() && publishDesc.value.trim() && selectedPatternIds.value.size > 0)
)

watch(publishablePatterns, patterns => {
  const validIds = new Set(patterns.map(pattern => pattern.id))
  const nextIds = [...selectedPatternIds.value].filter(id => validIds.has(id))
  if (nextIds.length !== selectedPatternIds.value.size) {
    selectedPatternIds.value = new Set(nextIds)
  }
}, { immediate: true })

const toggleExpand = (id: number) => {
  expandedPackId.value = expandedPackId.value === id ? null : id
}

const openPackPreview = async (pack: SharedClawProfile) => {
  previewLoading.value = true
  const res = await getSharedClawProfileApi(pack.id)
  selectedPack.value = res.data ?? pack
  if (!res.data && res.error) {
    actionError.value = res.error
  }
  previewLoading.value = false
}

const closePackPreview = () => {
  selectedPack.value = null
}

const togglePatternSelect = (id: number) => {
  const next = new Set(selectedPatternIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedPatternIds.value = next
}

const normalizeSharedWorkflow = (workflow: any): ClawProfileExchangeWorkflow => ({
  slug: typeof workflow?.slug === 'string'
    ? workflow.slug
    : String(workflow?.name ?? 'workflow').toLowerCase().replace(/\s+/g, '-'),
  frontmatter: workflow?.frontmatter && typeof workflow.frontmatter === 'object'
    ? workflow.frontmatter
    : { name: String(workflow?.name ?? 'Imported Workflow'), steps: Array.isArray(workflow?.steps) ? workflow.steps : [] },
  body: typeof workflow?.body === 'string'
    ? workflow.body
    : String(workflow?.description ?? ''),
})

const handleImport = async (pack: SharedClawProfile) => {
  actionError.value = null
  importingPackId.value = pack.id
  const res = await importPatternsApi({
    profile: {
      name: pack.profile.name,
      display: pack.profile.display,
      description: pack.profile.description ?? undefined,
      author: pack.profile.author ?? undefined,
      tags: pack.profile.tags,
      license: pack.profile.license ?? undefined,
      trust: pack.profile.trust ?? undefined,
      injection: pack.profile.injection ?? undefined,
    },
    patterns: pack.patterns,
    workflows: pack.workflows.map(normalizeSharedWorkflow),
  })

  if (res.data) {
    const [refreshPatterns, refreshWorkflows] = await Promise.all([
      patternsStore.fetchPatterns(undefined, true),
      patternsStore.fetchWorkflows(true),
    ])
    if (!refreshPatterns.data) patternsError.value = refreshPatterns.error ?? '本地模式刷新失败'
    if (!refreshWorkflows.data && !patternsError.value) patternsError.value = refreshWorkflows.error ?? '本地工作流刷新失败'
    importSuccess.value = pack.id
    setTimeout(() => { importSuccess.value = null }, 2500)
  } else {
    actionError.value = res.error ?? '导入失败，请稍后重试'
  }

  importingPackId.value = null
}

const handleStar = async (pack: SharedClawProfile) => {
  starringPackId.value = pack.id
  const res = await starSharedClawProfileApi(pack.id)
  starringPackId.value = null
  if (res.data) {
    packs.value = packs.value.map(item => item.id === pack.id ? { ...item, stars: res.data!.stars } : item)
    if (selectedPack.value?.id === pack.id) {
      selectedPack.value = { ...selectedPack.value, stars: res.data.stars }
    }
  } else {
    actionError.value = res.error ?? '点赞失败，请稍后重试'
  }
}

const handleDownload = async (pack: SharedClawProfile) => {
  downloadingPackId.value = pack.id
  const res = await downloadSharedClawProfileApi(pack.id)
  downloadingPackId.value = null
  const payload = res.data ?? pack
  if (!payload) {
    actionError.value = res.error ?? '下载失败，请稍后重试'
    return
  }

  packs.value = packs.value.map(item => item.id === pack.id ? { ...item, downloads: payload.downloads } : item)
  if (selectedPack.value?.id === pack.id) {
    selectedPack.value = payload
  }

  const blob = new Blob([JSON.stringify({
    schema: 'clawprofile/v1',
    profile: payload.profile,
    patterns: payload.patterns,
    workflows: payload.workflows,
    exported_at: Math.floor(Date.now() / 1000),
  }, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${payload.name || 'shared-clawprofile'}.json`
  anchor.click()
  URL.revokeObjectURL(url)
}

const formatCount = (n: number) => {
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

const handlePublish = async () => {
  if (!canPublish.value) return
  actionError.value = null
  publishSuccess.value = false
  publishing.value = true
  const selectedPatterns = myPatterns.value.filter(p => selectedPatternIds.value.has(p.id))
  const selectedSlugs = new Set(selectedPatterns.map(pattern => pattern.slug).filter(Boolean))
  const selectedWorkflows = patternsStore.workflows.filter(workflow =>
    workflow.steps.some(step => step.pattern && selectedSlugs.has(step.pattern))
    || workflow.patterns.some(id => selectedPatternIds.value.has(id))
  )
  const exportedWorkflows = selectedWorkflows.map(workflow => ({
    slug: workflow.name.toLowerCase().replace(/\s+/g, '-'),
    frontmatter: {
      name: workflow.name,
      steps: workflow.steps,
    },
    body: workflow.description,
  }))
  const tags = Array.from(new Set([publishCategory.value, ...publishTags.value.split(',').map(t => t.trim()).filter(Boolean)]))
  const profileMeta = activeProfile.value ?? {
    name: publishName.value.trim(),
    display: publishName.value.trim(),
    description: publishDesc.value.trim(),
    author: 'liyufeng',
    tags,
    license: 'public',
    trust: 'local',
    injection: { mode: 'proactive', budget: 2000 },
  }
  const res = await createSharedClawProfileApi({
    name: profileMeta.name,
    display: publishName.value.trim(),
    description: publishDesc.value.trim(),
    profile: {
      ...profileMeta,
      display: publishName.value.trim(),
      description: publishDesc.value.trim() || undefined,
      author: profileMeta.author ?? undefined,
      tags,
      license: profileMeta.license ?? undefined,
      trust: profileMeta.trust ?? undefined,
      injection: profileMeta.injection ?? undefined,
    },
    patterns: selectedPatterns,
    workflows: exportedWorkflows,
    tags,
  })
  publishing.value = false
  if (res.data) {
    publishSuccess.value = true
    packs.value = [res.data, ...packs.value]
    publishName.value = ''
    publishDesc.value = ''
    publishTags.value = ''
    publishCategory.value = 'coding'
    selectedPatternIds.value = new Set()
    setTimeout(() => { publishSuccess.value = false }, 4000)
  } else {
    actionError.value = res.error ?? '发布失败，请稍后重试'
  }
}
</script>

<template>
  <div class="p-6 space-y-6 overflow-y-auto h-full">
    <!-- 页面标题 -->
    <div>
      <h1 class="text-2xl font-semibold">社区分享</h1>
      <p class="text-sm text-gray-400 mt-1">发现和导入社区中优秀开发者的 Shared ClawProfile</p>
    </div>

    <div class="grid grid-cols-[1.2fr_0.8fr] gap-4">
      <div class="relative overflow-hidden rounded-2xl border border-openclaw/20 bg-surface-1 p-5">
        <div class="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.14),transparent_45%),radial-gradient(circle_at_bottom_right,rgba(124,92,252,0.14),transparent_40%)]" />
        <div class="relative">
          <div class="text-xs uppercase tracking-[0.2em] text-openclaw/80">Featured ClawProfiles</div>
          <div class="text-xl font-semibold text-gray-100 mt-2">把顶级工程习惯直接导入你的本地行为系统</div>
          <div class="text-sm text-gray-400 mt-2 leading-relaxed">这里不只是模式包，而是带工作流、场景和风格的 Shared ClawProfile。你可以按研究、机器人、长程记忆、开源交付等主题筛选导入。</div>
          <div class="grid grid-cols-4 gap-3 mt-5">
            <div class="rounded-xl bg-surface-2/80 border border-surface-3 p-3">
              <div class="text-[11px] text-gray-500">ClawProfile</div>
              <div class="text-2xl font-semibold text-gray-100 mt-1">{{ communityStats.profiles }}</div>
            </div>
            <div class="rounded-xl bg-surface-2/80 border border-surface-3 p-3">
              <div class="text-[11px] text-gray-500">行为准则</div>
              <div class="text-2xl font-semibold text-cyan-300 mt-1">{{ communityStats.patterns }}</div>
            </div>
            <div class="rounded-xl bg-surface-2/80 border border-surface-3 p-3">
              <div class="text-[11px] text-gray-500">工作流</div>
              <div class="text-2xl font-semibold text-emerald-400 mt-1">{{ communityStats.workflows }}</div>
            </div>
            <div class="rounded-xl bg-surface-2/80 border border-surface-3 p-3">
              <div class="text-[11px] text-gray-500">创作者</div>
              <div class="text-2xl font-semibold text-purple-400 mt-1">{{ communityStats.creators }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-surface-1 rounded-2xl border border-surface-3 p-5">
        <div class="text-xs uppercase tracking-[0.2em] text-gray-500">Top Creators</div>
        <div class="space-y-2.5 mt-4">
          <div
            v-for="pack in highlightedAuthors"
            :key="`author-${pack.id}`"
            class="flex items-center gap-3 rounded-xl bg-surface-2/80 border border-surface-3 px-3 py-2.5"
          >
            <div class="w-9 h-9 rounded-full bg-accent/15 text-accent flex items-center justify-center text-xs font-bold shrink-0">{{ pack.author.avatar }}</div>
            <div class="min-w-0 flex-1">
              <div class="text-sm text-gray-200 truncate">{{ pack.author.username }}</div>
              <div class="text-[10px] text-gray-500 truncate">{{ pack.author.title }}</div>
            </div>
            <div class="text-right shrink-0">
              <div class="text-[10px] text-amber-300">{{ formatCount(pack.stars) }} stars</div>
              <div class="text-[10px] text-gray-500">{{ formatCount(pack.downloads) }} downloads</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 搜索栏 -->
    <div class="relative">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
      </svg>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索 ClawProfile、作者、标签..."
        class="w-full bg-surface-1 border border-surface-3 rounded-xl pl-10 pr-4 py-2.5 text-sm text-gray-300 outline-none focus:border-accent transition-colors"
      />
    </div>

    <!-- 分类筛选 -->
    <div class="flex items-center gap-2 flex-wrap">
      <button
        v-for="cat in categories"
        :key="cat.key"
        class="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
        :class="categoryFilter === cat.key
          ? categoryBtnColor[cat.key]
          : 'bg-surface-2 text-gray-400 hover:bg-surface-3 hover:text-gray-300'"
        @click="categoryFilter = cat.key"
      >
        {{ cat.label }}
      </button>
    </div>

    <!-- 统计信息 -->
    <div class="text-sm text-gray-400">
      共 {{ filteredPacks.length }} 个 Shared ClawProfile
    </div>

    <div class="grid grid-cols-3 gap-4">
      <div
        v-for="track in communityTracks"
        :key="track.name"
        class="rounded-2xl border p-4 bg-gradient-to-br"
        :class="track.tone"
      >
        <div class="text-sm font-medium text-gray-100">{{ track.name }}</div>
        <div class="text-[11px] text-gray-400 mt-1">{{ filteredPacks.filter(track.match).length }} 个可导入 profile</div>
        <div class="flex flex-wrap gap-1.5 mt-3">
          <span
            v-for="pack in filteredPacks.filter(track.match).slice(0, 3)"
            :key="`${track.name}-${pack.id}`"
            class="text-[10px] px-2 py-0.5 rounded-full bg-surface-1/70 text-gray-300 border border-surface-3"
          >
            {{ pack.author.username }}
          </span>
        </div>
      </div>
    </div>

    <div v-if="actionError" class="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-300">
      {{ actionError }}
    </div>

    <div v-if="packsError && packs.length > 0" class="bg-yellow-500/10 border border-yellow-500/20 rounded-xl px-4 py-3 text-sm text-yellow-200">
      {{ packsError }}
    </div>

    <div v-if="patternsError" class="bg-yellow-500/10 border border-yellow-500/20 rounded-xl px-4 py-3 text-sm text-yellow-200">
      {{ patternsError }}
    </div>

    <!-- 模式包卡片网格 -->
    <div v-if="loading" class="bg-surface-1 rounded-xl border border-surface-3 py-20 text-center text-gray-500">
      <div class="text-lg mb-2">正在加载社区 ClawProfile...</div>
      <div class="text-sm text-gray-600">请稍候</div>
    </div>

    <div v-else-if="packsError && packs.length === 0" class="bg-surface-1 rounded-xl border border-red-500/20 py-20 text-center text-gray-400">
      <div class="text-lg mb-2 text-gray-200">社区 ClawProfile 加载失败</div>
      <div class="text-sm text-red-300 mb-4">{{ packsError }}</div>
      <button class="text-sm text-accent hover:text-accent-glow cursor-pointer" @click="loadCommunityData">重试</button>
    </div>

    <div v-else-if="filteredPacks.length === 0" class="bg-surface-1 rounded-xl border border-surface-3 py-20 text-center text-gray-500">
      <div class="text-lg mb-2">暂无匹配的 ClawProfile</div>
      <div class="text-sm text-gray-600">试试调整搜索词或分类</div>
    </div>

    <div v-else class="grid grid-cols-2 gap-4">
      <div
        v-for="pack in filteredPacks"
        :key="pack.id"
        class="bg-surface-1 rounded-xl border border-surface-3 p-4 space-y-3 hover:border-accent/40 transition-colors cursor-pointer"
        @click="toggleExpand(pack.id)"
      >
        <!-- 作者信息 -->
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-full bg-accent/20 flex items-center justify-center text-xs font-bold text-accent shrink-0">
            {{ pack.author.avatar }}
          </div>
          <div class="min-w-0">
            <div class="text-sm font-medium text-gray-200 truncate">{{ pack.author.username }}</div>
            <div class="text-[10px] text-gray-500 truncate">{{ pack.author.title }}</div>
          </div>
        </div>

        <!-- Profile 名称和分类 -->
        <div class="flex items-start justify-between gap-2">
          <div class="text-sm font-medium text-gray-200 leading-snug">{{ pack.display }}</div>
          <span class="text-[10px] px-2 py-0.5 rounded border shrink-0" :class="categoryColorMap[getPrimaryCategory(pack.tags)]">
            {{ categories.find(c => c.key === getPrimaryCategory(pack.tags))?.label }}
          </span>
        </div>

        <!-- 描述 -->
        <div class="text-xs text-gray-400 leading-relaxed line-clamp-2">{{ pack.description }}</div>

        <!-- 统计数据 -->
        <div class="flex items-center gap-4 text-[11px] text-gray-500">
          <div class="flex items-center gap-1">
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
            </svg>
            {{ formatCount(pack.downloads) }}
          </div>
          <div class="flex items-center gap-1">
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
            {{ formatCount(pack.stars) }}
          </div>
          <div class="text-[10px] text-gray-600">{{ pack.patterns.length }} 个模式 · {{ pack.workflows.length }} 个工作流</div>
        </div>

        <!-- 标签 -->
        <div class="flex flex-wrap gap-1.5">
          <span
            v-for="tag in pack.tags"
            :key="tag"
            class="text-[10px] px-2 py-0.5 rounded-full bg-surface-3 text-gray-400"
          >
            {{ tag }}
          </span>
        </div>

        <div class="grid grid-cols-4 gap-2 pt-1">
          <button
            class="py-1.5 rounded-lg text-[11px] font-medium bg-surface-2 text-gray-300 hover:bg-surface-3 transition-colors"
            :class="previewLoading && selectedPack?.id === pack.id ? 'opacity-70 cursor-wait' : ''"
            @click.stop="openPackPreview(pack)"
          >
            查看详情
          </button>
          <button
            class="py-1.5 rounded-lg text-[11px] font-medium bg-surface-2 text-amber-300 hover:bg-surface-3 transition-colors"
            :class="starringPackId === pack.id ? 'opacity-70 cursor-wait' : ''"
            @click.stop="handleStar(pack)"
          >
            {{ starringPackId === pack.id ? '处理中...' : '点赞' }}
          </button>
          <button
            class="py-1.5 rounded-lg text-[11px] font-medium bg-surface-2 text-cyan-300 hover:bg-surface-3 transition-colors"
            :class="downloadingPackId === pack.id ? 'opacity-70 cursor-wait' : ''"
            @click.stop="handleDownload(pack)"
          >
            {{ downloadingPackId === pack.id ? '导出中...' : '下载' }}
          </button>
          <button
            v-if="importSuccess !== pack.id"
            class="py-1.5 rounded-lg text-[11px] font-medium bg-accent/15 text-accent hover:bg-accent/25 transition-colors"
            :class="importingPackId === pack.id ? 'cursor-wait opacity-70' : ''"
            :disabled="importingPackId === pack.id"
            @click.stop="handleImport(pack)"
          >
            {{ importingPackId === pack.id ? '导入中...' : '导入' }}
          </button>
          <div
            v-else
            class="py-1.5 rounded-lg text-[11px] font-medium bg-emerald-500/15 text-emerald-400 text-center"
          >
            导入成功
          </div>
        </div>

        <!-- 展开的模式列表 -->
        <div v-if="expandedPackId === pack.id" class="border-t border-surface-3 pt-3 space-y-2">
          <div class="text-[10px] text-gray-500 mb-1">包含的模式</div>
          <div
            v-for="pattern in pack.patterns"
            :key="pattern.id"
            class="bg-surface-2 rounded-lg p-2.5 space-y-1"
          >
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-gray-300">{{ pattern.name }}</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded" :class="categoryColorMap[pattern.category]">
                {{ pattern.confidence }}%
              </span>
            </div>
            <div class="text-[10px] text-gray-500">{{ pattern.description }}</div>
            <div class="text-[10px] text-gray-600 font-mono">{{ pattern.rule }}</div>
          </div>
          <div v-if="pack.workflows.length" class="pt-1">
            <div class="text-[10px] text-gray-500 mb-1">包含的工作流</div>
            <div v-for="workflow in pack.workflows" :key="workflow.id" class="bg-surface-2 rounded-lg p-2.5 mb-1.5">
              <div class="text-xs text-gray-300">{{ workflow.name }}</div>
              <div class="text-[10px] text-gray-500 mt-1">{{ workflow.steps.length }} 个步骤</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="selectedPack" class="fixed inset-0 z-[120] flex items-center justify-center px-6" @click.self="closePackPreview">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" />
        <div class="relative w-full max-w-5xl max-h-[88vh] overflow-hidden rounded-2xl border border-surface-3 bg-surface-1 shadow-2xl">
          <div class="flex items-start justify-between gap-4 px-6 py-5 border-b border-surface-3">
            <div>
              <div class="flex items-center gap-2">
                <span class="text-sm font-semibold text-gray-100">{{ previewPack.display }}</span>
                <span class="text-[10px] px-2 py-0.5 rounded border" :class="categoryColorMap[getPrimaryCategory(previewPack.tags)]">
                  {{ categories.find(c => c.key === getPrimaryCategory(previewPack.tags))?.label }}
                </span>
              </div>
              <div class="text-xs text-gray-500 mt-1">{{ previewPack.author.username }} · {{ previewPack.author.title }}</div>
              <div class="text-sm text-gray-400 mt-3 max-w-3xl leading-relaxed">{{ previewPack.description }}</div>
            </div>
            <button class="text-gray-500 hover:text-gray-300 text-xl leading-none" @click="closePackPreview">x</button>
          </div>

          <div class="grid grid-cols-[1.2fr_0.8fr] gap-0 max-h-[calc(88vh-92px)]">
            <div class="overflow-y-auto p-6 space-y-4 border-r border-surface-3">
              <div>
                <div class="text-xs uppercase tracking-[0.18em] text-gray-500 mb-3">行为准则</div>
                <div class="space-y-3">
                  <div v-for="pattern in previewPack.patterns" :key="pattern.id" class="bg-surface-2 rounded-xl p-4 border border-surface-3">
                    <div class="flex items-center justify-between gap-3">
                      <div class="text-sm font-medium text-gray-100">{{ pattern.name }}</div>
                      <span class="text-[10px] px-2 py-0.5 rounded border" :class="categoryColorMap[pattern.category]">{{ pattern.confidence }}%</span>
                    </div>
                    <div class="text-xs text-gray-400 mt-2 leading-relaxed">{{ pattern.description }}</div>
                    <div class="text-[10px] text-gray-500 mt-3 font-mono">{{ pattern.rule }}</div>
                  </div>
                </div>
              </div>
            </div>

            <div class="overflow-y-auto p-6 space-y-4">
              <div class="grid grid-cols-2 gap-3">
                <div class="bg-surface-2 rounded-xl p-3">
                  <div class="text-[11px] text-gray-500">下载量</div>
                  <div class="text-xl font-semibold text-cyan-300 mt-1">{{ formatCount(previewPack.downloads) }}</div>
                </div>
                <div class="bg-surface-2 rounded-xl p-3">
                  <div class="text-[11px] text-gray-500">点赞</div>
                  <div class="text-xl font-semibold text-amber-300 mt-1">{{ formatCount(previewPack.stars) }}</div>
                </div>
                <div class="bg-surface-2 rounded-xl p-3">
                  <div class="text-[11px] text-gray-500">模式</div>
                  <div class="text-xl font-semibold text-gray-100 mt-1">{{ previewPack.patterns.length }}</div>
                </div>
                <div class="bg-surface-2 rounded-xl p-3">
                  <div class="text-[11px] text-gray-500">工作流</div>
                  <div class="text-xl font-semibold text-emerald-400 mt-1">{{ previewPack.workflows.length }}</div>
                </div>
              </div>

              <div class="bg-surface-2 rounded-xl p-4">
                <div class="text-xs uppercase tracking-[0.18em] text-gray-500 mb-3">工作流</div>
                <div class="space-y-3">
                  <div v-for="workflow in previewPack.workflows" :key="workflow.id" class="border border-surface-3 rounded-xl p-3">
                    <div class="text-sm text-gray-100">{{ workflow.name }}</div>
                    <div class="text-[11px] text-gray-500 mt-1">{{ workflow.description }}</div>
                    <div class="mt-3 space-y-2">
                      <div v-for="(step, index) in workflow.steps" :key="`${workflow.id}-${index}`" class="flex items-start gap-2 text-[11px] text-gray-300">
                        <span class="mt-1 w-1.5 h-1.5 rounded-full bg-openclaw shrink-0" />
                        <span>{{ step.pattern || step.inline || step.when || step.gate || '步骤' }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="bg-surface-2 rounded-xl p-4">
                <div class="text-xs uppercase tracking-[0.18em] text-gray-500 mb-3">标签</div>
                <div class="flex flex-wrap gap-2">
                  <span v-for="tag in previewPack.tags" :key="tag" class="text-[10px] px-2 py-0.5 rounded-full bg-surface-3 text-gray-300">{{ tag }}</span>
                </div>
              </div>

              <div class="grid grid-cols-3 gap-2">
                <button class="py-2 rounded-lg text-xs font-medium bg-accent/15 text-accent hover:bg-accent/25" @click="handleImport(previewPack)">
                  {{ importingPackId === previewPack.id ? '导入中...' : '导入到本地' }}
                </button>
                <button class="py-2 rounded-lg text-xs font-medium bg-surface-2 text-amber-300 hover:bg-surface-3" @click="handleStar(previewPack)">
                  {{ starringPackId === previewPack.id ? '处理中...' : '点赞支持' }}
                </button>
                <button class="py-2 rounded-lg text-xs font-medium bg-surface-2 text-cyan-300 hover:bg-surface-3" @click="handleDownload(previewPack)">
                  {{ downloadingPackId === previewPack.id ? '导出中...' : '下载 JSON' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 发布我的模式 -->
    <div class="bg-surface-1 rounded-xl border border-accent/30 p-5 space-y-4">
      <div class="text-sm font-medium text-accent">发布我的 ClawProfile</div>
      <div class="text-xs text-gray-400">将 active profile 元信息、选中模式和关联工作流整体发布到社区</div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <div class="text-[10px] text-gray-500 mb-1">ClawProfile 展示名称</div>
          <input
            v-model="publishName"
            type="text"
            placeholder="输入 Shared ClawProfile 名称..."
            class="w-full bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-xs text-gray-300 outline-none focus:border-accent transition-colors"
          />
        </div>
        <div>
          <div class="text-[10px] text-gray-500 mb-1">分类</div>
          <select
            v-model="publishCategory"
            class="w-full bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-xs text-gray-300 outline-none focus:border-accent transition-colors"
          >
            <option v-for="cat in categories.filter(c => c.key !== 'all')" :key="cat.key" :value="cat.key">
              {{ cat.label }}
            </option>
          </select>
        </div>
      </div>

      <div>
          <div class="text-[10px] text-gray-500 mb-1">描述</div>
        <textarea
          v-model="publishDesc"
          placeholder="描述这个 ClawProfile 的适用对象、风格和价值..."
          rows="2"
          class="w-full bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-xs text-gray-300 outline-none focus:border-accent transition-colors resize-none"
        />
      </div>

      <div>
        <div class="text-[10px] text-gray-500 mb-1">标签（逗号分隔）</div>
        <input
          v-model="publishTags"
          type="text"
          placeholder="如: python, 效率, 代码规范"
          class="w-full bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-xs text-gray-300 outline-none focus:border-accent transition-colors"
        />
      </div>

      <!-- 选择要发布的模式 -->
      <div>
        <div class="text-[10px] text-gray-500 mb-2">
          选择要发布的模式（将自动携带关联工作流）
          <span v-if="publishablePatterns.length === 0" class="text-yellow-500 ml-2">— 请先在模式页面确认模式</span>
        </div>
        <div v-if="publishablePatterns.length > 0" class="space-y-1.5 max-h-40 overflow-y-auto pr-1">
          <label
            v-for="p in publishablePatterns"
            :key="p.id"
            class="flex items-center gap-2.5 cursor-pointer p-2 rounded-lg hover:bg-surface-2 transition-colors"
          >
            <input
              type="checkbox"
              :checked="selectedPatternIds.has(p.id)"
              class="w-3.5 h-3.5 rounded accent-accent shrink-0"
              @change="togglePatternSelect(p.id)"
            />
            <span class="text-xs text-gray-300 flex-1 truncate">{{ p.name }}</span>
            <span class="text-[10px] text-gray-500 shrink-0">{{ p.confidence }}%</span>
            <span
              class="text-[10px] px-1.5 py-0.5 rounded shrink-0"
              :class="p.status === 'exportable' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-blue-500/20 text-blue-400'"
            >
              {{ p.status === 'exportable' ? '可导出' : '已确认' }}
            </span>
          </label>
        </div>
        <div v-if="selectedPatternIds.size > 0" class="text-[10px] text-accent mt-1">
          已选择 {{ selectedPatternIds.size }} 个模式
        </div>
      </div>

      <div class="flex items-center justify-between">
        <div v-if="publishSuccess" class="text-xs text-emerald-400 bg-emerald-500/10 rounded-lg px-3 py-1.5">
          发布成功，已添加到社区
        </div>
        <div v-else class="text-[10px] text-gray-600">
          {{ canPublish ? '准备发布' : '请填写名称、描述并选择至少一个模式' }}
        </div>
        <button
          class="px-5 py-2 rounded-lg text-xs font-medium transition-colors"
          :class="canPublish && !publishing
            ? 'bg-accent/20 text-accent hover:bg-accent/30 cursor-pointer'
            : 'bg-surface-3 text-gray-600 cursor-not-allowed'"
          :disabled="!canPublish || publishing"
          @click="handlePublish"
        >
          {{ publishing ? '发布中...' : '发布' }}
        </button>
      </div>
    </div>
  </div>
</template>

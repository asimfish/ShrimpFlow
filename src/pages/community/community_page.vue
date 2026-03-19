<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

import type { SharedPatternPack } from '@/types'
import { getPacksApi } from '@/http_api/community'

const searchQuery = ref('')
const categoryFilter = ref('all')
const expandedPackId = ref<number | null>(null)
const importSuccess = ref<number | null>(null)

const publishName = ref('')
const publishDesc = ref('')
const publishCategory = ref('coding')

const packs = ref<SharedPatternPack[]>([])

onMounted(async () => {
  const packRes = await getPacksApi()
  if (packRes.data) packs.value = packRes.data
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

const filteredPacks = computed(() => {
  let result: SharedPatternPack[] = packs.value
  if (categoryFilter.value !== 'all') {
    result = result.filter(p => p.category === categoryFilter.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(p =>
      p.name.toLowerCase().includes(q)
      || p.description.toLowerCase().includes(q)
      || p.tags.some(t => t.toLowerCase().includes(q))
      || p.author.username.toLowerCase().includes(q)
    )
  }
  return result
})

const toggleExpand = (id: number) => {
  expandedPackId.value = expandedPackId.value === id ? null : id
}

const handleImport = (packId: number) => {
  importSuccess.value = packId
  setTimeout(() => { importSuccess.value = null }, 2500)
}

const formatCount = (n: number) => {
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

const handlePublish = () => {
  publishName.value = ''
  publishDesc.value = ''
  publishCategory.value = 'coding'
}
</script>

<template>
  <div class="p-6 space-y-6 overflow-y-auto h-full">
    <!-- 页面标题 -->
    <div>
      <h1 class="text-2xl font-semibold">社区分享</h1>
      <p class="text-sm text-gray-400 mt-1">发现和导入社区中优秀开发者的行为模式包</p>
    </div>

    <!-- 搜索栏 -->
    <div class="relative">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
      </svg>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索模式包、作者、标签..."
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
      共 {{ filteredPacks.length }} 个模式包
    </div>

    <!-- 模式包卡片网格 -->
    <div class="grid grid-cols-2 gap-4">
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

        <!-- 包名称和分类 -->
        <div class="flex items-start justify-between gap-2">
          <div class="text-sm font-medium text-gray-200 leading-snug">{{ pack.name }}</div>
          <span class="text-[10px] px-2 py-0.5 rounded border shrink-0" :class="categoryColorMap[pack.category]">
            {{ categories.find(c => c.key === pack.category)?.label }}
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
          <div class="text-[10px] text-gray-600">{{ pack.patterns.length }} 个模式</div>
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

        <!-- 导入按钮 -->
        <div class="pt-1">
          <button
            v-if="importSuccess !== pack.id"
            class="w-full py-1.5 rounded-lg text-xs font-medium bg-accent/15 text-accent hover:bg-accent/25 transition-colors"
            @click.stop="handleImport(pack.id)"
          >
            导入到我的模式库
          </button>
          <div
            v-else
            class="w-full py-1.5 rounded-lg text-xs font-medium bg-emerald-500/15 text-emerald-400 text-center"
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
        </div>
      </div>
    </div>

    <!-- 发布我的模式 -->
    <div class="bg-surface-1 rounded-xl border border-accent/30 p-5 space-y-4">
      <div class="text-sm font-medium text-accent">发布我的模式</div>
      <div class="text-xs text-gray-400">将你的行为模式打包分享给社区</div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <div class="text-[10px] text-gray-500 mb-1">模式包名称</div>
          <input
            v-model="publishName"
            type="text"
            placeholder="输入模式包名称..."
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
          placeholder="描述你的模式包..."
          rows="3"
          class="w-full bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-xs text-gray-300 outline-none focus:border-accent transition-colors resize-none"
        />
      </div>
      <div class="flex justify-end">
        <button
          class="px-5 py-2 rounded-lg text-xs font-medium transition-colors"
          :class="publishName && publishDesc
            ? 'bg-accent/20 text-accent hover:bg-accent/30 cursor-pointer'
            : 'bg-surface-3 text-gray-600 cursor-not-allowed'"
          :disabled="!publishName || !publishDesc"
          @click="handlePublish"
        >
          发布
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

import { confirmPatternApi, rejectPatternApi, getPendingPatternsApi } from '@/http_api/patterns'

type PendingCard = {
  id: number
  name: string
  category: string
  confidence: number
  description: string
  evidence_count: number
  loading: boolean
}

const cards = ref<PendingCard[]>([])
const MAX_VISIBLE = 3

const categoryLabel: Record<string, string> = {
  coding: '编码',
  review: '审查',
  git: 'Git',
  devops: 'DevOps',
  collaboration: '协作',
}

const categoryColor: Record<string, string> = {
  coding: 'bg-accent/20 text-accent',
  review: 'bg-openclaw/20 text-openclaw',
  git: 'bg-git/20 text-git',
  devops: 'bg-terminal/20 text-terminal',
  collaboration: 'bg-purple-500/20 text-purple-400',
}

const addCard = (pattern: PendingCard) => {
  if (cards.value.some(c => c.id === pattern.id)) return
  cards.value.push({ ...pattern, loading: false })
  // 只保留最新 MAX_VISIBLE 张
  if (cards.value.length > MAX_VISIBLE) {
    cards.value = cards.value.slice(-MAX_VISIBLE)
  }
}

const removeCard = (id: number) => {
  cards.value = cards.value.filter(c => c.id !== id)
}

const handleConfirm = async (card: PendingCard) => {
  card.loading = true
  const res = await confirmPatternApi(card.id)
  card.loading = false
  if (res.data) {
    removeCard(card.id)
  }
}

const handleReject = async (card: PendingCard) => {
  card.loading = true
  const res = await rejectPatternApi(card.id)
  card.loading = false
  if (res.data) {
    removeCard(card.id)
  }
}

const onPatternPending = (e: Event) => {
  const detail = (e as CustomEvent).detail
  if (detail && typeof detail === 'object' && 'id' in detail) {
    addCard(detail as PendingCard)
  }
}

onMounted(async () => {
  window.addEventListener('pattern-pending', onPatternPending)
  // 启动时加载已有待确认模式
  const res = await getPendingPatternsApi()
  if (res.data) {
    for (const p of res.data.slice(0, MAX_VISIBLE)) {
      addCard({
        id: p.id,
        name: p.name,
        category: p.category,
        confidence: p.confidence,
        description: p.description,
        evidence_count: p.evidence_count,
        loading: false,
      })
    }
  }
})

onUnmounted(() => {
  window.removeEventListener('pattern-pending', onPatternPending)
})
</script>

<template>
  <Teleport to="body">
    <div class="fixed bottom-6 right-6 z-50 flex flex-col gap-3 w-80">
      <TransitionGroup name="toast-slide">
        <div
          v-for="card in cards"
          :key="card.id"
          class="bg-surface-1 border border-surface-3 rounded-xl p-4 shadow-xl shadow-black/30"
        >
          <!-- header -->
          <div class="flex items-center gap-2 mb-2">
            <span
              class="text-[10px] px-1.5 py-0.5 rounded font-medium"
              :class="categoryColor[card.category]"
            >
              {{ categoryLabel[card.category] }}
            </span>
            <span class="text-xs text-gray-200 font-medium truncate flex-1">{{ card.name }}</span>
            <button
              class="text-gray-500 hover:text-gray-300 text-xs"
              @click="removeCard(card.id)"
            >
              x
            </button>
          </div>

          <!-- confidence bar -->
          <div class="flex items-center gap-2 mb-2">
            <div class="flex-1 h-1.5 bg-surface-3 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all"
                :class="card.confidence >= 90 ? 'bg-emerald-400' : card.confidence >= 70 ? 'bg-purple-400' : 'bg-yellow-400'"
                :style="{ width: `${card.confidence}%` }"
              />
            </div>
            <span class="text-[10px] text-gray-500 w-8 text-right">{{ card.confidence }}%</span>
          </div>

          <!-- description -->
          <div class="text-[11px] text-gray-400 line-clamp-2 mb-1">{{ card.description }}</div>
          <div class="text-[10px] text-gray-600 mb-3">{{ card.evidence_count }} 条证据支撑</div>

          <!-- actions -->
          <div class="flex gap-2">
            <button
              class="flex-1 text-xs py-1.5 rounded-lg font-medium transition-colors"
              :class="card.loading ? 'bg-surface-3 text-gray-500 cursor-wait' : 'bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 cursor-pointer'"
              :disabled="card.loading"
              @click="handleConfirm(card)"
            >
              确认加入
            </button>
            <button
              class="flex-1 text-xs py-1.5 rounded-lg font-medium transition-colors"
              :class="card.loading ? 'bg-surface-3 text-gray-500 cursor-wait' : 'bg-surface-2 text-gray-400 hover:bg-surface-3 cursor-pointer'"
              :disabled="card.loading"
              @click="handleReject(card)"
            >
              不是有意义的
            </button>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-slide-enter-active { transition: all 0.3s ease; }
.toast-slide-leave-active { transition: all 0.2s ease; }
.toast-slide-enter-from { opacity: 0; transform: translateX(40px); }
.toast-slide-leave-to { opacity: 0; transform: translateX(40px); }
.toast-slide-move { transition: transform 0.3s ease; }
</style>

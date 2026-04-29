<script setup lang="ts">
import { useToast } from '@/libs/toast'

const { toasts, dismiss } = useToast()

const levelClass = (lvl: string) => {
  switch (lvl) {
    case 'error': return 'border-red-500/50 bg-red-950/60'
    case 'warn': return 'border-amber-500/50 bg-amber-950/60'
    case 'success': return 'border-emerald-500/50 bg-emerald-950/60'
    default: return 'border-sky-500/40 bg-sky-950/55'
  }
}

const icon = (lvl: string) => {
  switch (lvl) {
    case 'error': return '!'
    case 'warn': return '!'
    case 'success': return '✓'
    default: return 'i'
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed bottom-4 right-4 z-[200] flex flex-col-reverse gap-2 w-80 pointer-events-none">
      <TransitionGroup name="toast-slide">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="pointer-events-auto rounded-xl border backdrop-blur-md px-3.5 py-3 shadow-lg text-sm"
          :class="levelClass(t.level)"
        >
          <div class="flex items-start gap-2.5">
            <span
              class="mt-0.5 inline-flex w-5 h-5 items-center justify-center rounded-full text-[11px] font-semibold shrink-0"
              :class="{
                'bg-red-500/30 text-red-200': t.level === 'error',
                'bg-amber-500/30 text-amber-200': t.level === 'warn',
                'bg-emerald-500/30 text-emerald-200': t.level === 'success',
                'bg-sky-500/30 text-sky-200': !['error', 'warn', 'success'].includes(t.level),
              }"
            >
              {{ icon(t.level) }}
            </span>
            <div class="flex-1 min-w-0">
              <div class="font-medium leading-snug break-words">{{ t.title }}</div>
              <div v-if="t.detail" class="mt-0.5 text-[11px] text-gray-400 break-words">{{ t.detail }}</div>
            </div>
            <button
              class="text-gray-500 hover:text-gray-200 shrink-0 leading-none"
              @click="dismiss(t.id)"
              :aria-label="'关闭通知'"
            >✕</button>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-slide-enter-active { transition: all 0.22s ease; }
.toast-slide-leave-active { transition: all 0.18s ease; }
.toast-slide-enter-from { opacity: 0; transform: translateY(8px); }
.toast-slide-leave-to { opacity: 0; transform: translateX(12px); }
</style>

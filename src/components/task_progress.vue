<script setup lang="ts">
import { ref, watch, onUnmounted, onMounted } from 'vue'
import { getTaskApi, type BackgroundTask } from '@/http_api/tasks'

const props = defineProps<{
  taskId: string
  storageKey?: string
}>()

const emit = defineEmits<{
  done: [task: BackgroundTask]
  error: [task: BackgroundTask]
}>()

const task = ref<BackgroundTask | null>(null)
const timer = ref<ReturnType<typeof setInterval> | null>(null)

const stopPolling = () => {
  if (timer.value !== null) {
    clearInterval(timer.value)
    timer.value = null
  }
}

const poll = async () => {
  const res = await getTaskApi(props.taskId)
  if (!res.data) return
  task.value = res.data
  if (res.data.status === 'done') {
    stopPolling()
    if (props.storageKey) localStorage.removeItem(props.storageKey)
    emit('done', res.data)
  } else if (res.data.status === 'error') {
    stopPolling()
    if (props.storageKey) localStorage.removeItem(props.storageKey)
    emit('error', res.data)
  }
}

const startPolling = () => {
  stopPolling()
  poll()
  timer.value = setInterval(poll, 1500)
}

onMounted(() => {
  if (props.storageKey) localStorage.setItem(props.storageKey, props.taskId)
  startPolling()
})

onUnmounted(stopPolling)

watch(() => props.taskId, () => {
  if (props.storageKey) localStorage.setItem(props.storageKey, props.taskId)
  startPolling()
})

const statusLabel = (s: string) => {
  if (s === 'pending') return '排队中'
  if (s === 'running') return '运行中'
  if (s === 'done') return '已完成'
  if (s === 'error') return '出错'
  return s
}
</script>

<template>
  <div v-if="task" class="bg-surface-2 rounded-lg border border-surface-3 p-3 space-y-2">
    <div class="flex items-center justify-between text-xs">
      <span class="text-gray-400">{{ task.stage ?? statusLabel(task.status) }}</span>
      <span
        :class="[
          task.status === 'done' ? 'text-emerald-400' :
          task.status === 'error' ? 'text-red-400' :
          'text-amber-400'
        ]"
      >{{ statusLabel(task.status) }}</span>
    </div>
    <div class="w-full bg-surface-3 rounded-full h-1.5">
      <div
        class="h-1.5 rounded-full transition-all duration-500"
        :class="task.status === 'error' ? 'bg-red-500' : 'bg-accent'"
        :style="{ width: task.progress + '%' }"
      />
    </div>
    <div v-if="task.status === 'error'" class="text-xs text-red-400">{{ task.error }}</div>
  </div>
  <div v-else class="text-xs text-gray-500 animate-pulse">加载任务状态…</div>
</template>

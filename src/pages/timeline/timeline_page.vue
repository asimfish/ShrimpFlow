<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'

import { useEventsStore } from '@/stores/events'
import type { DevEvent } from '@/types'
import TimelineToolbar from './timeline_toolbar.vue'
import TimelineCanvas from './timeline_canvas.vue'
import EventDetailPanel from './event_detail_panel.vue'

const eventsStore = useEventsStore()
const selectedEvent = ref<DevEvent | null>(null)
const MAX_TIMELINE_EVENTS = 1200

onMounted(async () => {
  await eventsStore.ensureLoaded()
})

const sampledEvents = computed(() => {
  const items = eventsStore.filteredEvents
  if (items.length <= MAX_TIMELINE_EVENTS) return items

  const pinned = items.filter(event => event.openclaw_session_id).slice(0, 240)
  const pinnedIds = new Set(pinned.map(event => event.id))
  const rest = items.filter(event => !pinnedIds.has(event.id))
  const sampleSize = Math.max(0, MAX_TIMELINE_EVENTS - pinned.length)
  if (sampleSize <= 0) return pinned.slice(0, MAX_TIMELINE_EVENTS)

  const stride = rest.length / sampleSize
  const sampled: DevEvent[] = []
  for (let index = 0; index < sampleSize; index++) {
    const event = rest[Math.floor(index * stride)]
    if (event) sampled.push(event)
  }
  return [...pinned, ...sampled]
    .sort((a, b) => b.timestamp - a.timestamp || b.id - a.id)
    .slice(0, MAX_TIMELINE_EVENTS)
})

const selectEvent = (event: DevEvent) => {
  selectedEvent.value = event
}

const closeDetail = () => {
  selectedEvent.value = null
}
</script>

<template>
  <div class="flex h-full">
    <div class="flex-1 flex flex-col overflow-hidden">
      <div class="p-6 pb-0">
        <h1 class="text-2xl font-semibold">时间线</h1>
        <p class="text-sm text-gray-400 mt-1">你的 OpenClaw 开发活动流</p>
        <p v-if="eventsStore.filteredEvents.length > sampledEvents.length" class="text-[11px] text-amber-400 mt-2">
          为保证流畅度，当前仅渲染 {{ sampledEvents.length }} / {{ eventsStore.filteredEvents.length }} 个事件
        </p>
      </div>
      <TimelineToolbar />
      <div v-if="eventsStore.loading" class="flex-1 flex items-center justify-center text-gray-500">
        <div class="text-center">
          <div class="text-lg mb-2">正在加载事件数据...</div>
          <div class="text-sm text-gray-600">请稍候</div>
        </div>
      </div>
      <div v-else-if="eventsStore.filteredEvents.length === 0" class="flex-1 flex items-center justify-center text-gray-500">
        <div class="text-center">
          <div class="text-lg mb-2">暂无事件数据</div>
          <div class="text-sm text-gray-600">尝试调整筛选条件或采集新数据</div>
        </div>
      </div>
      <TimelineCanvas
        v-else
        :events="sampledEvents"
        @select="selectEvent"
      />
    </div>
    <EventDetailPanel :event="selectedEvent" @close="closeDetail" />
  </div>
</template>

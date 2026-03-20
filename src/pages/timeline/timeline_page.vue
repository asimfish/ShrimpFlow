<script setup lang="ts">
import { ref, onMounted } from 'vue'

import { useEventsStore } from '@/stores/events'
import type { DevEvent } from '@/types'
import TimelineToolbar from './timeline_toolbar.vue'
import TimelineCanvas from './timeline_canvas.vue'
import EventDetailPanel from './event_detail_panel.vue'

const eventsStore = useEventsStore()
const selectedEvent = ref<DevEvent | null>(null)

onMounted(async () => {
  if (eventsStore.events.length === 0) {
    await eventsStore.fetchEvents()
  }
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
        :events="eventsStore.filteredEvents"
        @select="selectEvent"
      />
    </div>
    <EventDetailPanel :event="selectedEvent" @close="closeDetail" />
  </div>
</template>

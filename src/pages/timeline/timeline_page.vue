<script setup lang="ts">
import { ref } from 'vue'

import { useEventsStore } from '@/stores/events'
import type { DevEvent } from '@/types'
import TimelineToolbar from './timeline_toolbar.vue'
import TimelineCanvas from './timeline_canvas.vue'
import EventDetailPanel from './event_detail_panel.vue'

const eventsStore = useEventsStore()
const selectedEvent = ref<DevEvent | null>(null)

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
      <TimelineCanvas
        :events="eventsStore.filteredEvents"
        @select="selectEvent"
      />
    </div>
    <EventDetailPanel :event="selectedEvent" @close="closeDetail" />
  </div>
</template>

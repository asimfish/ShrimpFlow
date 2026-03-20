<script setup lang="ts">
import { KeepAlive, onMounted, onUnmounted } from 'vue'

import AppSidebar from '@/components/layout/app_sidebar.vue'
import GlobalSearch from '@/components/global_search.vue'
import PatternConfirmToast from '@/components/pattern_confirm_toast.vue'
import { useEventsStore } from '@/stores/events'
import { useSkillsStore } from '@/stores/skills'

const eventsStore = useEventsStore()
const skillsStore = useSkillsStore()

onMounted(() => {
  void eventsStore.ensureLoaded()
  eventsStore.startRealtime()
  void skillsStore.ensureLoaded()
})

onUnmounted(() => {
  eventsStore.stopRealtime()
})
</script>

<template>
  <div class="flex h-screen bg-void text-white overflow-hidden">
    <AppSidebar />
    <main class="flex-1 overflow-auto">
      <router-view v-slot="{ Component, route }">
        <KeepAlive :max="8">
          <component
            v-if="route.meta.keepAlive"
            :is="Component"
            :key="String(route.name || route.path)"
          />
        </KeepAlive>
        <transition v-if="!route.meta.keepAlive" name="page-fade" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </main>
    <GlobalSearch />
    <PatternConfirmToast />
  </div>
</template>

<style>
.page-fade-enter-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.page-fade-leave-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.page-fade-enter-from { opacity: 0; transform: translateY(8px); }
.page-fade-leave-to { opacity: 0; transform: translateY(-4px); }
</style>

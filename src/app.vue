<script setup lang="ts">
import { onMounted } from 'vue'

import AppSidebar from '@/components/layout/app_sidebar.vue'
import GlobalSearch from '@/components/global_search.vue'
import { useEventsStore } from '@/stores/events'
import { useSkillsStore } from '@/stores/skills'
import { useOpenClawStore } from '@/stores/openclaw'
import { useDigestStore } from '@/stores/digest'

const eventsStore = useEventsStore()
const skillsStore = useSkillsStore()
const openclawStore = useOpenClawStore()
const digestStore = useDigestStore()

onMounted(() => {
  eventsStore.fetchEvents()
  skillsStore.fetchSkills()
  openclawStore.fetchSessions()
  openclawStore.fetchDocuments()
  digestStore.fetchSummaries()
})
</script>

<template>
  <div class="flex h-screen bg-void text-white overflow-hidden">
    <AppSidebar />
    <main class="flex-1 overflow-auto">
      <router-view v-slot="{ Component, route }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </main>
    <GlobalSearch />
  </div>
</template>

<style>
.page-fade-enter-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.page-fade-leave-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.page-fade-enter-from { opacity: 0; transform: translateY(8px); }
.page-fade-leave-to { opacity: 0; transform: translateY(-4px); }
</style>

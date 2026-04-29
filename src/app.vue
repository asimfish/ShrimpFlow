<script setup lang="ts">
import { KeepAlive, onMounted, onUnmounted, ref } from 'vue'

import AppSidebar from '@/components/layout/app_sidebar.vue'
import GlobalSearch from '@/components/global_search.vue'
import PatternConfirmToast from '@/components/pattern_confirm_toast.vue'
import ToastStack from '@/components/shared/toast_stack.vue'
import { useEventsStore } from '@/stores/events'
import { useSkillsStore } from '@/stores/skills'

const eventsStore = useEventsStore()
const skillsStore = useSkillsStore()

const demoMode = ref(false)
const showDeploy = ref(false)
const copied = ref(false)
const bilibiliUrl = 'https://www.bilibili.com/video/BV1UBAVzyErU/?vd_source=082c9486c13eeaf225d08c23aeccd98c#reply116256560646936'

const checkBackend = async () => {
  try {
    const res = await fetch('/api/stats', { signal: AbortSignal.timeout(3000) })
    demoMode.value = !res.ok
  } catch {
    demoMode.value = true
  }
}

const copyCmd = () => {
  navigator.clipboard.writeText('git clone https://github.com/asimfish/ShrimpFlow.git && cd ShrimpFlow && bash setup.sh')
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

onMounted(() => {
  void eventsStore.ensureLoaded()
  eventsStore.startRealtime()
  void skillsStore.ensureLoaded()
  checkBackend()
})

onUnmounted(() => {
  eventsStore.stopRealtime()
})
</script>

<template>
  <div class="flex h-screen bg-void text-white overflow-hidden">
    <!-- 演示模式 Banner -->
    <div v-if="demoMode" class="fixed top-0 left-0 right-0 z-50 bg-gradient-to-r from-violet-600/90 to-cyan-600/90 backdrop-blur-sm text-white text-center py-2 px-4 text-sm flex items-center justify-center gap-3">
      <span>🎯 演示模式 — 数据来自真实开发者快照</span>
      <a
        :href="bilibiliUrl"
        target="_blank"
        rel="noreferrer"
        class="px-3 py-0.5 bg-white/20 hover:bg-white/30 rounded-full text-xs font-medium transition-colors"
      >B 站演示 →</a>
      <button
        class="px-3 py-0.5 bg-white/20 hover:bg-white/30 rounded-full text-xs font-medium transition-colors"
        @click="showDeploy = true"
      >部署到你的电脑 →</button>
    </div>

    <!-- 部署弹窗 -->
    <Teleport to="body">
      <div v-if="showDeploy" class="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm" @click.self="showDeploy = false">
        <div class="bg-[#12121a] border border-[#252535] rounded-2xl p-8 max-w-lg w-full mx-4 shadow-2xl">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-semibold">一键部署 DevTwin</h2>
            <button class="text-gray-500 hover:text-white text-xl" @click="showDeploy = false">✕</button>
          </div>

          <div class="space-y-4 text-sm">
            <div class="text-gray-400">只需一条命令，在你的电脑上运行完整的 DevTwin 系统：</div>

            <div class="bg-[#0a0a0f] rounded-xl p-4 font-mono text-xs leading-relaxed">
              <span class="text-emerald-400">$</span>
              <span class="text-gray-300"> git clone https://github.com/asimfish/ShrimpFlow.git && cd ShrimpFlow && bash setup.sh</span>
            </div>

            <button
              class="w-full py-2.5 rounded-xl text-sm font-medium transition-all"
              :class="copied ? 'bg-emerald-600 text-white' : 'bg-violet-600 hover:bg-violet-500 text-white'"
              @click="copyCmd"
            >
              {{ copied ? '✓ 已复制到剪贴板' : '复制命令' }}
            </button>

            <div class="border-t border-[#252535] pt-4 space-y-2 text-gray-500 text-xs">
              <div class="font-medium text-gray-400">前置要求</div>
              <div>• Node.js 18+ &amp; Git</div>
              <div>• Anthropic API Key（<a href="https://console.anthropic.com/" target="_blank" class="text-violet-400 hover:underline">获取</a>）</div>
              <div>• setup.sh 会自动安装 uv、pnpm 等依赖</div>
            </div>

            <div class="border-t border-[#252535] pt-4 space-y-2 text-gray-500 text-xs">
              <div class="font-medium text-gray-400">安装后</div>
              <div>• 前端: http://localhost:5173</div>
              <div>• 后端: http://localhost:7891</div>
              <div>• 系统会自动采集你的 AI 使用数据并开始学习</div>
            </div>

            <a
              :href="bilibiliUrl"
              target="_blank"
              rel="noreferrer"
              class="block text-center text-xs text-violet-400 hover:text-violet-300 hover:underline"
            >查看 B 站宣传演示</a>
          </div>
        </div>
      </div>
    </Teleport>

    <AppSidebar />
    <main class="flex-1 overflow-auto" :class="{ 'pt-10': demoMode }">
      <router-view v-slot="{ Component, route }">
        <transition name="page-fade" mode="out-in">
          <KeepAlive v-if="route.meta.keepAlive" :max="8">
            <component :is="Component" :key="String(route.name || route.path)" />
          </KeepAlive>
          <component v-else :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </main>
    <GlobalSearch />
    <PatternConfirmToast />
    <ToastStack />
  </div>
</template>

<style>
.page-fade-enter-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.page-fade-leave-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.page-fade-enter-from { opacity: 0; transform: translateY(8px); }
.page-fade-leave-to { opacity: 0; transform: translateY(-4px); }
</style>

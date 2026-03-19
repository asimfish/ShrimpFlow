<script setup lang="ts">
import { computed } from 'vue'

import { useOpenClawStore } from '@/stores/openclaw'
import { dayjs } from '@/libs/dayjs'

const store = useOpenClawStore()

// 默认选中第一个会话
if (!store.selectedSessionId && store.sessions.length > 0) {
  store.selectSession(store.sessions[0].id)
}

const categories = ['', 'paper', 'debug', 'review', 'experiment', 'architecture', 'learning']
const categoryLabels: Record<string, string> = {
  '': '全部',
  paper: '论文分析',
  debug: '调试排查',
  review: '代码审查',
  experiment: '实验总结',
  architecture: '方案设计',
  learning: '学习探索',
}

const categoryColors: Record<string, string> = {
  paper: 'bg-blue-500/20 text-blue-400',
  debug: 'bg-red-500/20 text-red-400',
  review: 'bg-openclaw/20 text-openclaw',
  experiment: 'bg-emerald-500/20 text-emerald-400',
  architecture: 'bg-purple-500/20 text-purple-400',
  learning: 'bg-cyan-500/20 text-cyan-400',
}

const docTypeLabels: Record<string, string> = {
  daily_task: '每日任务',
  paper_note: '论文笔记',
  experiment_log: '实验日志',
  meeting_note: '会议纪要',
}

const docTypeColors: Record<string, string> = {
  daily_task: 'bg-accent/20 text-accent',
  paper_note: 'bg-blue-500/20 text-blue-400',
  experiment_log: 'bg-emerald-500/20 text-emerald-400',
  meeting_note: 'bg-openclaw/20 text-openclaw',
}

const formatTime = (ts: number) => dayjs(ts * 1000).format('MM-DD HH:mm')

const selectedDocId = computed({
  get: () => store.documents[0]?.id ?? 0,
  set: () => {},
})
</script>

<template>
  <div class="flex h-full">
    <!-- 左侧面板 -->
    <div class="w-72 shrink-0 bg-surface-1 border-r border-surface-3 flex flex-col">
      <!-- Tab 切换 -->
      <div class="flex border-b border-surface-3">
        <button
          class="flex-1 py-3 text-xs font-medium transition-colors"
          :class="store.activeTab === 'sessions' ? 'text-openclaw border-b-2 border-openclaw' : 'text-gray-500 hover:text-gray-300'"
          @click="store.activeTab = 'sessions'"
        >
          对话记录
        </button>
        <button
          class="flex-1 py-3 text-xs font-medium transition-colors"
          :class="store.activeTab === 'documents' ? 'text-openclaw border-b-2 border-openclaw' : 'text-gray-500 hover:text-gray-300'"
          @click="store.activeTab = 'documents'"
        >
          知识库
        </button>
      </div>

      <!-- 会话列表 -->
      <template v-if="store.activeTab === 'sessions'">
        <!-- 类别筛选 -->
        <div class="p-2 flex flex-wrap gap-1 border-b border-surface-3">
          <button
            v-for="cat in categories"
            :key="cat"
            class="text-[10px] px-2 py-1 rounded-full transition-colors"
            :class="store.categoryFilter === cat ? 'bg-openclaw/20 text-openclaw' : 'bg-surface-2 text-gray-500 hover:text-gray-300'"
            @click="store.categoryFilter = cat"
          >
            {{ categoryLabels[cat] }}
          </button>
        </div>

        <!-- 列表 -->
        <div class="flex-1 overflow-y-auto">
          <button
            v-for="session in store.filteredSessions"
            :key="session.id"
            class="w-full text-left p-3 border-b border-surface-3/50 transition-colors"
            :class="store.selectedSessionId === session.id ? 'bg-surface-2' : 'hover:bg-surface-2/50'"
            @click="store.selectSession(session.id)"
          >
            <div class="flex items-center gap-2 mb-1">
              <span class="text-[10px] px-1.5 py-0.5 rounded" :class="categoryColors[session.category]">
                {{ categoryLabels[session.category] }}
              </span>
            </div>
            <div class="text-xs text-gray-200 line-clamp-2">{{ session.title }}</div>
            <div class="flex items-center gap-2 mt-1.5">
              <span class="text-[10px] text-gray-500">{{ session.project }}</span>
              <span class="text-[10px] text-gray-600">{{ formatTime(session.created_at) }}</span>
            </div>
          </button>
        </div>
      </template>

      <!-- 知识库文档列表 -->
      <template v-else>
        <div class="flex-1 overflow-y-auto">
          <button
            v-for="doc in store.documents"
            :key="doc.id"
            class="w-full text-left p-3 border-b border-surface-3/50 transition-colors hover:bg-surface-2/50"
            @click="selectedDocId = doc.id"
          >
            <div class="flex items-center gap-2 mb-1">
              <span class="text-[10px] px-1.5 py-0.5 rounded" :class="docTypeColors[doc.type]">
                {{ docTypeLabels[doc.type] }}
              </span>
            </div>
            <div class="text-xs text-gray-200 line-clamp-2">{{ doc.title }}</div>
            <div class="text-[10px] text-gray-500 mt-1">{{ formatTime(doc.created_at) }}</div>
          </button>
        </div>
      </template>
    </div>

    <!-- 右侧内容区 -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- 会话对话视图 -->
      <template v-if="store.activeTab === 'sessions' && store.selectedSession">
        <!-- 会话头部 -->
        <div class="p-4 border-b border-surface-3">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-[10px] px-1.5 py-0.5 rounded" :class="categoryColors[store.selectedSession.category]">
              {{ categoryLabels[store.selectedSession.category] }}
            </span>
            <span class="text-xs text-gray-500">{{ store.selectedSession.project }}</span>
          </div>
          <h2 class="text-base font-medium text-gray-200">{{ store.selectedSession.title }}</h2>
          <p class="text-xs text-gray-500 mt-1">{{ store.selectedSession.summary }}</p>
          <div class="flex flex-wrap gap-1 mt-2">
            <span v-for="tag in store.selectedSession.tags" :key="tag" class="text-[10px] px-1.5 py-0.5 rounded-full bg-surface-3 text-gray-400">
              {{ tag }}
            </span>
          </div>
        </div>

        <!-- 对话消息 -->
        <div class="flex-1 overflow-y-auto p-4 space-y-4">
          <div
            v-for="(msg, idx) in store.selectedSession.messages"
            :key="idx"
            class="flex"
            :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[75%] rounded-xl px-4 py-3"
              :class="msg.role === 'user' ? 'bg-accent/20 text-gray-200' : 'bg-surface-2 text-gray-300 border border-surface-3'"
            >
              <!-- 角色标识 -->
              <div class="flex items-center gap-1.5 mb-2">
                <div
                  v-if="msg.role === 'assistant'"
                  class="w-4 h-4 rounded-full bg-openclaw/30 flex items-center justify-center"
                >
                  <span class="text-[8px] text-openclaw font-bold">OC</span>
                </div>
                <span class="text-[10px]" :class="msg.role === 'user' ? 'text-accent' : 'text-openclaw'">
                  {{ msg.role === 'user' ? '你' : 'OpenClaw' }}
                </span>
                <span class="text-[10px] text-gray-600">{{ formatTime(msg.timestamp) }}</span>
              </div>
              <!-- 消息内容 - 简单渲染 markdown -->
              <div class="text-xs leading-relaxed whitespace-pre-wrap">{{ msg.content }}</div>
            </div>
          </div>
        </div>
      </template>

      <!-- 知识库文档视图 -->
      <template v-else-if="store.activeTab === 'documents' && store.documents.length">
        <div class="flex-1 overflow-y-auto p-6">
          <div v-for="doc in store.documents" :key="doc.id" class="mb-6 bg-surface-1 rounded-xl border border-surface-3 p-5">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-[10px] px-1.5 py-0.5 rounded" :class="docTypeColors[doc.type]">
                {{ docTypeLabels[doc.type] }}
              </span>
              <span class="text-[10px] text-gray-500">{{ formatTime(doc.created_at) }}</span>
            </div>
            <h3 class="text-sm font-medium text-gray-200 mb-3">{{ doc.title }}</h3>
            <div class="text-xs text-gray-400 leading-relaxed whitespace-pre-wrap">{{ doc.content }}</div>
            <div class="flex flex-wrap gap-1 mt-3">
              <span v-for="tag in doc.tags" :key="tag" class="text-[10px] px-1.5 py-0.5 rounded-full bg-surface-3 text-gray-500">
                {{ tag }}
              </span>
            </div>
          </div>
        </div>
      </template>

      <!-- 空状态 -->
      <template v-else>
        <div class="flex-1 flex items-center justify-center">
          <div class="text-center text-gray-500">
            <div class="text-3xl mb-2 opacity-30">&#128172;</div>
            <div class="text-sm">选择一个会话查看详情</div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

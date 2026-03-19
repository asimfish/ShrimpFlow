<script setup lang="ts">
import { ref } from 'vue'

// 当前展开的详情面板
const activeDetail = ref<string>('')

const toggleDetail = (key: string) => {
  activeDetail.value = activeDetail.value === key ? '' : key
}

// 颜色映射
const dotColorMap: Record<string, string> = {
  terminal: 'bg-terminal',
  git: 'bg-git',
  openclaw: 'bg-openclaw',
  claude: 'bg-claude',
  danger: 'bg-red-500',
  accent: 'bg-accent',
  success: 'bg-emerald-500',
}

const borderColorMap: Record<string, string> = {
  terminal: 'border-terminal shadow-lg',
  git: 'border-git shadow-lg',
  openclaw: 'border-openclaw shadow-lg',
  claude: 'border-claude shadow-lg',
  danger: 'border-red-500 shadow-lg',
  accent: 'border-accent shadow-lg',
  success: 'border-emerald-500 shadow-lg',
}

const iconBgMap: Record<string, string> = {
  accent: 'bg-accent/15',
  openclaw: 'bg-openclaw/15',
  claude: 'bg-purple-500/15',
  success: 'bg-emerald-500/15',
}

const iconTextMap: Record<string, string> = {
  accent: 'text-accent',
  openclaw: 'text-openclaw',
  claude: 'text-purple-400',
  success: 'text-emerald-400',
}

// 数据源节点
const dataSources = [
  { key: 'terminal', label: '终端命令', color: 'terminal', desc: 'Shell 命令、脚本执行、进程管理' },
  { key: 'git', label: 'Git 操作', color: 'git', desc: '提交、分支、合并、代码审查' },
  { key: 'openclaw', label: 'OpenClaw', color: 'openclaw', desc: '对话、技能调用、知识检索' },
  { key: 'claude', label: 'Claude Code', color: 'claude', desc: '代码编辑、重构、调试辅助' },
  { key: 'env', label: '环境变量', color: 'danger', desc: '系统配置、运行时环境、硬件信息' },
]

// 处理管线层
const pipelines = [
  { key: 'shadow', label: 'Shadow', sub: '采集层', color: 'accent', icon: 'eye' },
  { key: 'mirror', label: 'Mirror', sub: '可视化', color: 'openclaw', icon: 'monitor' },
  { key: 'brain', label: 'Brain', sub: '模式学习', color: 'claude', icon: 'cpu' },
  { key: 'autopilot', label: 'Autopilot', sub: '下发', color: 'success', icon: 'rocket' },
]

// 层详情
const layerDetails: Record<string, { title: string; items: { label: string; desc: string }[] }> = {
  shadow: {
    title: 'Shadow 采集层',
    items: [
      { label: '采集方式', desc: 'Shell hook, Git hook, OpenClaw API, 文件系统监听' },
      { label: '数据格式', desc: '统一 DevEvent 结构' },
      { label: '存储', desc: '本地 SQLite, 端到端加密' },
    ],
  },
  mirror: {
    title: 'Mirror 可视化层',
    items: [
      { label: '可视化', desc: '时间线, 技能图谱, 热力图' },
      { label: '实时更新', desc: 'WebSocket 推送' },
      { label: '交互', desc: '缩放, 筛选, 搜索' },
    ],
  },
  brain: {
    title: 'Brain 模式学习层',
    items: [
      { label: '算法', desc: '频繁序列挖掘 + 时间模式检测' },
      { label: '置信度', desc: '基于证据累积的贝叶斯更新' },
      { label: '输出', desc: '结构化 BehaviorPattern' },
    ],
  },
  autopilot: {
    title: 'Autopilot 下发层',
    items: [
      { label: 'Workflow 组合', desc: '多模式组合成工作流' },
      { label: '团队下发', desc: '一键分享给团队成员' },
      { label: '反馈闭环', desc: '执行结果反哺模式优化' },
    ],
  },
}

// 对比数据
const rlPoints = [
  '行为 -> 梯度更新 -> 神经网络参数',
  '隐式存储, 不可解释',
  '需要大量训练数据',
  '难以迁移到新任务',
]

const dtPoints = [
  '行为 -> 模式提取 -> 结构化存储',
  '显式存储, 可审计可编辑',
  '少量数据即可提取模式',
  '可直接迁移和分享',
]
</script>

<template>
  <div class="p-6 space-y-8 overflow-y-auto h-full">
    <!-- 标题 -->
    <div>
      <h1 class="text-2xl font-bold text-white">ShrimpFlow 系统架构</h1>
      <p class="text-sm text-gray-400 mt-1">数据流与四层处理管线</p>
    </div>

    <!-- 架构图主体 -->
    <div class="flex gap-6 items-start">
      <!-- 左侧: 数据源 -->
      <div class="flex flex-col gap-3 shrink-0 w-44">
        <div class="text-xs text-gray-500 font-mono mb-1">DATA SOURCES</div>
        <div
          v-for="src in dataSources"
          :key="src.key"
          class="bg-surface-2 border border-surface-3 rounded-lg p-3 cursor-pointer transition-all duration-200 hover:scale-[1.02]"
          :class="activeDetail === src.key ? borderColorMap[src.color] : ''"
          @click="toggleDetail(src.key)"
        >
          <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full shrink-0" :class="dotColorMap[src.color]" />
            <span class="text-sm text-white font-medium">{{ src.label }}</span>
          </div>
          <p class="text-[11px] text-gray-500 mt-1 leading-relaxed">{{ src.desc }}</p>
        </div>
      </div>

      <!-- 中间: 箭头连接 -->
      <div class="flex flex-col items-center justify-center pt-10 shrink-0">
        <svg class="w-12 h-64" viewBox="0 0 48 256">
          <defs>
            <linearGradient id="arrow-grad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stop-color="#7c5cfc" stop-opacity="0.6" />
              <stop offset="100%" stop-color="#f59e0b" stop-opacity="0.6" />
            </linearGradient>
          </defs>
          <line v-for="i in 5" :key="i" x1="0" :y1="(i - 1) * 56 + 20" x2="48" :y2="(i - 1) * 56 + 20" stroke="url(#arrow-grad)" stroke-width="1.5" />
          <polygon v-for="i in 5" :key="'a' + i" :points="`40,${(i - 1) * 56 + 15} 48,${(i - 1) * 56 + 20} 40,${(i - 1) * 56 + 25}`" fill="#f59e0b" opacity="0.6" />
        </svg>
      </div>

      <!-- 右侧: 四层管线 -->
      <div class="flex-1 flex flex-col gap-3">
        <div class="text-xs text-gray-500 font-mono mb-1">PROCESSING PIPELINE</div>
        <div class="flex gap-3">
          <div
            v-for="(pipe, idx) in pipelines"
            :key="pipe.key"
            class="flex-1 bg-surface-2 border border-surface-3 rounded-lg p-4 cursor-pointer transition-all duration-200 hover:scale-[1.02] relative"
            :class="activeDetail === pipe.key ? borderColorMap[pipe.color] : ''"
            @click="toggleDetail(pipe.key)"
          >
            <div class="flex items-center gap-2 mb-2">
              <div class="w-8 h-8 rounded-lg flex items-center justify-center" :class="iconBgMap[pipe.color]">
                <svg class="w-4 h-4" :class="iconTextMap[pipe.color]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <template v-if="pipe.icon === 'eye'">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" />
                  </template>
                  <template v-if="pipe.icon === 'monitor'">
                    <rect x="2" y="3" width="20" height="14" rx="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
                  </template>
                  <template v-if="pipe.icon === 'cpu'">
                    <rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" />
                    <line x1="9" y1="1" x2="9" y2="4" /><line x1="15" y1="1" x2="15" y2="4" />
                    <line x1="9" y1="20" x2="9" y2="23" /><line x1="15" y1="20" x2="15" y2="23" />
                    <line x1="20" y1="9" x2="23" y2="9" /><line x1="20" y1="14" x2="23" y2="14" />
                    <line x1="1" y1="9" x2="4" y2="9" /><line x1="1" y1="14" x2="4" y2="14" />
                  </template>
                  <template v-if="pipe.icon === 'rocket'">
                    <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z" />
                    <path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z" />
                    <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 3 0 3 0" />
                    <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-3 0-3" />
                  </template>
                </svg>
              </div>
              <div>
                <div class="text-sm font-semibold text-white">{{ pipe.label }}</div>
                <div class="text-[11px] text-gray-500">{{ pipe.sub }}</div>
              </div>
            </div>
            <!-- 层间箭头 -->
            <div v-if="idx < pipelines.length - 1" class="absolute -right-3 top-1/2 -translate-y-1/2 z-10">
              <svg class="w-6 h-6 text-gray-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </div>
          </div>
        </div>

        <!-- 详情面板 -->
        <Transition name="detail-slide">
          <div
            v-if="activeDetail && layerDetails[activeDetail]"
            class="bg-surface-2 border border-surface-3 rounded-lg p-5 mt-2"
          >
            <h3 class="text-sm font-semibold text-white mb-3">{{ layerDetails[activeDetail].title }}</h3>
            <div class="grid grid-cols-3 gap-4">
              <div
                v-for="item in layerDetails[activeDetail].items"
                :key="item.label"
                class="bg-surface-1 rounded-lg p-3"
              >
                <div class="text-[11px] text-gray-500 mb-1">{{ item.label }}</div>
                <div class="text-xs text-gray-300">{{ item.desc }}</div>
              </div>
            </div>
          </div>
        </Transition>

        <!-- 数据源详情 -->
        <Transition name="detail-slide">
          <div
            v-if="activeDetail && dataSources.find(s => s.key === activeDetail)"
            class="bg-surface-2 border border-surface-3 rounded-lg p-5 mt-2"
          >
            <div class="flex items-center gap-2 mb-2">
              <div class="w-2.5 h-2.5 rounded-full" :class="dotColorMap[dataSources.find(s => s.key === activeDetail)!.color]" />
              <h3 class="text-sm font-semibold text-white">{{ dataSources.find(s => s.key === activeDetail)!.label }}</h3>
            </div>
            <p class="text-xs text-gray-400">{{ dataSources.find(s => s.key === activeDetail)!.desc }}</p>
          </div>
        </Transition>
      </div>
    </div>

    <!-- OpenClaw-RL 对比说明 -->
    <div class="bg-surface-2 border border-surface-3 rounded-xl p-6">
      <h2 class="text-lg font-semibold text-white mb-4">OpenClaw-RL vs ShrimpFlow 记忆机制对比</h2>
      <div class="grid grid-cols-2 gap-6">
        <!-- RL 列 -->
        <div class="bg-surface-1 rounded-lg p-4 border border-surface-3">
          <div class="flex items-center gap-2 mb-3">
            <div class="w-2 h-2 rounded-full bg-openclaw" />
            <span class="text-sm font-medium text-openclaw">OpenClaw-RL (参数化记忆)</span>
          </div>
          <ul class="space-y-2">
            <li v-for="point in rlPoints" :key="point" class="flex items-start gap-2">
              <span class="text-gray-600 mt-0.5 shrink-0">-</span>
              <span class="text-xs text-gray-400">{{ point }}</span>
            </li>
          </ul>
        </div>
        <!-- ShrimpFlow 列 -->
        <div class="bg-surface-1 rounded-lg p-4 border border-surface-3">
          <div class="flex items-center gap-2 mb-3">
            <div class="w-2 h-2 rounded-full bg-accent" />
            <span class="text-sm font-medium text-accent">ShrimpFlow (结构化记忆)</span>
          </div>
          <ul class="space-y-2">
            <li v-for="point in dtPoints" :key="point" class="flex items-start gap-2">
              <span class="text-gray-600 mt-0.5 shrink-0">-</span>
              <span class="text-xs text-gray-400">{{ point }}</span>
            </li>
          </ul>
        </div>
      </div>
      <!-- 底部说明 -->
      <div class="mt-4 pt-4 border-t border-surface-3 text-center">
        <p class="text-xs text-gray-500">
          两者互补: ShrimpFlow 的显式模式可以反哺为 RL 的 reward shaping hints
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail-slide-enter-active { transition: all 0.3s ease; }
.detail-slide-leave-active { transition: all 0.2s ease; }
.detail-slide-enter-from { opacity: 0; transform: translateY(-8px); }
.detail-slide-leave-to { opacity: 0; transform: translateY(-8px); }
</style>

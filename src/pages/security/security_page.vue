<script setup lang="ts">
import { ref } from 'vue'

// 脱敏规则开关状态
const rules = ref([
  { name: 'IP 地址脱敏', before: '192.168.1.100', after: '192.168.*.**', enabled: true },
  { name: '文件路径脱敏', before: '/home/liyufeng/research/', after: '/home/****/research/', enabled: true },
  { name: 'Token/密钥过滤', before: '自动识别并遮蔽 API Key、密码', after: '********', enabled: true },
  { name: 'SSH 地址脱敏', before: 'robot@192.168.1.100', after: 'robot@192.168.*.**', enabled: true },
])

// 清除数据确认弹窗
const showConfirm = ref(false)
</script>

<template>
  <div class="p-6 space-y-6 overflow-y-auto h-full">
    <!-- 顶部安全状态总览 -->
    <div class="bg-surface-1 rounded-xl border border-surface-3 p-6 gradient-border">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <div class="w-14 h-14 rounded-2xl bg-emerald-500/15 flex items-center justify-center">
            <svg class="w-7 h-7 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <div>
            <div class="text-xl font-semibold text-gray-100">安全状态：良好</div>
            <div class="text-sm text-gray-400 mt-0.5">所有安全策略运行正常</div>
          </div>
        </div>
        <div class="flex items-center gap-8">
          <div class="text-center">
            <div class="text-lg font-bold text-emerald-400">本地模式</div>
            <div class="text-[11px] text-gray-500 mt-0.5">数据未离开设备</div>
          </div>
          <div class="w-px h-10 bg-surface-3" />
          <div class="text-center">
            <div class="text-lg font-bold text-accent">已脱敏 42 条</div>
            <div class="text-[11px] text-gray-500 mt-0.5">敏感记录已处理</div>
          </div>
          <div class="w-px h-10 bg-surface-3" />
          <div class="text-center">
            <div class="text-lg font-bold text-purple-400">30 天自动清理</div>
            <div class="text-[11px] text-gray-500 mt-0.5">数据保留策略</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 数据脱敏规则 -->
    <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
      <div class="text-sm font-medium mb-4 text-gray-300">数据脱敏规则</div>
      <div class="space-y-3">
        <div v-for="(rule, i) in rules" :key="i" class="flex items-center gap-4 bg-surface-2 rounded-lg px-4 py-3">
          <div class="w-36 text-sm text-gray-200 shrink-0">{{ rule.name }}</div>
          <div class="flex-1 text-xs font-mono text-gray-400 truncate">
            <span class="text-gray-500">{{ rule.before }}</span>
            <span class="mx-2 text-gray-600">-></span>
            <span class="text-emerald-400/70">{{ rule.after }}</span>
          </div>
          <button
            class="relative w-10 h-5 rounded-full transition-colors shrink-0"
            :class="rule.enabled ? 'bg-emerald-500/40' : 'bg-surface-3'"
            @click="rule.enabled = !rule.enabled"
          >
            <div
              class="absolute top-0.5 w-4 h-4 rounded-full transition-all"
              :class="rule.enabled ? 'left-5.5 bg-emerald-400' : 'left-0.5 bg-gray-500'"
            />
          </button>
        </div>
      </div>
    </div>

    <!-- 数据敏感度分类 -->
    <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
      <div class="text-sm font-medium mb-4 text-gray-300">数据敏感度分类</div>
      <div class="grid grid-cols-3 gap-4">
        <!-- 低敏感 -->
        <div class="bg-surface-2 rounded-lg p-4 space-y-3">
          <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full bg-emerald-400" />
            <span class="text-sm font-medium text-emerald-400">低敏感</span>
            <span class="text-xs text-gray-500 ml-auto">60%</span>
          </div>
          <div class="h-2 bg-surface-3 rounded-full overflow-hidden">
            <div class="h-full bg-emerald-500/60 rounded-full" style="width: 60%" />
          </div>
          <div class="text-xs text-gray-500 space-y-1">
            <div>文件打开</div>
            <div>目录切换</div>
            <div>环境检测</div>
          </div>
        </div>
        <!-- 中敏感 -->
        <div class="bg-surface-2 rounded-lg p-4 space-y-3">
          <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full bg-yellow-400" />
            <span class="text-sm font-medium text-yellow-400">中敏感</span>
            <span class="text-xs text-gray-500 ml-auto">35%</span>
          </div>
          <div class="h-2 bg-surface-3 rounded-full overflow-hidden">
            <div class="h-full bg-yellow-500/60 rounded-full" style="width: 35%" />
          </div>
          <div class="text-xs text-gray-500 space-y-1">
            <div>命令执行</div>
            <div>Git 操作</div>
            <div>代码编辑</div>
          </div>
        </div>
        <!-- 高敏感 -->
        <div class="bg-surface-2 rounded-lg p-4 space-y-3">
          <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full bg-red-400" />
            <span class="text-sm font-medium text-red-400">高敏感</span>
            <span class="text-xs text-gray-500 ml-auto">5%</span>
          </div>
          <div class="h-2 bg-surface-3 rounded-full overflow-hidden">
            <div class="h-full bg-red-500/60 rounded-full" style="width: 5%" />
          </div>
          <div class="text-xs text-gray-500 space-y-1">
            <div>含密码/token 的命令</div>
            <div>SSH 连接</div>
            <div>API 调用</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 本地优先架构 -->
    <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
      <div class="text-sm font-medium mb-4 text-gray-300">本地优先架构</div>
      <div class="grid grid-cols-3 gap-4">
        <div class="bg-surface-2 rounded-lg p-4">
          <div class="w-10 h-10 rounded-xl bg-accent/15 flex items-center justify-center mb-3">
            <svg class="w-5 h-5 text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="2" width="20" height="8" rx="2" />
              <rect x="2" y="14" width="20" height="8" rx="2" />
              <line x1="6" y1="6" x2="6.01" y2="6" />
              <line x1="6" y1="18" x2="6.01" y2="18" />
            </svg>
          </div>
          <div class="text-sm font-medium text-gray-200">数据本地存储</div>
          <div class="text-xs text-gray-500 mt-1">所有开发行为数据存储在用户设备上，不经过云端</div>
        </div>
        <div class="bg-surface-2 rounded-lg p-4">
          <div class="w-10 h-10 rounded-xl bg-purple-500/15 flex items-center justify-center mb-3">
            <svg class="w-5 h-5 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          </div>
          <div class="text-sm font-medium text-gray-200">端到端加密</div>
          <div class="text-xs text-gray-500 mt-1">即使同步到云端，数据也使用 AES-256 加密</div>
        </div>
        <div class="bg-surface-2 rounded-lg p-4">
          <div class="w-10 h-10 rounded-xl bg-emerald-500/15 flex items-center justify-center mb-3">
            <svg class="w-5 h-5 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </div>
          <div class="text-sm font-medium text-gray-200">最小化采集</div>
          <div class="text-xs text-gray-500 mt-1">只记录行为元数据，不记录文件内容和代码</div>
        </div>
      </div>
    </div>

    <!-- 数据保留策略 -->
    <div class="bg-surface-1 rounded-xl border border-surface-3 p-5">
      <div class="text-sm font-medium mb-4 text-gray-300">数据保留策略</div>
      <div class="space-y-3">
        <div class="flex items-center gap-4 bg-surface-2 rounded-lg px-4 py-3">
          <div class="w-2 h-2 rounded-full bg-yellow-400" />
          <div class="text-sm text-gray-200 w-28">原始事件</div>
          <div class="text-xs text-gray-500">30 天后自动清理</div>
        </div>
        <div class="flex items-center gap-4 bg-surface-2 rounded-lg px-4 py-3">
          <div class="w-2 h-2 rounded-full bg-emerald-400" />
          <div class="text-sm text-gray-200 w-28">行为模式</div>
          <div class="text-xs text-gray-500">永久保留（已脱敏）</div>
        </div>
        <div class="flex items-center gap-4 bg-surface-2 rounded-lg px-4 py-3">
          <div class="w-2 h-2 rounded-full bg-accent" />
          <div class="text-sm text-gray-200 w-28">技能数据</div>
          <div class="text-xs text-gray-500">永久保留</div>
        </div>
        <div class="flex items-center gap-4 bg-surface-2 rounded-lg px-4 py-3">
          <div class="w-2 h-2 rounded-full bg-gray-500" />
          <div class="text-sm text-gray-200 w-28">用户操作</div>
          <div class="text-xs text-gray-500">用户可随时一键清除所有数据</div>
        </div>
      </div>
      <div class="mt-5">
        <button
          class="px-5 py-2.5 text-sm bg-red-500/15 text-red-400 rounded-lg border border-red-500/25 hover:bg-red-500/25 transition-colors"
          @click="showConfirm = true"
        >
          清除所有数据
        </button>
      </div>
    </div>
  </div>

  <!-- 清除确认弹窗 -->
  <Teleport to="body">
    <div v-if="showConfirm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60" @click.self="showConfirm = false">
      <div class="bg-surface-1 rounded-xl border border-surface-3 p-6 w-96 space-y-4">
        <div class="text-base font-semibold text-gray-100">确认清除所有数据？</div>
        <div class="text-sm text-gray-400">此操作将永久删除所有本地存储的开发行为数据，且无法恢复。</div>
        <div class="flex justify-end gap-3">
          <button class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors" @click="showConfirm = false">取消</button>
          <button class="px-4 py-2 text-sm bg-red-500/20 text-red-400 rounded-lg border border-red-500/30 hover:bg-red-500/30 transition-colors" @click="showConfirm = false">确认清除</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

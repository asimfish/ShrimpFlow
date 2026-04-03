<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { useSkillsStore } from '@/stores/skills'
import type {
  LearningPlan,
  Skill,
  SkillDiscoveryReport,
  SkillRecommendation,
  SkillWorkflow,
  SkillWorkflowItem,
} from '@/types'
import {
  generateLearningPlanApi,
  getMinedWorkflowsApi,
  getSkillRecommendationsApi,
  getSkillDiscoveryApi,
  getSkillWorkflowsApi,
  recommendationFeedbackApi,
  summarizeWorkflowsApi,
  updateWorkflowStatusApi,
  postImplicitEventApi,
} from '@/http_api/skills'
import SkillGraph from './skill_graph.vue'
import SkillDetailPanel from './skill_detail_panel.vue'

const skillsStore = useSkillsStore()
const selectedSkill = ref<Skill | null>(null)
const learningGoal = ref('')
const planning = ref(false)
const planError = ref('')
const learningPlan = ref<LearningPlan | null>(null)

// 当前面板 tab
const activeTab = ref<'detail' | 'workflow' | 'recommend'>('detail')

// workflow 数据
const workflows = ref<SkillWorkflow[]>([])
const workflowLoading = ref(false)
const workflowLoaded = ref(false)

// 推荐数据
const recommendations = ref<SkillRecommendation[]>([])
const recommendLoading = ref(false)
const recommendLoaded = ref(false)

// 推荐 tab：持久化挖掘的 workflow
const minedWorkflows = ref<SkillWorkflowItem[]>([])
const discoveryReport = ref<SkillDiscoveryReport | null>(null)

const confidenceColor = (v: number) => {
  if (v >= 0.8) return 'text-emerald-400'
  if (v >= 0.6) return 'text-amber-400'
  return 'text-gray-400'
}

// Workflow tab 增强
const workflowFilter = ref<'all' | 'draft' | 'confirmed' | 'archived'>('all')
const summarizing = ref(false)
const expandedWorkflow = ref<number | null>(null)

const filteredMinedWorkflows = () => {
  if (!minedWorkflows.value.length) return []
  if (workflowFilter.value === 'all') return minedWorkflows.value
  return minedWorkflows.value.filter(wf => wf.status === workflowFilter.value)
}

const handleSummarize = async () => {
  summarizing.value = true
  const res = await summarizeWorkflowsApi()
  summarizing.value = false
  if (res.data) {
    const result = await getMinedWorkflowsApi()
    if (result.data) minedWorkflows.value = [...result.data].sort((a, b) => b.frequency - a.frequency)
  }
}

const handleWorkflowStatus = async (id: number, status: 'confirmed' | 'archived') => {
  await updateWorkflowStatusApi(id, status)
  const wf = minedWorkflows.value.find(w => w.id === id)
  if (wf) wf.status = status
}

const toggleWorkflowExpand = (id: number) => {
  expandedWorkflow.value = expandedWorkflow.value === id ? null : id
}

const recommendTypeLabel: Record<string, string> = {
  advanced: '进阶',
  gap: '缺口',
  related: '关联',
  workflow_co: '共现',
}
const recommendTypeColor: Record<string, string> = {
  advanced: 'bg-openclaw/10 text-openclaw',
  gap: 'bg-red-500/10 text-red-400',
  related: 'bg-sky-500/10 text-sky-400',
  workflow_co: 'bg-violet-500/10 text-violet-400',
}

const selectSkill = (skill: Skill) => {
  selectedSkill.value = skill
  activeTab.value = 'detail'
  postImplicitEventApi(skill.name, 'click').catch(() => {})
}

const closeDetail = () => {
  selectedSkill.value = null
}

const switchTab = async (tab: 'detail' | 'workflow' | 'recommend') => {
  activeTab.value = tab
  if (tab === 'workflow' && !workflowLoaded.value) {
    workflowLoading.value = true
    const [res, minedRes] = await Promise.all([getSkillWorkflowsApi(), getMinedWorkflowsApi()])
    workflowLoading.value = false
    if (res.data) workflows.value = res.data
    if (minedRes.data) minedWorkflows.value = [...minedRes.data].sort((a, b) => b.frequency - a.frequency)
    workflowLoaded.value = true
  }
  if (tab === 'recommend' && !recommendLoaded.value) {
    recommendLoading.value = true
    const [recRes, minedRes, discRes] = await Promise.all([
      getSkillRecommendationsApi(),
      getMinedWorkflowsApi(),
      getSkillDiscoveryApi(),
    ])
    recommendLoading.value = false
    if (recRes.data) {
      recommendations.value = recRes.data
    }
    if (minedRes.data) {
      minedWorkflows.value = [...minedRes.data].sort((a, b) => b.frequency - a.frequency)
    }
    if (discRes.data) {
      discoveryReport.value = discRes.data
    }
    recommendLoaded.value = true
  }
}

onMounted(() => {
  void skillsStore.ensureLoaded()
})

const feedbackSent = ref<Set<string>>(new Set())

const sendRecFeedback = async (name: string, action: 'useful' | 'dismiss') => {
  feedbackSent.value.add(`${name}:${action}`)
  await recommendationFeedbackApi(name, action)
  if (action === 'dismiss') {
    recommendations.value = recommendations.value.filter(r => r.name !== name)
  }
}

const generatePlan = async () => {
  if (!learningGoal.value.trim()) return
  planning.value = true
  planError.value = ''
  const res = await generateLearningPlanApi(learningGoal.value.trim())
  planning.value = false
  if (res.data) {
    learningPlan.value = res.data
  } else {
    planError.value = res.error ?? '学习计划生成失败'
  }
}
</script>

<template>
  <div class="flex h-full">
    <div class="flex-1 flex flex-col overflow-hidden">
      <div class="p-6 pb-3">
        <h1 class="text-2xl font-semibold">技能图谱</h1>
        <p class="text-sm text-gray-400 mt-1">OpenClaw 追踪的开发者技能图</p>
      </div>
      <SkillGraph :skills="skillsStore.skills" @select="selectSkill" />
    </div>
    <div class="w-[28rem] shrink-0 border-l border-surface-3 bg-surface-1 flex flex-col">
      <!-- 顶部 tab 切换 -->
      <div class="flex border-b border-surface-3 shrink-0">
        <button
          v-for="tab in ([{ key: 'detail', label: '技能 / 计划' }, { key: 'workflow', label: 'Workflow' }, { key: 'recommend', label: '推荐发现' }] as const)"
          :key="tab.key"
          class="flex-1 py-3 text-xs font-medium transition-colors"
          :class="activeTab === tab.key ? 'text-openclaw border-b-2 border-openclaw' : 'text-gray-500 hover:text-gray-300'"
          @click="switchTab(tab.key)"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- 技能详情 / 学习计划 tab -->
      <template v-if="activeTab === 'detail'">
        <div class="p-4 border-b border-surface-3 space-y-3 shrink-0">
          <div>
            <div class="text-sm font-semibold text-gray-200">AI 学习计划</div>
            <div class="text-xs text-gray-500 mt-1">输入你的目标，系统会结合技能图谱和知识库给出下一步提升建议</div>
          </div>
          <textarea
            v-model="learningGoal"
            rows="3"
            placeholder="例如：我想在 2 个月内提升具身智能方向的实验设计、代码实现和论文复现能力"
            class="w-full bg-surface-2 border border-surface-3 rounded-xl px-3 py-2 text-sm text-gray-200 outline-none focus:border-openclaw resize-none"
          />
          <div class="flex items-center justify-between gap-3">
            <div v-if="planError" class="text-[11px] text-red-400">{{ planError }}</div>
            <button
              class="px-3 py-2 rounded-lg text-xs font-medium ml-auto"
              :class="planning ? 'bg-surface-3 text-gray-500' : 'bg-openclaw/15 text-openclaw hover:bg-openclaw/25'"
              :disabled="planning"
              @click="generatePlan"
            >
              {{ planning ? '生成中...' : '生成学习计划' }}
            </button>
          </div>
        </div>

        <div class="flex-1 min-h-0 overflow-y-auto">
          <div v-if="learningPlan" class="p-4 space-y-4">
            <div class="bg-surface-2 rounded-xl p-4 border border-openclaw/15">
              <div class="text-xs text-openclaw mb-2">目标</div>
              <div class="text-sm text-gray-100">{{ learningPlan.goal }}</div>
              <div class="text-xs text-gray-400 mt-3 leading-relaxed">{{ learningPlan.summary }}</div>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div class="bg-surface-2 rounded-xl p-3">
                <div class="text-[11px] text-emerald-300 mb-2">已有优势</div>
                <div class="space-y-1">
                  <div v-for="item in learningPlan.strengths" :key="item" class="text-[11px] text-gray-300 leading-relaxed">{{ item }}</div>
                </div>
              </div>
              <div class="bg-surface-2 rounded-xl p-3">
                <div class="text-[11px] text-amber-300 mb-2">重点方向</div>
                <div class="flex flex-wrap gap-1.5">
                  <span v-for="item in learningPlan.focus_areas" :key="item" class="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400">{{ item }}</span>
                </div>
              </div>
            </div>
            <div v-for="phase in learningPlan.phases" :key="phase.title" class="bg-surface-2 rounded-xl p-4">
              <div class="text-sm font-medium text-gray-100">{{ phase.title }}</div>
              <div class="text-[11px] text-gray-500 mt-1">{{ phase.objective }}</div>
              <div class="mt-3 space-y-2">
                <div v-for="action in phase.actions" :key="action" class="flex items-start gap-2 text-xs text-gray-300">
                  <span class="mt-1 w-1.5 h-1.5 rounded-full bg-openclaw shrink-0" />
                  <span>{{ action }}</span>
                </div>
              </div>
            </div>
            <div class="bg-surface-2 rounded-xl p-4">
              <div class="text-[11px] text-cyan-300 mb-2">额外建议</div>
              <div class="space-y-2">
                <div v-for="item in learningPlan.recommendations" :key="item" class="text-xs text-gray-300 leading-relaxed">{{ item }}</div>
              </div>
            </div>
          </div>
          <div v-else class="p-4">
            <SkillDetailPanel :skill="selectedSkill" :embedded="true" @close="closeDetail" />
          </div>
        </div>
      </template>

      <!-- Workflow 分析 tab -->
      <template v-else-if="activeTab === 'workflow'">
        <div class="flex-1 min-h-0 overflow-y-auto">
          <div v-if="workflowLoading" class="flex items-center justify-center h-32 text-gray-500 text-sm">加载中...</div>
          <div v-else class="p-4 space-y-4">
            <!-- 顶部操作栏 -->
            <div class="flex items-center justify-between gap-2">
              <div class="flex items-center gap-1.5">
                <button
                  v-for="f in (['all', 'draft', 'confirmed', 'archived'] as const)"
                  :key="f"
                  class="px-2 py-1 rounded text-[10px] transition-colors"
                  :class="workflowFilter === f ? 'bg-openclaw/15 text-openclaw' : 'bg-surface-3 text-gray-500 hover:text-gray-300'"
                  @click="workflowFilter = f"
                >{{ { all: '全部', draft: '待确认', confirmed: '已确认', archived: '已归档' }[f] }}</button>
              </div>
              <button
                class="px-3 py-1.5 rounded-lg text-[11px] font-medium transition-colors"
                :class="summarizing ? 'bg-surface-3 text-gray-500' : 'bg-openclaw/15 text-openclaw hover:bg-openclaw/25'"
                :disabled="summarizing"
                @click="handleSummarize"
              >{{ summarizing ? 'AI 提炼中...' : 'AI 提炼' }}</button>
            </div>

            <!-- 实时统计 workflow -->
            <div v-if="workflows.length > 0" class="space-y-3">
              <div class="text-xs text-gray-500">实时统计 · {{ workflows.length }} 条序列</div>
              <div v-for="wf in workflows" :key="wf.name" class="bg-surface-2 rounded-xl p-4 space-y-2">
                <div class="flex flex-wrap items-center gap-1">
                  <template v-for="(step, idx) in wf.sequence" :key="step">
                    <span class="text-[11px] px-2 py-0.5 rounded-full bg-openclaw/10 text-openclaw font-mono">{{ step }}</span>
                    <span v-if="idx < wf.sequence.length - 1" class="text-gray-600 text-[10px]">→</span>
                  </template>
                </div>
                <div class="flex items-center gap-4 text-[11px]">
                  <span class="text-gray-400">出现 <span class="text-gray-200 font-medium">{{ wf.count }}</span> 次</span>
                  <span class="text-gray-400">成功率 <span :class="wf.success_rate >= 0.8 ? 'text-emerald-400' : wf.success_rate >= 0.5 ? 'text-amber-400' : 'text-red-400'" class="font-medium">{{ Math.round(wf.success_rate * 100) }}%</span></span>
                </div>
              </div>
            </div>

            <!-- 持久化 mined workflows -->
            <div class="space-y-3 pt-3 border-t border-surface-3">
              <div class="text-xs font-semibold text-gray-200 tracking-wide">Skill Workflow 库</div>
              <div v-if="filteredMinedWorkflows().length === 0" class="text-sm text-gray-500 py-4 text-center">
                {{ workflowFilter === 'all' ? '暂无数据，点击「AI 提炼」生成' : '该分类暂无 workflow' }}
              </div>
              <div
                v-for="wf in filteredMinedWorkflows()"
                :key="wf.id"
                class="bg-surface-2 rounded-xl p-4 space-y-2 cursor-pointer hover:bg-surface-2/80 transition-colors"
                @click="toggleWorkflowExpand(wf.id)"
              >
                <div class="flex items-start justify-between gap-2">
                  <div>
                    <div class="text-sm font-medium text-gray-100">{{ wf.name }}</div>
                    <div v-if="wf.description" class="text-[11px] text-gray-400 mt-0.5">{{ wf.description }}</div>
                    <div v-else class="text-[11px] text-gray-600 mt-0.5 italic">待 AI 提炼</div>
                  </div>
                  <span
                    class="text-[10px] px-2 py-0.5 rounded-full shrink-0"
                    :class="{
                      'bg-amber-500/10 text-amber-400': wf.status === 'draft' || !wf.status,
                      'bg-emerald-500/10 text-emerald-400': wf.status === 'confirmed',
                      'bg-gray-500/10 text-gray-500': wf.status === 'archived',
                    }"
                  >{{ { draft: '待确认', confirmed: '已确认', archived: '已归档' }[wf.status || 'draft'] }}</span>
                </div>

                <!-- 序列 -->
                <div class="flex flex-wrap items-center gap-1">
                  <template v-for="(step, idx) in wf.skill_sequence" :key="`${wf.id}-${idx}-${step}`">
                    <span class="text-[11px] px-2 py-0.5 rounded-full bg-openclaw/10 text-openclaw font-mono">{{ step }}</span>
                    <span v-if="idx < wf.skill_sequence.length - 1" class="text-gray-600 text-[10px]">→</span>
                  </template>
                </div>

                <!-- 统计 + 标签 -->
                <div class="flex items-center gap-4 text-[11px]">
                  <span class="text-gray-400">频次 <span class="text-gray-200 font-medium">{{ wf.frequency }}</span></span>
                  <span class="text-gray-400">成功率 <span :class="wf.success_rate >= 0.8 ? 'text-emerald-400' : wf.success_rate >= 0.5 ? 'text-amber-400' : 'text-red-400'" class="font-medium">{{ Math.round(wf.success_rate * 100) }}%</span></span>
                  <span class="text-gray-600 text-[10px]">{{ wf.source }}</span>
                </div>

                <!-- 展开详情 -->
                <template v-if="expandedWorkflow === wf.id">
                  <div v-if="wf.trigger" class="bg-surface-1 rounded-lg p-3 mt-2">
                    <div class="text-[10px] text-gray-500 mb-1">触发条件</div>
                    <div class="text-xs text-gray-300">{{ wf.trigger }}</div>
                  </div>
                  <div v-if="wf.steps && wf.steps.length" class="bg-surface-1 rounded-lg p-3">
                    <div class="text-[10px] text-gray-500 mb-2">步骤流程</div>
                    <div class="space-y-1.5">
                      <div v-for="(s, si) in wf.steps" :key="si" class="flex items-start gap-2 text-xs">
                        <span class="w-5 h-5 rounded-full bg-openclaw/10 text-openclaw flex items-center justify-center text-[10px] shrink-0 mt-0.5">{{ si + 1 }}</span>
                        <div>
                          <span class="text-gray-200">{{ s.action }}</span>
                          <span v-if="s.tool" class="text-gray-500 ml-1">[{{ s.tool }}]</span>
                          <div v-if="s.checkpoint" class="text-[10px] text-gray-600 mt-0.5">✓ {{ s.checkpoint }}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div v-if="wf.context_tags?.length" class="flex flex-wrap gap-1">
                    <span v-for="tag in wf.context_tags" :key="tag" class="text-[10px] px-2 py-0.5 rounded-full bg-surface-3 text-gray-400">{{ tag }}</span>
                  </div>
                  <div v-if="wf.status !== 'confirmed' && wf.status !== 'archived'" class="flex items-center gap-2 pt-1">
                    <button
                      class="px-3 py-1 rounded-lg text-[11px] bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-colors"
                      @click.stop="handleWorkflowStatus(wf.id, 'confirmed')"
                    >确认采纳</button>
                    <button
                      class="px-3 py-1 rounded-lg text-[11px] bg-surface-3 text-gray-400 hover:text-gray-300 transition-colors"
                      @click.stop="handleWorkflowStatus(wf.id, 'archived')"
                    >归档</button>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- 推荐发现 tab -->
      <template v-else-if="activeTab === 'recommend'">
        <div class="flex-1 min-h-0 overflow-y-auto">
          <div v-if="recommendLoading" class="flex items-center justify-center h-32 text-gray-500 text-sm">加载中...</div>
          <div v-else class="p-4 space-y-6">
            <!-- Skill Discovery -->
            <div v-if="discoveryReport && (discoveryReport.new_skills.length || discoveryReport.related_skills.length || discoveryReport.upgrade_skills.length)" class="space-y-2 pb-2 border-b border-surface-3">
              <div class="text-xs font-semibold text-gray-200 tracking-wide">技能发现</div>
              <div v-for="ns in discoveryReport.new_skills.slice(0, 5)" :key="ns.name" class="text-[11px] text-emerald-400">+ {{ ns.name }} <span class="text-gray-500">{{ ns.category }}</span></div>
              <div v-for="rs in discoveryReport.related_skills.slice(0, 3)" :key="rs.external.name" class="text-[11px] text-sky-400">~ {{ rs.external.name }} → {{ rs.local_skill.name }}</div>
              <div v-for="us in discoveryReport.upgrade_skills.slice(0, 3)" :key="us.external.name" class="text-[11px] text-amber-400">↑ {{ us.external.name }} (升级 {{ us.base_skill.name }})</div>
            </div>

            <div class="space-y-3">
              <div v-if="recommendations.length > 0" class="text-xs text-gray-500">
                系统根据你的技能图谱和行为模式推荐 {{ recommendations.length }} 项
              </div>
              <div v-else class="text-sm text-gray-500">暂无推荐</div>
              <div
                v-for="rec in recommendations"
                :key="rec.name"
                class="bg-surface-2 rounded-xl p-4 space-y-2"
              >
                <div class="flex items-start justify-between gap-2">
                  <div class="text-sm font-medium text-gray-100">{{ rec.name }}</div>
                  <span class="text-[10px] px-2 py-0.5 rounded-full shrink-0" :class="recommendTypeColor[rec.type] ?? 'bg-surface-3 text-gray-400'">{{ recommendTypeLabel[rec.type] ?? rec.type }}</span>
                </div>
                <div class="text-[11px] text-gray-400 leading-relaxed">{{ rec.reason }}</div>
                <div class="flex items-center justify-between text-[11px]">
                  <div class="flex items-center gap-3">
                    <span class="text-gray-500">置信度 <span :class="confidenceColor(rec.confidence)" class="font-medium">{{ Math.round(rec.confidence * 100) }}%</span></span>
                    <span class="text-gray-600">{{ rec.category }}</span>
                  </div>
                  <div class="flex items-center gap-1.5">
                    <button
                      class="px-2 py-0.5 rounded text-[10px] transition-colors"
                      :class="feedbackSent.has(`${rec.name}:useful`) ? 'bg-emerald-500/20 text-emerald-400' : 'bg-surface-3 text-gray-400 hover:text-emerald-400 hover:bg-emerald-500/10'"
                      :disabled="feedbackSent.has(`${rec.name}:useful`)"
                      @click.stop="sendRecFeedback(rec.name, 'useful')"
                    >有用</button>
                    <button
                      class="px-2 py-0.5 rounded text-[10px] bg-surface-3 text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      @click.stop="sendRecFeedback(rec.name, 'dismiss')"
                    >忽略</button>
                  </div>
                </div>
              </div>
            </div>

            <div class="space-y-3 pt-2 border-t border-surface-3">
              <div class="text-xs font-semibold text-gray-200 tracking-wide">Skill Workflow 挖掘</div>
              <div v-if="minedWorkflows.length === 0" class="text-sm text-gray-500">暂无挖掘数据</div>
              <div
                v-for="wf in minedWorkflows"
                :key="wf.id"
                class="bg-surface-2 rounded-xl p-4 space-y-2"
              >
                <div class="text-sm font-medium text-gray-100">{{ wf.name }}</div>
                <div class="flex flex-wrap items-center gap-1">
                  <template v-for="(step, idx) in wf.skill_sequence" :key="`${wf.id}-${idx}-${step}`">
                    <span class="text-[11px] px-2 py-0.5 rounded-full bg-openclaw/10 text-openclaw font-mono">{{ step }}</span>
                    <span v-if="idx < wf.skill_sequence.length - 1" class="text-gray-600 text-[10px]">→</span>
                  </template>
                </div>
                <div class="flex items-center gap-4 text-[11px]">
                  <span class="text-gray-400">频次 <span class="text-gray-200 font-medium">{{ wf.frequency }}</span></span>
                  <span class="text-gray-400">
                    成功率
                    <span
                      :class="wf.success_rate >= 0.8 ? 'text-emerald-400' : wf.success_rate >= 0.5 ? 'text-amber-400' : 'text-red-400'"
                      class="font-medium"
                    >{{ Math.round(wf.success_rate * 100) }}%</span>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

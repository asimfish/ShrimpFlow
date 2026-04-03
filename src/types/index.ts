// ShrimpFlow 类型定义

// 统一事件格式
export type EventSource = 'terminal' | 'git' | 'openclaw' | 'claude_code' | 'codex' | 'cursor' | 'vscode' | 'env'

export type DevEvent = {
  id: number
  timestamp: number
  source: EventSource
  action: string
  directory: string
  project: string
  branch: string
  exit_code: number
  duration_ms: number
  semantic: string
  tags: string[]
  openclaw_session_id?: number
}

// 每日摘要
export type DailySummary = {
  date: string
  event_count: number
  top_projects: { name: string; count: number }[]
  top_commands: { cmd: string; count: number }[]
  ai_summary: string
  openclaw_sessions: number
}

// 技能
export type Skill = {
  id: number
  name: string
  category: string
  level: number
  total_uses: number
  cot_uses: number
  manual_uses: number
  auto_uses: number
  combo_patterns: string[]
  workflow_roles: string[]
  last_used: number
  first_seen: number
}

export type SkillWorkflow = {
  name: string
  sequence: string[]
  count: number
  success_rate: number
  description: string
}

// GET /skills/workflows/mined（持久化行；JSON 字段为 sequence，前端统一为 skill_sequence）
export type SkillWorkflowItem = {
  id: number
  name: string
  skill_sequence: string[]
  frequency: number
  success_rate: number
  source: string
  created_at: number
  updated_at?: number
  description?: string | null
  trigger?: string | null
  steps?: WorkflowStepDetail[]
  status?: 'draft' | 'confirmed' | 'archived'
  context_tags?: string[]
  confirmed_by?: string | null
}

export type WorkflowStepDetail = {
  action: string
  tool?: string
  checkpoint?: string
}

export type SkillRecommendation = {
  name: string
  category: string
  reason: string
  type: 'advanced' | 'gap' | 'related' | 'workflow_co' | 'usage_based'
  confidence: number
  explanation_chain?: string[]
}

// GET /skills/discovery（本地 skill 库扫描 + 与 DB 比对）
export type SkillDiscoveryExternalEntry = {
  name: string
  description: string
  category: string
  path: string
  paths: string[]
  source_library: string
}

export type SkillDiscoveryStats = {
  total_scanned: number
  new_found: number
  related_found: number
  upgrade_found: number
  library_count: number
}

export type SkillDiscoveryRelatedItem = {
  external: {
    name: string
    category: string
    description: string
    source_library: string
  }
  local_skill: {
    id: number
    name: string
    category: string
    level: number
  }
  score: number
}

export type SkillDiscoveryUpgradeItem = {
  external: {
    name: string
    description: string
    category: string
    source_library: string
  }
  base_skill: {
    id: number
    name: string
    category: string
    level: number
  }
}

export type SkillDiscoveryReport = {
  libraries_scanned: string[]
  stats: SkillDiscoveryStats
  external_skills: SkillDiscoveryExternalEntry[]
  new_skills: SkillDiscoveryExternalEntry[]
  related_skills: SkillDiscoveryRelatedItem[]
  upgrade_skills: SkillDiscoveryUpgradeItem[]
}

export type LearningPlanPhase = {
  title: string
  objective: string
  actions: string[]
}

export type LearningPlan = {
  goal: string
  summary: string
  strengths: string[]
  focus_areas: string[]
  phases: LearningPlanPhase[]
  recommendations: string[]
}

// 技能类别
export type SkillCategory = 'language' | 'devops' | 'vcs' | 'framework' | 'tool' | 'package-manager' | 'editor' | 'network' | 'openclaw'

// 统计概览
export type StatsOverview = {
  total_events: number
  total_days: number
  total_projects: number
  total_skills: number
  total_openclaw_sessions: number
  total_claude_sessions: number
  total_codex_sessions?: number
  total_git_commits: number
  most_active_project: string
  streak_days: number
}

export type ClawProfile = {
  id: number
  schema: string
  name: string
  display: string
  description: string | null
  author: string | null
  tags: string[]
  license: string | null
  forked_from: string | null
  trust: string | null
  injection: { mode?: string; budget?: number } | null
  is_active: boolean
  created_at: number | null
  updated_at: number | null
  pattern_count: number
  workflow_count: number
}

// 时间线缩放级别
export type TimelineZoom = 'hour' | 'day' | 'week' | 'month'

// 项目信息
export type ProjectInfo = {
  name: string
  event_count: number
  last_active: number
  languages: string[]
}

// OpenClaw 对话消息
export type OpenClawMessage = {
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

// OpenClaw 完整会话
export type OpenClawSession = {
  id: number
  title: string
  display_title?: string
  category: 'paper' | 'debug' | 'review' | 'experiment' | 'architecture' | 'learning'
  messages: OpenClawMessage[]
  project: string
  tags: string[]
  origin?: 'openclaw' | 'claude_code' | 'codex' | 'cursor' | 'vscode' | 'unknown'
  origin_label?: string
  index_label?: string
  display_summary?: string
  profile_id?: number | null
  injected_pattern_slugs?: string[]
  analysis_summary?: string | null
  analysis_status?: string | null
  created_at: number
  summary: string
}

// OpenClaw 知识库文档
export type OpenClawDocument = {
  id: number
  title: string
  display_title?: string
  type:
    | 'daily_task'
    | 'paper_note'
    | 'experiment_log'
    | 'meeting_note'
    | 'daily_summary'
    | 'ai_tools_daily'
    | 'ai_tools_weekly'
    | 'ai_tools_index'
    | 'github_daily'
    | 'media_daily'
    | 'misc'
  content: string
  tags: string[]
  origin?: 'openclaw' | 'claude_code' | 'codex' | 'cursor' | 'vscode' | 'unknown'
  origin_label?: string
  index_label?: string
  preview_excerpt?: string
  profile_id?: number | null
  created_at: number
  source_session_id: number
}

// 模式演化快照
export type PatternSnapshot = {
  date: string
  confidence: number
  event_description: string
}

// 模式子规则
export type PatternRule = {
  id: number
  name: string
  description: string
  trigger: string
  action: string
  example: string
}

// 模式执行日志
export type PatternExecution = {
  id: number
  pattern_id: number
  timestamp: number
  trigger_event: string
  action_taken: string
  result: 'success' | 'skipped' | 'modified'
}

export type PatternTrigger = {
  when: string
  globs?: string[]
  event?: string
  context?: string[]
}

export type PatternInsight = {
  context: string
  insight: string
  confidence: number
}

// 行为模式
export type BehaviorPattern = {
  id: number
  profile_id?: number | null
  name: string
  category: 'git' | 'coding' | 'review' | 'devops' | 'collaboration'
  description: string
  confidence: number
  evidence_count: number
  learned_from: string
  rule: string
  created_at: number
  evolution: PatternSnapshot[]
  status: 'learning' | 'confirmed' | 'exportable'
  rules: PatternRule[]
  executions: PatternExecution[]
  applicable_scenarios: string[]
  // ClawProfile v1
  slug: string | null
  trigger: string | PatternTrigger | null
  body: string | null
  source: 'auto' | 'manual' | 'imported' | 'forked' | null
  confidence_level: 'low' | 'medium' | 'high' | 'very_high' | null
  learned_from_data: PatternInsight[] | null
  // Phase 1: 记忆衰减与强化
  heat_score: number
  last_accessed_at: number
  access_count: number
  lifecycle_state: 'active' | 'warm' | 'cool' | 'compressed' | 'archived'
}

// 记忆健康评分
export type MemoryHealth = {
  score: number
  grade: 'A' | 'B' | 'C' | 'D' | 'F'
  total: number
  confirmed: number
  avg_heat: number
  by_lifecycle: Record<string, number>
  breakdown: {
    heat: number
    vitality: number
    evidence: number
    freshness: number
    confirmation: number
  }
  issues: string[]
}

// Workflow 步骤
export type WorkflowStep = {
  pattern?: string
  inline?: string
  when?: string
  gate?: string
  parallel?: WorkflowStep[]
}

// 团队 Workflow
export type TeamWorkflow = {
  id: number
  profile_id?: number | null
  name: string
  description: string
  patterns: number[]
  target_team: string
  status: 'draft' | 'active' | 'distributed'
  created_at: number
  steps: WorkflowStep[]
}

// 社区分享用户
export type SharedProfile = {
  id: number
  username: string
  avatar: string
  title: string
  bio: string
  followers: number
  patterns_count: number
}

// 社区分享模式包
export type SharedPatternPack = {
  id: number
  author: SharedProfile
  name: string
  description: string
  category: string
  patterns: BehaviorPattern[]
  downloads: number
  stars: number
  tags: string[]
  created_at: number
}

export type SharedClawProfile = {
  id: number
  author: SharedProfile
  name: string
  display: string
  description: string
  profile: ClawProfile
  patterns: BehaviorPattern[]
  workflows: TeamWorkflow[]
  downloads: number
  stars: number
  tags: string[]
  created_at: number
}

// 定时采集配置
export type ScheduleConfig = {
  enabled: boolean
  interval_hours: number
  running: boolean
}

export type AIProviderStrategy = 'auto' | 'heuristic_only' | string

export type AIProviderOption = {
  key: string
  label: string
  configured?: boolean
  family?: string
  models?: { id: string; name: string }[]
  default_model?: string | null
  active?: boolean
  preferred?: boolean
}

export type AISettings = {
  selected_provider: string
  default_model: string
  selector_model: string
  providers: AIProviderOption[]
  models: { id: string; name: string }[]
}

export type OpenClawInvocationLog = {
  id: number
  session_id: number
  profile_id: number | null
  provider: string | null
  model: string | null
  selector_type: string | null
  selected_pattern_slugs: string[]
  prompt_excerpt: string | null
  response_summary: string | null
  status: string | null
  created_at: number | null
}

// Brain 层: EventAtom
export type EventAtom = {
  id: number
  event_id: number
  timestamp: number
  source: string
  project: string
  intent: string
  tool: string
  artifact: string
  outcome: string
  error_signature: string
  command_family: string
  task_hint: string
}

// Brain 层: Episode
export type Episode = {
  id: number
  project: string
  start_ts: number
  end_ts: number
  duration_seconds: number
  task_label: string
  task_category: string
  event_count: number
  atom_count: number
  tool_sequence: string[]
  intent_sequence: string[]
  outcome: string
  features: Record<string, unknown>
  session_ids: number[]
  created_at: number
  atoms?: EventAtom[]
}

export type EpisodeStats = {
  total_episodes: number
  total_atoms: number
  by_category: Record<string, number>
  by_outcome: Record<string, number>
}

// Feature Graph
export type ArchetypeSummary = {
  archetype: string
  count: number
  top_projects: string[]
  top_categories: string[]
}

export type FeatureGraphStats = {
  total_nodes: number
  total_edges: number
  archetype_distribution: Record<string, number>
  edge_type_distribution: Record<string, number>
}

// Evidence Ledger
export type EvidenceEntry = {
  id: number
  pattern_id: number
  episode_id: number | null
  evidence_type: 'support' | 'conflict' | 'novelty' | 'utility'
  description: string
  confidence_before: number
  confidence_after: number
  delta: number
  source: string
  created_at: number
}

export type EvidenceLedgerStats = {
  total: number
  by_type: Record<string, number>
  avg_delta: number
}

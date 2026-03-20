// ShrimpFlow 类型定义

// 统一事件格式
export type EventSource = 'terminal' | 'git' | 'openclaw' | 'claude_code' | 'env'

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
  last_used: number
  first_seen: number
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
  category: 'paper' | 'debug' | 'review' | 'experiment' | 'architecture' | 'learning'
  messages: OpenClawMessage[]
  project: string
  tags: string[]
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

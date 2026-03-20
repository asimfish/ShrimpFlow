import { post } from './client'

// 采集 shell 历史
export const collectShellHistoryApi = () => post<{ count: number }>('/collect/shell-history', {})

// 采集 Claude Code 历史
export const collectClaudeCodeApi = () => post<{ count: number }>('/collect/claude-code', {})

// 采集 Codex 历史
export const collectCodexApi = () => post<{ count: number }>('/collect/codex', {})

// 采集 Clawd 历史
export const collectClawdApi = () => post<{ count: number }>('/collect/clawd', {})

// 采集 Git 历史
export const collectGitHistoryApi = () => post<{ count: number }>('/collect/git-history', {})

// 采集全部
export const collectAllApi = () => post<{ count: number }>('/collect/all', {})

// 采集全部 + 分析（挖掘模式 + 生成今日摘要）
export const collectAllAndAnalyzeApi = () =>
  post<{ results: any[]; mining_count: number; digest_updated: boolean }>('/collect/all-and-analyze', {})

// 行为模式挖掘算法
// 从事件序列中自动发现频繁模式和时间规律

import type { DevEvent } from '@/types'

export type MinedPattern = {
  id: string
  name: string
  description: string
  type: 'sequence' | 'time' | 'correlation'
  confidence: number
  occurrences: number
  examples: string[]
}

// 频繁序列挖掘：找出经常连续出现的 action 组合
export const mineFrequentSequences = (events: DevEvent[], windowSize = 3, minSupport = 3): MinedPattern[] => {
  const sorted = [...events].sort((a, b) => a.timestamp - b.timestamp)
  const seqCounts = new Map<string, { count: number; examples: string[] }>()

  for (let i = 0; i < sorted.length - windowSize + 1; i++) {
    const window = sorted.slice(i, i + windowSize)
    // 同一天内的事件才算序列
    const daySpan = (window[window.length - 1].timestamp - window[0].timestamp) / 3600
    if (daySpan > 4) continue

    const key = window.map(e => simplifyAction(e)).join(' -> ')
    if (!seqCounts.has(key)) seqCounts.set(key, { count: 0, examples: [] })
    const entry = seqCounts.get(key)!
    entry.count++
    if (entry.examples.length < 2) {
      entry.examples.push(window.map(e => e.action.slice(0, 50)).join(' | '))
    }
  }

  return [...seqCounts.entries()]
    .filter(([_, v]) => v.count >= minSupport)
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 8)
    .map(([key, v], i) => ({
      id: `seq-${i}`,
      name: key,
      description: `该序列在 ${v.count} 个时间窗口中出现`,
      type: 'sequence' as const,
      confidence: Math.min(95, 50 + v.count * 3),
      occurrences: v.count,
      examples: v.examples,
    }))
}

// 时间模式检测：发现用户的时间规律
export const mineTimePatterns = (events: DevEvent[]): MinedPattern[] => {
  const patterns: MinedPattern[] = []
  const hourCounts = new Array(24).fill(0)
  const dayOfWeekCounts = new Array(7).fill(0)
  const sourceByHour: Record<string, number[]> = {}

  for (const e of events) {
    const d = new Date(e.timestamp * 1000)
    hourCounts[d.getHours()]++
    dayOfWeekCounts[d.getDay()]++
    if (!sourceByHour[e.source]) sourceByHour[e.source] = new Array(24).fill(0)
    sourceByHour[e.source][d.getHours()]++
  }

  // 高峰时段检测
  const maxHour = hourCounts.indexOf(Math.max(...hourCounts))
  const totalEvents = events.length
  const peakRatio = hourCounts[maxHour] / totalEvents
  patterns.push({
    id: 'time-peak',
    name: `高峰时段: ${maxHour}:00-${maxHour + 1}:00`,
    description: `${(peakRatio * 100).toFixed(1)}% 的事件集中在此时段`,
    type: 'time',
    confidence: Math.min(95, Math.round(peakRatio * 500)),
    occurrences: hourCounts[maxHour],
    examples: [`${maxHour}:00 时段产生 ${hourCounts[maxHour]} 个事件`],
  })

  // 工作日 vs 周末
  const weekdayAvg = dayOfWeekCounts.slice(1, 6).reduce((a, b) => a + b, 0) / 5
  const weekendAvg = (dayOfWeekCounts[0] + dayOfWeekCounts[6]) / 2
  if (weekdayAvg > weekendAvg * 1.5) {
    patterns.push({
      id: 'time-weekday',
      name: '工作日集中型',
      description: `工作日平均 ${Math.round(weekdayAvg)} 事件，周末 ${Math.round(weekendAvg)} 事件`,
      type: 'time',
      confidence: Math.min(90, Math.round((weekdayAvg / (weekendAvg + 1)) * 30)),
      occurrences: Math.round(weekdayAvg * 5),
      examples: ['工作日活跃度显著高于周末'],
    })
  }

  // 来源时间偏好
  for (const [source, hours] of Object.entries(sourceByHour)) {
    const peakH = hours.indexOf(Math.max(...hours))
    const sourceTotal = hours.reduce((a, b) => a + b, 0)
    if (sourceTotal < 10) continue
    const ratio = hours[peakH] / sourceTotal
    if (ratio > 0.15) {
      patterns.push({
        id: `time-source-${source}`,
        name: `${source} 偏好 ${peakH}:00`,
        description: `${source} 事件 ${(ratio * 100).toFixed(0)}% 集中在 ${peakH}:00`,
        type: 'time',
        confidence: Math.min(85, Math.round(ratio * 300)),
        occurrences: hours[peakH],
        examples: [`${peakH}:00 产生 ${hours[peakH]} 个 ${source} 事件`],
      })
    }
  }

  return patterns
}

// 关联模式检测：发现事件之间的关联
export const mineCorrelations = (events: DevEvent[]): MinedPattern[] => {
  const patterns: MinedPattern[] = []
  const sorted = [...events].sort((a, b) => a.timestamp - b.timestamp)

  // 检测 "git commit 前总是 pytest" 这类模式
  const pairCounts = new Map<string, number>()
  const sourceCounts = new Map<string, number>()

  for (let i = 0; i < sorted.length - 1; i++) {
    const curr = simplifyAction(sorted[i])
    const next = simplifyAction(sorted[i + 1])
    // 10 分钟内的连续事件
    if (sorted[i + 1].timestamp - sorted[i].timestamp > 600) continue
    const pair = `${curr} -> ${next}`
    pairCounts.set(pair, (pairCounts.get(pair) ?? 0) + 1)
    sourceCounts.set(curr, (sourceCounts.get(curr) ?? 0) + 1)
  }

  for (const [pair, count] of pairCounts) {
    if (count < 4) continue
    const [first] = pair.split(' -> ')
    const total = sourceCounts.get(first) ?? 1
    const confidence = Math.round(count / total * 100)
    if (confidence < 30) continue
    patterns.push({
      id: `corr-${patterns.length}`,
      name: pair,
      description: `${count} 次观察到此关联，置信度 ${confidence}%`,
      type: 'correlation',
      confidence: Math.min(95, confidence),
      occurrences: count,
      examples: [`${first} 之后 ${confidence}% 概率出现后续动作`],
    })
  }

  return patterns.sort((a, b) => b.confidence - a.confidence).slice(0, 6)
}

// 简化 action 为类别标签
const simplifyAction = (e: DevEvent): string => {
  if (e.source === 'openclaw') return 'openclaw-chat'
  if (e.source === 'env') return 'env-check'
  if (e.source === 'git') {
    if (e.action.includes('commit')) return 'git-commit'
    if (e.action.includes('merge')) return 'git-merge'
    return 'git-op'
  }
  if (e.source === 'claude_code') return 'claude-edit'
  if (e.source === 'codex') return 'codex-edit'
  // terminal
  if (e.action.includes('python')) return 'python-run'
  if (e.action.includes('pytest') || e.action.includes('test')) return 'test-run'
  if (e.action.includes('colcon') || e.action.includes('build')) return 'build'
  if (e.action.includes('ssh')) return 'ssh-connect'
  if (e.action.includes('nvidia-smi') || e.action.includes('tensorboard')) return 'monitor'
  if (e.action.includes('pip') || e.action.includes('conda')) return 'pkg-install'
  return 'terminal-cmd'
}

// 运行所有挖掘算法
export const mineAllPatterns = (events: DevEvent[]): MinedPattern[] => [
  ...mineFrequentSequences(events),
  ...mineTimePatterns(events),
  ...mineCorrelations(events),
]

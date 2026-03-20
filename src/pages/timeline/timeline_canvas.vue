<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'

import type { DevEvent } from '@/types'
import * as d3 from '@/libs/d3'

const props = defineProps<{
  events: DevEvent[]
}>()

const emit = defineEmits<{
  select: [event: DevEvent]
}>()

const svgRef = ref<SVGSVGElement>()
const tooltip = ref({ visible: false, x: 0, y: 0, event: null as DevEvent | null })

const sourceColor: Record<string, string> = {
  openclaw: '#f59e0b',
  terminal: '#38bdf8',
  git: '#34d399',
  claude_code: '#a78bfa',
  env: '#f87171',
}

const sourceLabel: Record<string, string> = {
  openclaw: 'OpenClaw',
  terminal: '终端',
  git: 'Git',
  claude_code: 'Claude',
  env: '环境',
}

// 不同来源用不同形状的 path
const sourceShape: Record<string, (x: number, y: number, r: number) => string> = {
  openclaw: (x, y, r) => {
    // 六边形
    const a = r * 1.2
    return Array.from({ length: 6 }, (_, i) => {
      const angle = (Math.PI / 3) * i - Math.PI / 2
      return `${x + a * Math.cos(angle)},${y + a * Math.sin(angle)}`
    }).join(' ')
  },
  terminal: (x, y, r) => `${x},${y - r} ${x + r},${y} ${x},${y + r} ${x - r},${y}`, // 菱形
  git: (x, y, r) => `${x - r},${y - r} ${x + r},${y - r} ${x + r},${y + r} ${x - r},${y + r}`, // 方形
  claude_code: (x, y, r) => `${x},${y - r * 1.2} ${x + r},${y + r * 0.6} ${x - r},${y + r * 0.6}`, // 三角
  env: (x, y, r) => `${x},${y - r} ${x + r},${y} ${x},${y + r} ${x - r},${y}`, // 菱形
}

// 给每个事件预计算一个稳定的 y 偏移，避免 redraw 时跳动
const yOffsetMap = new Map<number, number>()
const getYOffset = (id: number) => {
  if (!yOffsetMap.has(id)) yOffsetMap.set(id, (Math.random() - 0.5) * 0.6)
  return yOffsetMap.get(id)!
}

const drawTimeline = () => {
  const svg = d3.select(svgRef.value!)
  svg.selectAll('*').remove()

  const container = svgRef.value!.parentElement!
  const width = container.clientWidth
  const height = container.clientHeight
  const margin = { top: 40, right: 30, bottom: 40, left: 90 }

  svg.attr('width', width).attr('height', height)

  const data = props.events
  if (data.length === 0) return

  // scales
  const timeExtent = d3.extent(data, d => d.timestamp) as [number, number]
  const xScale = d3.scaleTime()
    .domain([new Date(timeExtent[0] * 1000), new Date(timeExtent[1] * 1000)])
    .range([margin.left, width - margin.right])

  const sources = ['openclaw', 'terminal', 'git', 'claude_code', 'env']
  const yScale = d3.scaleBand<string>()
    .domain(sources)
    .range([margin.top, height - margin.bottom])
    .padding(0.3)

  // defs: clip path + 背景渐变
  const defs = svg.append('defs')
  defs.append('clipPath')
    .attr('id', 'chart-clip')
    .append('rect')
    .attr('x', margin.left)
    .attr('y', 0)
    .attr('width', width - margin.left - margin.right)
    .attr('height', height)
  const bgGrad = defs.append('linearGradient').attr('id', 'tl-bg').attr('x1', '0%').attr('y1', '0%').attr('x2', '0%').attr('y2', '100%')
  bgGrad.append('stop').attr('offset', '0%').attr('stop-color', '#0a0a0f')
  bgGrad.append('stop').attr('offset', '50%').attr('stop-color', '#12121a')
  bgGrad.append('stop').attr('offset', '100%').attr('stop-color', '#0a0a0f')
  svg.insert('rect', ':first-child').attr('width', width).attr('height', height).attr('fill', 'url(#tl-bg)')

  // 固定的 Y 轴标签（不随 zoom 移动）
  const sourceCounts: Record<string, number> = {}
  data.forEach(d => { sourceCounts[d.source] = (sourceCounts[d.source] ?? 0) + 1 })

  sources.forEach(s => {
    const y = yScale(s)! + yScale.bandwidth() / 2
    svg.append('text')
      .attr('x', 8)
      .attr('y', y - 6)
      .attr('fill', sourceColor[s])
      .attr('font-size', '11px')
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('dominant-baseline', 'middle')
      .text(sourceLabel[s])

    svg.append('text')
      .attr('x', 8)
      .attr('y', y + 8)
      .attr('fill', '#6b7280')
      .attr('font-size', '9px')
      .attr('dominant-baseline', 'middle')
      .text(`${sourceCounts[s] ?? 0} 个事件`)

    // 网格线
    svg.append('line')
      .attr('x1', margin.left)
      .attr('x2', width - margin.right)
      .attr('y1', y)
      .attr('y2', y)
      .attr('stroke', '#1a1a2e')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '4,4')
  })

  // 垂直网格线
  for (let i = 0; i < 8; i++) {
    const x = margin.left + (width - margin.left - margin.right) * i / 7
    svg.append('line')
      .attr('x1', x).attr('x2', x)
      .attr('y1', margin.top).attr('y2', height - margin.bottom)
      .attr('stroke', '#1a1a2e').attr('stroke-width', 1).attr('stroke-dasharray', '2,6')
  }

  // X 轴
  const xAxisG = svg.append('g')
    .attr('transform', `translate(0,${height - margin.bottom})`)

  const renderXAxis = (scale: any) => {
    xAxisG
      .call(d3.axisBottom(scale).ticks(8).tickFormat(d3.timeFormat('%m/%d %H:%M') as any))
      .call(g => g.selectAll('text').attr('fill', '#6b7280').attr('font-size', '9px'))
      .call(g => g.selectAll('line').attr('stroke', '#242438'))
      .call(g => g.select('.domain').attr('stroke', '#242438'))
  }
  renderXAxis(xScale)

  // 圆点组（clip 裁剪）
  const dotsG = svg.append('g').attr('clip-path', 'url(#chart-clip)')

  const calcCy = (d: DevEvent) => {
    const base = yScale(d.source)! + yScale.bandwidth() / 2
    return base + getYOffset(d.id) * yScale.bandwidth()
  }

  // 使用不同形状的 polygon
  const shapes = dotsG.selectAll('polygon')
    .data(data)
    .join('polygon')
    .attr('points', (d: DevEvent) => {
      const cx = xScale(new Date(d.timestamp * 1000))
      const cy = calcCy(d)
      return sourceShape[d.source](cx, cy, 0)
    })
    .attr('fill', (d: DevEvent) => sourceColor[d.source])
    .attr('opacity', (d: DevEvent) => d.source === 'openclaw' ? 0.9 : 0.7)
    .attr('cursor', 'pointer')
    .on('mouseenter', (event: MouseEvent, d: DevEvent) => {
      const r = d.source === 'openclaw' ? 8 : 6
      const cx = parseFloat(d3.select(event.currentTarget as Element).attr('data-cx'))
      const cy = parseFloat(d3.select(event.currentTarget as Element).attr('data-cy'))
      d3.select(event.currentTarget as Element).attr('points', sourceShape[d.source](cx, cy, r))
      tooltip.value = { visible: true, x: event.offsetX + 12, y: event.offsetY - 10, event: d }
    })
    .on('mouseleave', (event: MouseEvent, d: DevEvent) => {
      const r = d.source === 'openclaw' ? 5 : 3.5
      const cx = parseFloat(d3.select(event.currentTarget as Element).attr('data-cx'))
      const cy = parseFloat(d3.select(event.currentTarget as Element).attr('data-cy'))
      d3.select(event.currentTarget as Element).attr('points', sourceShape[d.source](cx, cy, r))
      tooltip.value = { ...tooltip.value, visible: false }
    })
    .on('click', (event: MouseEvent, d: DevEvent) => {
      event.stopPropagation()
      emit('select', d)
    })

  // 存储位置数据
  shapes.each(function(d: DevEvent) {
    const cx = xScale(new Date(d.timestamp * 1000))
    const cy = calcCy(d)
    d3.select(this).attr('data-cx', cx).attr('data-cy', cy)
  })

  // 分层入场动画 - 按来源分组波浪展开
  const sourceOrder = ['terminal', 'git', 'env', 'claude_code', 'openclaw']
  shapes.transition()
    .duration(600)
    .delay((d: DevEvent) => {
      const layerIdx = sourceOrder.indexOf(d.source)
      return layerIdx * 200 + Math.random() * 100
    })
    .attr('points', (d: DevEvent) => {
      const cx = xScale(new Date(d.timestamp * 1000))
      const cy = calcCy(d)
      const r = d.source === 'openclaw' ? 5 : 3.5
      return sourceShape[d.source](cx, cy, r)
    })

  // 同一 AI 会话的事件用虚线连接
  const openclawEvents = data.filter(d =>
    (d.source === 'openclaw' || d.source === 'claude_code') && d.openclaw_session_id
  )
  const sessionGroups = new Map<number, DevEvent[]>()
  openclawEvents.forEach(d => {
    const sid = d.openclaw_session_id!
    if (!sessionGroups.has(sid)) sessionGroups.set(sid, [])
    sessionGroups.get(sid)!.push(d)
  })
  sessionGroups.forEach(events => {
    if (events.length < 2) return
    const sorted = events.sort((a, b) => a.timestamp - b.timestamp)
    for (let i = 0; i < sorted.length - 1; i++) {
      const x1 = xScale(new Date(sorted[i].timestamp * 1000))
      const y1 = calcCy(sorted[i])
      const x2 = xScale(new Date(sorted[i + 1].timestamp * 1000))
      const y2 = calcCy(sorted[i + 1])
      dotsG.append('line')
        .attr('x1', x1).attr('y1', y1).attr('x2', x2).attr('y2', y2)
        .attr('stroke', sourceColor.openclaw).attr('stroke-width', 1)
        .attr('stroke-dasharray', '3,3').attr('opacity', 0)
        .transition().delay(1200).duration(600).attr('opacity', 0.3)
    }
  })

  // 底部时间密度条 - 按来源着色
  const densityHeight = 20
  const densityY = height - margin.bottom + 20
  const bucketCount = 48
  const bucketsBySource: Record<string, number[]> = {}
  sources.forEach(s => { bucketsBySource[s] = new Array(bucketCount).fill(0) })
  const tRange = timeExtent[1] - timeExtent[0]
  data.forEach(d => {
    const idx = Math.min(Math.floor((d.timestamp - timeExtent[0]) / tRange * bucketCount), bucketCount - 1)
    bucketsBySource[d.source][idx]++
  })
  const totalBuckets = new Array(bucketCount).fill(0)
  data.forEach(d => {
    const idx = Math.min(Math.floor((d.timestamp - timeExtent[0]) / tRange * bucketCount), bucketCount - 1)
    totalBuckets[idx]++
  })
  const maxBucket = Math.max(...totalBuckets, 1)
  const barW = (width - margin.left - margin.right) / bucketCount
  // 堆叠柱状图
  totalBuckets.forEach((_total, i) => {
    let yOffset = 0
    for (const s of sources) {
      const count = bucketsBySource[s][i]
      if (count === 0) continue
      const h = densityHeight * (count / maxBucket)
      svg.append('rect')
        .attr('x', margin.left + i * barW)
        .attr('y', densityY + densityHeight - yOffset - h)
        .attr('width', barW - 1)
        .attr('height', h)
        .attr('fill', sourceColor[s])
        .attr('opacity', 0.3)
      yOffset += h
    }
  })

  // zoom（只缩放 X 轴）
  let currentTransform = d3.zoomIdentity
  const zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.5, 50])
    .on('zoom', (event) => {
      currentTransform = event.transform
      const newX = currentTransform.rescaleX(xScale)
      renderXAxis(newX)
      shapes.each(function(d: DevEvent) {
        const cx = newX(new Date(d.timestamp * 1000))
        const cy = calcCy(d)
        const r = d.source === 'openclaw' ? 5 : 3.5
        d3.select(this)
          .attr('points', sourceShape[d.source](cx, cy, r))
          .attr('data-cx', cx)
          .attr('data-cy', cy)
      })
    })

  svg.call(zoomBehavior as any)
}

onMounted(drawTimeline)
watch(() => props.events, drawTimeline)
</script>

<template>
  <div class="flex-1 relative overflow-hidden">
    <svg ref="svgRef" class="w-full h-full" />
    <div
      v-show="tooltip.visible"
      class="absolute pointer-events-none bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 shadow-xl z-50 max-w-xs"
      :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
    >
      <template v-if="tooltip.event">
        <div class="flex items-center gap-1.5 mb-1">
          <div class="w-2 h-2 rounded-full" :style="{ background: sourceColor[tooltip.event.source] }" />
          <span class="text-xs font-medium" :style="{ color: sourceColor[tooltip.event.source] }">
            {{ sourceLabel[tooltip.event.source] }}
          </span>
        </div>
        <div class="text-xs font-mono text-gray-300 truncate">{{ tooltip.event.action }}</div>
        <div class="text-[10px] text-gray-400 mt-1">{{ tooltip.event.semantic }}</div>
        <div class="text-[10px] text-gray-500 mt-1">
          {{ tooltip.event.project }} · {{ tooltip.event.duration_ms }}ms · exit:{{ tooltip.event.exit_code }}
        </div>
        <div v-if="tooltip.event.tags.length" class="flex flex-wrap gap-1 mt-1">
          <span v-for="tag in tooltip.event.tags.slice(0, 3)" :key="tag" class="text-[9px] px-1 py-0.5 rounded bg-surface-3 text-gray-500">{{ tag }}</span>
        </div>
      </template>
    </div>
  </div>
</template>

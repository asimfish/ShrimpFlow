<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

import type { Skill } from '@/types'
import * as d3 from '@/libs/d3'

const props = defineProps<{
  skills: Skill[]
}>()

const emit = defineEmits<{
  select: [skill: Skill]
}>()

const svgRef = ref<SVGSVGElement>()
const skillTooltip = ref({ visible: false, x: 0, y: 0, skill: null as Skill | null })
let animFrameId: number

const categoryColor: Record<string, string> = {
  openclaw: '#f59e0b',
  language: '#38bdf8',
  devops: '#f87171',
  vcs: '#34d399',
  framework: '#a78bfa',
  tool: '#64748b',
  'package-manager': '#94a3b8',
  editor: '#94a3b8',
  network: '#94a3b8',
}

const categoryLabel: Record<string, string> = {
  openclaw: 'AI', language: '语言', devops: '运维', vcs: '版本控制',
  framework: '框架', tool: '工具', 'package-manager': '包管理', editor: '编辑器', network: '网络',
}

type GraphNode = {
  id: string
  label: string
  type: 'center' | 'category' | 'skill'
  category: string
  radius: number
  color: string
  skill?: Skill
  x?: number
  y?: number
  fx?: number | null
  fy?: number | null
}

type GraphLink = {
  source: string | GraphNode
  target: string | GraphNode
}

const drawGraph = () => {
  const svg = d3.select(svgRef.value!)
  svg.selectAll('*').remove()

  const container = svgRef.value!.parentElement!
  const width = container.clientWidth
  const height = container.clientHeight

  svg.attr('width', width).attr('height', height)

  // 径向渐变背景
  const defs = svg.append('defs')
  const radialGrad = defs.append('radialGradient').attr('id', 'bg-glow')
  radialGrad.append('stop').attr('offset', '0%').attr('stop-color', '#7c5cfc').attr('stop-opacity', 0.06)
  radialGrad.append('stop').attr('offset', '50%').attr('stop-color', '#7c5cfc').attr('stop-opacity', 0.02)
  radialGrad.append('stop').attr('offset', '100%').attr('stop-color', 'transparent').attr('stop-opacity', 0)
  svg.append('circle').attr('cx', width / 2).attr('cy', height / 2).attr('r', Math.min(width, height) * 0.4).attr('fill', 'url(#bg-glow)')

  // 构建节点
  const nodes: GraphNode[] = []
  const links: GraphLink[] = []

  // 中心节点
  nodes.push({
    id: 'center',
    label: '李宇峰',
    type: 'center',
    category: '',
    radius: 28,
    color: '#7c5cfc',
  })

  // 类别节点
  const categories = [...new Set(props.skills.map(s => s.category))]
  for (const cat of categories) {
    nodes.push({
      id: `cat-${cat}`,
      label: cat,
      type: 'category',
      category: cat,
      radius: 14,
      color: categoryColor[cat] ?? '#94a3b8',
    })
    links.push({ source: 'center', target: `cat-${cat}` })
  }

  // 技能节点
  const now = Math.floor(Date.now() / 1000)
  for (const skill of props.skills) {
    const radius = 6 + Math.sqrt(skill.total_uses) * 0.5

    nodes.push({
      id: `skill-${skill.id}`,
      label: skill.name,
      type: 'skill',
      category: skill.category,
      radius: Math.min(radius, 20),
      color: categoryColor[skill.category] ?? '#94a3b8',
      skill,
    })
    links.push({ source: `cat-${skill.category}`, target: `skill-${skill.id}` })
  }

  // 缩放 - 过滤掉节点上的事件
  const g = svg.append('g')
  const zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.3, 3])
    .filter((event: any) => {
      const tag = (event.target as Element).tagName
      if (tag === 'circle' || tag === 'text') return false
      return (!event.ctrlKey || event.type === 'wheel') && !event.button
    })
    .on('zoom', (event) => {
      g.attr('transform', event.transform)
    })
  svg.call(zoomBehavior as any)

  // 力模拟
  const simulation = d3.forceSimulation(nodes as any)
    .force('link', d3.forceLink(links as any).id((d: any) => d.id).distance((d: any) => {
      const src = d.source as GraphNode
      if (src.type === 'center') return 160
      return 80
    }))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius((d: any) => d.radius + 15))

  // 连线（带动画）
  const link = g.append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke', '#ffffff')
    .attr('stroke-opacity', (d: any) => {
      const tgt = d.target as GraphNode
      if (tgt.skill) {
        const recentDays = (now - tgt.skill.last_used) / 86400
        return recentDays < 7 ? 0.2 : 0.08
      }
      return 0.12
    })
    .attr('stroke-width', 1.5)
    .attr('stroke-dasharray', '6,4')
    .style('animation', 'dash-flow 2s linear infinite')

  // 粒子流动效果
  const particles = g.append('g').attr('class', 'particles')
  const particleData = links.map((l, i) => ({ link: l, id: i, offset: Math.random() }))

  const particleCircles = particles.selectAll('circle')
    .data(particleData)
    .join('circle')
    .attr('r', 1.5)
    .attr('fill', (d: any) => {
      const target = typeof d.link.target === 'string' ? nodes.find(n => n.id === d.link.target) : d.link.target as GraphNode
      return target?.color ?? '#fff'
    })
    .attr('opacity', 0.6)

  // 节点组
  let dragStartX = 0
  let dragStartY = 0
  const node = g.append('g')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .attr('cursor', 'pointer')
    .call(d3.drag<SVGGElement, GraphNode>()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x
        d.fy = d.y
        dragStartX = event.x
        dragStartY = event.y
      })
      .on('drag', (event, d) => {
        d.fx = event.x
        d.fy = event.y
      })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0)
        d.fx = null
        d.fy = null
        // 如果几乎没移动，视为 click
        const dx = event.x - dragStartX
        const dy = event.y - dragStartY
        if (Math.abs(dx) < 3 && Math.abs(dy) < 3 && d.skill) {
          emit('select', d.skill)
        }
      }) as any
    )

  // 节点圆
  node.append('circle')
    .attr('r', d => d.radius)
    .attr('fill', d => d.color)
    .attr('opacity', d => {
      if (d.type !== 'skill') return 0.9
      const recentDays = d.skill ? (now - d.skill.last_used) / 86400 : 30
      return recentDays < 7 ? 0.9 : recentDays < 14 ? 0.6 : 0.35
    })
    .attr('stroke', d => d.type === 'center' ? '#a78bfa' : 'none')
    .attr('stroke-width', d => d.type === 'center' ? 2 : 0)

  // 中心节点呼吸光环
  node.filter(d => d.type === 'center')
    .insert('circle', ':first-child')
    .attr('r', 36)
    .attr('fill', 'none')
    .attr('stroke', '#7c5cfc')
    .attr('stroke-opacity', 0.2)
    .attr('stroke-width', 2)
    .attr('class', 'center-pulse')

  // 发光效果 (openclaw 节点)
  node.filter(d => d.category === 'openclaw' && d.type === 'skill')
    .append('circle')
    .attr('r', d => d.radius + 4)
    .attr('fill', 'none')
    .attr('stroke', '#f59e0b')
    .attr('stroke-opacity', 0.3)
    .attr('stroke-width', 2)

  // 标签
  node.append('text')
    .text(d => d.type === 'category' ? (categoryLabel[d.category] ?? d.label) : d.label)
    .attr('text-anchor', 'middle')
    .attr('dy', d => d.radius + 14)
    .attr('fill', '#9ca3af')
    .attr('font-size', d => d.type === 'center' ? '12px' : d.type === 'category' ? '10px' : '9px')
    .attr('font-family', 'JetBrains Mono, monospace')

  // 技能等级标签（在节点内部）
  node.filter(d => d.type === 'skill')
    .append('text')
    .text(d => `${d.skill?.level}`)
    .attr('text-anchor', 'middle')
    .attr('dy', 3)
    .attr('fill', '#fff')
    .attr('font-size', '8px')
    .attr('font-weight', '600')
    .attr('pointer-events', 'none')

  // 中心标签特殊处理
  node.filter(d => d.type === 'center')
    .select('text')
    .attr('fill', '#e5e7eb')
    .attr('font-weight', '600')

  // 点击事件
  node.on('click', (_event: MouseEvent, d: GraphNode) => {
    if (d.skill) emit('select', d.skill)
  })
    .on('mouseenter', (event: MouseEvent, d: GraphNode) => {
      if (d.skill) {
        skillTooltip.value = { visible: true, x: event.offsetX + 15, y: event.offsetY - 10, skill: d.skill }
      }
    })
    .on('mouseleave', () => {
      skillTooltip.value = { ...skillTooltip.value, visible: false }
    })

  // 力模拟 tick
  simulation.on('tick', () => {
    link
      .attr('x1', (d: any) => d.source.x)
      .attr('y1', (d: any) => d.source.y)
      .attr('x2', (d: any) => d.target.x)
      .attr('y2', (d: any) => d.target.y)

    node.attr('transform', (d: any) => `translate(${d.x},${d.y})`)
  })

  // 持续粒子动画
  const animateParticles = () => {
    const time = Date.now() / 2000
    particleCircles.attr('cx', (d: any) => {
      const src = d.link.source as GraphNode
      const tgt = d.link.target as GraphNode
      const t = ((time + d.offset) % 1)
      return (src.x ?? 0) + ((tgt.x ?? 0) - (src.x ?? 0)) * t
    }).attr('cy', (d: any) => {
      const src = d.link.source as GraphNode
      const tgt = d.link.target as GraphNode
      const t = ((time + d.offset) % 1)
      return (src.y ?? 0) + ((tgt.y ?? 0) - (src.y ?? 0)) * t
    })
    animFrameId = requestAnimationFrame(animateParticles)
  }
  animateParticles()
}

onMounted(drawGraph)
onUnmounted(() => {
  if (animFrameId) cancelAnimationFrame(animFrameId)
})
</script>

<template>
  <div class="flex-1 relative overflow-hidden bg-void">
    <svg ref="svgRef" class="w-full h-full" />
    <div
      v-show="skillTooltip.visible && skillTooltip.skill"
      class="absolute pointer-events-none bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 shadow-xl z-50"
      :style="{ left: skillTooltip.x + 'px', top: skillTooltip.y + 'px' }"
    >
      <template v-if="skillTooltip.skill">
        <div class="text-xs font-medium text-gray-200">{{ skillTooltip.skill.name }}</div>
        <div class="text-[10px] text-gray-400 mt-1">Lv.{{ skillTooltip.skill.level }} · {{ skillTooltip.skill.total_uses }} 次使用</div>
        <div class="h-1 bg-surface-3 rounded-full mt-1.5 w-24">
          <div class="h-full bg-accent rounded-full" :style="{ width: `${skillTooltip.skill.level}%` }" />
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
@keyframes dash-flow {
  to { stroke-dashoffset: -20; }
}
svg :deep(line) {
  animation: dash-flow 2s linear infinite;
}
@keyframes center-breathe {
  0%, 100% { stroke-opacity: 0.15; r: 36; }
  50% { stroke-opacity: 0.35; r: 40; }
}
svg :deep(.center-pulse) {
  animation: center-breathe 3s ease-in-out infinite;
}
</style>

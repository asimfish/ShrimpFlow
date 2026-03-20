// 模拟数据生成器 - 具身智能博士生的开发数据
import type { DevEvent, DailySummary, Skill, StatsOverview, BehaviorPattern, TeamWorkflow, OpenClawSession, OpenClawDocument, SharedProfile, SharedPatternPack } from '@/types'

const now = Math.floor(Date.now() / 1000)
const DAY = 86400
const HOUR = 3600

// 具身智能研究项目
const projects = ['embodied-nav', 'grasp-policy', 'ros2-workspace', 'paper-reproduce', 'sim2real-transfer']
const branches = ['main', 'feat/ppo-reward', 'fix/tf2-transform', 'dev', 'feat/habitat-env', 'exp/domain-rand']

const pickSource = () => {
  const r = Math.random()
  if (r < 0.35) return 'openclaw' as const
  if (r < 0.6) return 'terminal' as const
  if (r < 0.8) return 'git' as const
  if (r < 0.9) return 'claude_code' as const
  if (r < 0.97) return 'codex' as const
  return 'env' as const
}

const openclawActions = [
  { action: 'openclaw chat: "帮我分析 PointNav 论文的核心创新点"', semantic: '请求 OpenClaw 分析导航论文', tags: ['openclaw', 'paper'], session_id: 1 },
  { action: 'openclaw chat: "PPO 训练 reward 不收敛，帮我排查"', semantic: 'OpenClaw 协助调试 RL 训练', tags: ['openclaw', 'debug'], session_id: 2 },
  { action: 'openclaw skill: code-review on grasp_policy/model.py', semantic: 'OpenClaw 审查抓取策略代码', tags: ['openclaw', 'review'], session_id: 3 },
  { action: 'openclaw chat: "ROS2 tf2 坐标变换报错，帮我调试"', semantic: 'OpenClaw 调试 ROS2 坐标变换', tags: ['openclaw', 'debug'], session_id: 4 },
  { action: 'openclaw chat: "设计 sim2real domain randomization 方案"', semantic: 'OpenClaw 辅助设计仿真迁移方案', tags: ['openclaw', 'architecture'], session_id: 5 },
  { action: 'openclaw chat: "总结今天实验结果，写入知识库"', semantic: 'OpenClaw 生成实验总结', tags: ['openclaw', 'summary'], session_id: 6 },
  { action: 'openclaw skill: tdd-guide for nav_planner', semantic: 'OpenClaw TDD 引导导航规划器开发', tags: ['openclaw', 'tdd'], session_id: 7 },
  { action: 'openclaw chat: "对比 Habitat 和 iGibson 仿真环境的优劣"', semantic: 'OpenClaw 对比仿真环境', tags: ['openclaw', 'learning'], session_id: 8 },
  { action: 'openclaw chat: "帮我设计 Habitat 环境的 reward function"', semantic: 'OpenClaw 辅助设计奖励函数', tags: ['openclaw', 'architecture'], session_id: 9 },
  { action: 'openclaw chat: "分析 SAC 和 TD3 在连续控制任务上的差异"', semantic: 'OpenClaw 分析 RL 算法差异', tags: ['openclaw', 'paper'], session_id: 10 },
  { action: 'openclaw chat: "帮我写一个 ROS2 的 action server"', semantic: 'OpenClaw 辅助 ROS2 开发', tags: ['openclaw', 'architecture'], session_id: 11 },
  { action: 'openclaw skill: code-review on sim2real/visual_dr.py', semantic: 'OpenClaw 审查 sim2real 代码', tags: ['openclaw', 'review'], session_id: 12 },
  { action: 'openclaw chat: "整理本周实验数据，生成对比表格"', semantic: 'OpenClaw 整理实验数据', tags: ['openclaw', 'experiment'], session_id: 13 },
  { action: 'openclaw chat: "讨论 ViT 在视觉导航中的应用前景"', semantic: 'OpenClaw 讨论前沿技术', tags: ['openclaw', 'learning'], session_id: 14 },
  { action: 'openclaw chat: "帮我调试 CUDA out of memory 问题"', semantic: 'OpenClaw 调试 GPU 内存问题', tags: ['openclaw', 'debug'], session_id: 15 },
]

const terminalActions = [
  { action: 'python train.py --env HabitatNav-v2 --epochs 200 --lr 3e-4', semantic: '训练视觉导航 PPO 策略', tags: ['ml', 'training'] },
  { action: 'roslaunch manipulation_pkg grasp_demo.launch', semantic: '启动机械臂抓取演示', tags: ['ros', 'manipulation'] },
  { action: 'gazebo --verbose worlds/tabletop.world', semantic: '启动 Gazebo 桌面仿真环境', tags: ['simulation', 'gazebo'] },
  { action: 'colcon build --packages-select nav_planner', semantic: '编译 ROS2 导航规划包', tags: ['ros2', 'build'] },
  { action: 'tensorboard --logdir runs/ppo_nav_0318', semantic: '查看训练曲线', tags: ['ml', 'visualization'] },
  { action: 'ssh robot@192.168.1.100 "rostopic echo /joint_states"', semantic: '远程查看机器人关节状态', tags: ['robot', 'ssh'] },
  { action: 'pytest tests/test_policy.py -v', semantic: '运行策略网络单元测试', tags: ['test', 'python'] },
  { action: 'python eval.py --checkpoint best_model.pt --episodes 100', semantic: '评估最优模型性能', tags: ['ml', 'evaluation'] },
  { action: 'pip install habitat-sim==0.3.0', semantic: '安装 Habitat 仿真器', tags: ['dependency', 'python'] },
  { action: 'nvidia-smi', semantic: '检查 GPU 使用情况', tags: ['gpu', 'monitoring'] },
]

const gitActions = [
  { action: 'commit: feat: implement PPO reward shaping for navigation', semantic: '提交导航奖励塑形功能', tags: ['git', 'feature'] },
  { action: 'commit: fix: resolve tf2 lookup timeout in grasp pipeline', semantic: '修复抓取流水线坐标变换超时', tags: ['git', 'bugfix'] },
  { action: 'commit: refactor: extract point cloud preprocessing utils', semantic: '重构点云预处理工具', tags: ['git', 'refactor'] },
  { action: 'commit: docs: add experiment results for PPO vs SAC', semantic: '记录 PPO vs SAC 实验结果', tags: ['git', 'docs'] },
  { action: 'commit: feat: add domain randomization for sim2real', semantic: '添加域随机化仿真迁移', tags: ['git', 'feature'] },
  { action: 'merge: feat/ppo-reward into main', semantic: '合并 PPO 奖励分支', tags: ['git', 'merge'] },
  { action: 'commit: test: add unit tests for nav_planner', semantic: '添加导航规划器单元测试', tags: ['git', 'test'] },
]

const claudeCodeActions = [
  { action: 'claude: Edit src/models/ppo_agent.py', semantic: 'Claude Code 编辑 PPO 智能体', tags: ['claude', 'edit'] },
  { action: 'claude: Bash python -m pytest tests/ -v', semantic: 'Claude Code 运行测试套件', tags: ['claude', 'test'] },
  { action: 'claude: Grep "reward_function" src/', semantic: 'Claude Code 搜索奖励函数', tags: ['claude', 'search'] },
]

const codexActions = [
  { action: 'codex session: refine devtwin realtime collector', semantic: 'Codex 辅助完善实时采集链路', tags: ['codex', 'edit'] },
  { action: 'codex session: inspect clawprofile export/import path', semantic: 'Codex 审查 ClawProfile 导入导出', tags: ['codex', 'analysis'] },
  { action: 'codex session: patch openclaw runtime selector', semantic: 'Codex 调整 OpenClaw runtime', tags: ['codex', 'runtime'] },
]

type GeneratedEventData = Omit<DevEvent, 'id' | 'timestamp' | 'source'>

const generateEventData = (source: DevEvent['source']): GeneratedEventData => {
  const project = projects[Math.floor(Math.random() * projects.length)]
  const branch = branches[Math.floor(Math.random() * branches.length)]
  const base = { directory: `/home/liyufeng/research/${project}`, project, branch }

  switch (source) {
    case 'openclaw': {
      const d = openclawActions[Math.floor(Math.random() * openclawActions.length)]
      return { ...base, action: d.action, semantic: d.semantic, tags: d.tags, exit_code: 0, duration_ms: 2000 + Math.floor(Math.random() * 30000), openclaw_session_id: d.session_id }
    }
    case 'terminal': {
      const d = terminalActions[Math.floor(Math.random() * terminalActions.length)]
      const exit_code = Math.random() > 0.9 ? 1 : 0
      return { ...base, action: d.action, semantic: d.semantic, tags: d.tags, exit_code, duration_ms: 100 + Math.floor(Math.random() * 10000) }
    }
    case 'git': {
      const d = gitActions[Math.floor(Math.random() * gitActions.length)]
      return { ...base, action: d.action, semantic: d.semantic, tags: d.tags, exit_code: 0, duration_ms: 50 + Math.floor(Math.random() * 500) }
    }
    case 'claude_code': {
      const d = claudeCodeActions[Math.floor(Math.random() * claudeCodeActions.length)]
      return { ...base, action: d.action, semantic: d.semantic, tags: d.tags, exit_code: 0, duration_ms: 500 + Math.floor(Math.random() * 5000) }
    }
    case 'codex': {
      const d = codexActions[Math.floor(Math.random() * codexActions.length)]
      return { ...base, action: d.action, semantic: d.semantic, tags: d.tags, exit_code: 0, duration_ms: 500 + Math.floor(Math.random() * 5000) }
    }
    case 'env':
      return { ...base, action: 'env snapshot: CUDA 12.4 / PyTorch 2.3 / ROS2 Humble', semantic: '环境变更检测', tags: ['env'], exit_code: 0, duration_ms: 0 }
  }
}

const generateEvents = (): DevEvent[] => {
  const events: DevEvent[] = []
  let id = 1
  for (let day = 29; day >= 0; day--) {
    const baseTs = now - day * DAY
    const eventsPerDay = 20 + Math.floor(Math.random() * 40)
    for (let i = 0; i < eventsPerDay; i++) {
      const ts = baseTs + Math.floor(Math.random() * 12 * HOUR) + 8 * HOUR
      const source = pickSource()
      events.push({ id: id++, timestamp: ts, source, ...generateEventData(source) })
    }
  }
  return events.sort((a, b) => a.timestamp - b.timestamp)
}

export const mockEvents: DevEvent[] = generateEvents()

// 每日摘要
const generateDaySummary = (total: number, openclaw: number): string => {
  if (total === 0) return '今天没有研究活动。'
  const summaries = [
    `今天通过 OpenClaw 完成了 ${openclaw} 次 AI 辅助研究，总共产生 ${total} 个事件。主要集中在视觉导航策略训练和 ROS2 调试上。`,
    `高效的一天！与 OpenClaw 进行了 ${openclaw} 次交互，涵盖论文分析、RL 调参和仿真实验。共 ${total} 个事件。`,
    `今天重点使用 OpenClaw 进行 PPO 训练调试和代码审查，${openclaw} 次 AI 协作帮助解决了 reward shaping 问题。总事件 ${total} 个。`,
    `今天在 Habitat 仿真环境中完成了导航基线实验，OpenClaw 协助分析了 ${openclaw} 次实验结果。总事件 ${total} 个。`,
  ]
  return summaries[Math.floor(Math.random() * summaries.length)]
}

export const mockSummaries: DailySummary[] = Array.from({ length: 30 }, (_, i) => {
  const dayEvents = mockEvents.filter(e => {
    const dayStart = now - (29 - i) * DAY
    return e.timestamp >= dayStart && e.timestamp < dayStart + DAY
  })
  const date = new Date((now - (29 - i) * DAY) * 1000)
  const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  const projectCounts = new Map<string, number>()
  const cmdCounts = new Map<string, number>()
  let openclawCount = 0
  for (const e of dayEvents) {
    projectCounts.set(e.project, (projectCounts.get(e.project) ?? 0) + 1)
    if (e.source === 'terminal') {
      const cmd = e.action.split(' ')[0]
      cmdCounts.set(cmd, (cmdCounts.get(cmd) ?? 0) + 1)
    }
    if (e.source === 'openclaw') openclawCount++
  }
  return {
    date: dateStr,
    event_count: dayEvents.length,
    top_projects: [...projectCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5).map(([name, count]) => ({ name, count })),
    top_commands: [...cmdCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5).map(([cmd, count]) => ({ cmd, count })),
    ai_summary: generateDaySummary(dayEvents.length, openclawCount),
    openclaw_sessions: openclawCount,
  }
})

// 技能数据 - 具身智能研究者
export const mockSkills: Skill[] = [
  { id: 1, name: 'OpenClaw', category: 'openclaw', level: 85, total_uses: 420, last_used: now - 300, first_seen: now - 25 * DAY },
  { id: 2, name: 'Python', category: 'language', level: 82, total_uses: 380, last_used: now - 600, first_seen: now - 29 * DAY },
  { id: 3, name: 'PyTorch', category: 'framework', level: 78, total_uses: 310, last_used: now - 1200, first_seen: now - 28 * DAY },
  { id: 4, name: 'ROS2', category: 'framework', level: 72, total_uses: 260, last_used: now - 1800, first_seen: now - 27 * DAY },
  { id: 5, name: 'Git', category: 'vcs', level: 70, total_uses: 240, last_used: now - 900, first_seen: now - 29 * DAY },
  { id: 6, name: 'Gazebo', category: 'tool', level: 65, total_uses: 180, last_used: now - 2 * HOUR, first_seen: now - 25 * DAY },
  { id: 7, name: 'Habitat', category: 'tool', level: 60, total_uses: 150, last_used: now - 4 * HOUR, first_seen: now - 20 * DAY },
  { id: 8, name: 'Docker', category: 'devops', level: 55, total_uses: 95, last_used: now - DAY, first_seen: now - 20 * DAY },
  { id: 9, name: 'TensorBoard', category: 'tool', level: 52, total_uses: 88, last_used: now - 3 * HOUR, first_seen: now - 26 * DAY },
  { id: 10, name: 'Claude Code', category: 'openclaw', level: 58, total_uses: 140, last_used: now - 1200, first_seen: now - 20 * DAY },
  { id: 11, name: 'C++', category: 'language', level: 48, total_uses: 75, last_used: now - 2 * DAY, first_seen: now - 29 * DAY },
  { id: 12, name: 'CUDA', category: 'language', level: 42, total_uses: 55, last_used: now - 3 * DAY, first_seen: now - 22 * DAY },
  { id: 13, name: 'SSH', category: 'network', level: 45, total_uses: 60, last_used: now - 5 * HOUR, first_seen: now - 29 * DAY },
  { id: 14, name: 'NumPy', category: 'framework', level: 68, total_uses: 200, last_used: now - 2 * HOUR, first_seen: now - 29 * DAY },
  { id: 15, name: 'Open3D', category: 'framework', level: 35, total_uses: 30, last_used: now - 5 * DAY, first_seen: now - 15 * DAY },
]

// 统计概览
export const mockStats: StatsOverview = {
  total_events: mockEvents.length,
  total_days: 30,
  total_projects: 5,
  total_skills: mockSkills.length,
  total_openclaw_sessions: mockEvents.filter(e => e.source === 'openclaw').length,
  total_claude_sessions: mockEvents.filter(e => e.source === 'claude_code').length,
  total_git_commits: mockEvents.filter(e => e.source === 'git').length,
  most_active_project: 'embodied-nav',
  streak_days: 12,
}

// OpenClaw 会话数据 - 完整多轮对话
export const mockSessions: OpenClawSession[] = [
  {
    id: 1,
    title: '分析 PointNav 论文核心创新点',
    category: 'paper',
    project: 'paper-reproduce',
    tags: ['论文', '导航', 'PointNav'],
    created_at: now - 2 * DAY,
    summary: '深入分析了 PointNav 论文的视觉编码器设计和奖励函数创新',
    messages: [
      { role: 'user', content: '帮我分析这篇 PointNav 论文的核心创新点，特别是它的视觉编码器设计和 reward shaping 策略。', timestamp: now - 2 * DAY },
      { role: 'assistant', content: '这篇论文的核心创新有三点：\n\n1. **视觉编码器**：采用 ResNet-18 作为 backbone，但关键创新在于引入了 depth prediction auxiliary task，让编码器同时学习深度估计，这显著提升了导航策略对空间结构的理解。\n\n2. **Reward Shaping**：不同于传统的稀疏奖励（只在到达目标时给正奖励），论文设计了基于 geodesic distance 的密集奖励：\n   - 每步奖励 = Δd(geodesic) × α + success_reward\n   - 其中 α=1.0 用于平衡探索和利用\n\n3. **训练策略**：采用 DD-PPO（Decentralized Distributed PPO），在 64 个 GPU 上并行训练，每个 worker 独立收集经验，通过 gradient averaging 同步。\n\n建议你在复现时重点关注 reward shaping 部分，这是性能提升的关键。', timestamp: now - 2 * DAY + 30 },
      { role: 'user', content: '那 geodesic distance 具体怎么计算的？在 Habitat 环境里有现成的 API 吗？', timestamp: now - 2 * DAY + 120 },
      { role: 'assistant', content: 'Habitat 提供了现成的 API：\n\n```python\n# 获取 geodesic distance\ngeo_dist = env.sim.geodesic_distance(\n    position_a=agent_position,\n    position_b=goal_position\n)\n```\n\n底层实现是基于 NavMesh 的最短路径计算。注意几个坑：\n- 如果两点之间不可达，返回 `inf`，需要处理这种情况\n- NavMesh 的精度取决于 mesh 的分辨率，建议用 `navmesh_settings.cell_size=0.05`\n- 计算开销不大，每步调用不会成为瓶颈\n\n你的 reward function 可以这样写：\n```python\ndef compute_reward(prev_dist, curr_dist, success):\n    reward = prev_dist - curr_dist  # 接近目标为正\n    if success:\n        reward += 10.0  # success bonus\n    reward -= 0.01  # step penalty\n    return reward\n```', timestamp: now - 2 * DAY + 150 },
    ],
  },
  {
    id: 2,
    title: 'PPO 训练 reward 不收敛排查',
    category: 'debug',
    project: 'embodied-nav',
    tags: ['PPO', '训练', '调试'],
    created_at: now - DAY,
    summary: '排查了 PPO 训练不收敛问题，发现是 reward normalization 和 learning rate 的问题',
    messages: [
      { role: 'user', content: '我的 PPO 训练跑了 500 个 epoch，reward 一直在 -2 到 0 之间震荡，完全不收敛。loss 也在跳。帮我排查一下。', timestamp: now - DAY },
      { role: 'assistant', content: '典型的 PPO 不收敛问题，我们逐步排查：\n\n**1. 先看 reward 分布**\n你的 reward range 是 [-2, 0]，这说明 agent 基本没有成功到达目标。先确认：\n- 目标距离是否合理？初始距离太远会导致探索困难\n- success rate 是多少？如果接近 0%，说明任务太难\n\n**2. 检查 hyperparameters**\n常见问题：\n- `lr` 太大导致策略崩溃，建议 `2.5e-4`\n- `clip_param` 建议 `0.1`（不是默认的 0.2）\n- `num_steps` 太短，导航任务建议至少 `128`\n- `entropy_coef` 太小，建议 `0.01` 保持探索\n\n**3. Reward normalization**\n你有做 reward normalization 吗？PPO 对 reward scale 很敏感。\n\n先把这些信息发给我看看。', timestamp: now - DAY + 30 },
      { role: 'user', content: '我的 lr 是 1e-3，clip 是 0.2，没有做 reward normalization。初始距离大概 5-15 米。', timestamp: now - DAY + 180 },
      { role: 'assistant', content: '找到问题了，主要是两个：\n\n**问题 1: lr 太大**\n`1e-3` 对 PPO 来说太激进了，会导致策略更新过大，KL divergence 爆炸。改成 `2.5e-4`。\n\n**问题 2: 缺少 reward normalization**\n这是最关键的。加上 running mean/std normalization：\n\n```python\nclass RunningMeanStd:\n    def __init__(self):\n        self.mean = 0.0\n        self.var = 1.0\n        self.count = 1e-4\n    \n    def update(self, x):\n        batch_mean = np.mean(x)\n        batch_var = np.var(x)\n        batch_count = len(x)\n        self.update_from_moments(batch_mean, batch_var, batch_count)\n    \n    def normalize(self, x):\n        return (x - self.mean) / np.sqrt(self.var + 1e-8)\n```\n\n改完这两个，重新训练应该能看到明显改善。另外建议加上 gradient clipping `max_grad_norm=0.5`。', timestamp: now - DAY + 210 },
      { role: 'user', content: '改了之后 reward 开始上升了！但是到 epoch 200 左右又开始下降，是过拟合了吗？', timestamp: now - DAY + HOUR },
      { role: 'assistant', content: '不太像过拟合，更像是 **policy collapse**。PPO 在训练中期容易出现策略退化。\n\n建议：\n1. **增大 entropy coefficient** 到 `0.02`，防止策略过早收敛\n2. **使用 learning rate schedule**：线性衰减到 0\n3. **增加训练环境多样性**：用多个不同的 scene 训练\n\n```python\n# LR schedule\ndef lr_lambda(epoch):\n    return 1.0 - epoch / total_epochs\n\nscheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)\n```\n\n另外检查一下 value function 的 loss 是否也在震荡，如果是的话可能需要增大 `value_loss_coef`。', timestamp: now - DAY + HOUR + 30 },
    ],
  },
  {
    id: 3,
    title: 'Review grasp policy 代码',
    category: 'review',
    project: 'grasp-policy',
    tags: ['代码审查', '抓取', '策略'],
    created_at: now - 3 * DAY,
    summary: '审查了抓取策略代码，发现了点云处理和 action space 设计的问题',
    messages: [
      { role: 'user', content: '帮我 review 一下 grasp_policy/model.py 的代码，特别关注网络结构和 action space 设计。', timestamp: now - 3 * DAY },
      { role: 'assistant', content: '看了你的代码，有几个问题需要注意：\n\n**1. 点云预处理 (Critical)**\n你直接把原始点云喂进 PointNet，但没有做 voxel downsampling。10万个点的计算量太大，建议先降采样到 2048 个点：\n```python\nimport open3d as o3d\npcd = o3d.geometry.PointCloud()\npcd.points = o3d.utility.Vector3dVector(points)\npcd = pcd.voxel_down_sample(voxel_size=0.005)\n```\n\n**2. Action Space 设计 (High)**\n你用的是连续 6-DoF action space (x,y,z,roll,pitch,yaw)，但 yaw 的范围是 [-π, π]，这会导致 boundary 问题。建议用 quaternion 表示旋转，或者把 yaw 拆成 sin/cos 两个维度。\n\n**3. Reward 设计 (Medium)**\n抓取成功只给 +1 奖励太稀疏了。建议加入中间奖励：\n- 接近物体: +0.1 × Δdistance\n- 手指闭合时接触物体: +0.3\n- 成功抬起: +1.0\n\n**4. 网络结构 (Low)**\nPointNet 的 feature 维度 1024 对于抓取任务可能过大，512 就够了。', timestamp: now - 3 * DAY + 60 },
    ],
  },
  {
    id: 4,
    title: 'ROS2 tf2 坐标变换调试',
    category: 'debug',
    project: 'ros2-workspace',
    tags: ['ROS2', 'tf2', '调试'],
    created_at: now - 4 * DAY,
    summary: '解决了 ROS2 tf2 坐标变换超时问题，原因是 static transform publisher 启动顺序',
    messages: [
      { role: 'user', content: 'ROS2 的 tf2 坐标变换一直报 LookupException: "base_link" passed to lookupTransform argument target_frame does not exist。但我明明发布了 static transform。', timestamp: now - 4 * DAY },
      { role: 'assistant', content: '这个问题通常是 **启动顺序** 导致的。tf2 的 buffer 需要时间来接收 transform。\n\n排查步骤：\n\n1. **确认 transform 是否在发布**：\n```bash\nros2 topic echo /tf_static\n```\n\n2. **检查 frame 名称**：注意有没有多余的 `/` 前缀。ROS2 的 frame 不应该以 `/` 开头：\n```python\n# 错误\ntarget_frame = "/base_link"\n# 正确\ntarget_frame = "base_link"\n```\n\n3. **增加 timeout**：\n```python\ntry:\n    transform = tf_buffer.lookup_transform(\n        "base_link", "camera_link",\n        rclpy.time.Time(),\n        timeout=rclpy.duration.Duration(seconds=2.0)\n    )\nexcept TransformException as e:\n    self.get_logger().warn(f"Transform not available: {e}")\n```\n\n4. **确保 static_transform_publisher 先启动**：在 launch 文件中设置依赖。\n\n最常见的原因就是第 2 点，frame 名称带了 `/`。', timestamp: now - 4 * DAY + 45 },
    ],
  },
  {
    id: 5,
    title: '设计 sim2real domain randomization 方案',
    category: 'architecture',
    project: 'sim2real-transfer',
    tags: ['sim2real', 'domain randomization', '方案设计'],
    created_at: now - 5 * DAY,
    summary: '设计了完整的 domain randomization 方案，覆盖视觉、物理和动力学三个层面',
    messages: [
      { role: 'user', content: '我的导航策略在 Habitat 仿真中 success rate 85%，但部署到真实机器人上只有 30%。帮我设计一个 sim2real 的 domain randomization 方案。', timestamp: now - 5 * DAY },
      { role: 'assistant', content: 'sim2real gap 55% 确实很大。我建议从三个层面做 domain randomization：\n\n## 1. 视觉层 (Visual DR)\n- **光照随机化**：随机调整环境光强度 [0.3, 1.5]、色温 [3000K, 7000K]\n- **纹理随机化**：墙面、地面纹理随机替换\n- **相机噪声**：添加高斯噪声 σ∈[0, 0.05]，模拟真实相机\n- **色彩抖动**：brightness/contrast/saturation 各 ±20%\n\n## 2. 物理层 (Physics DR)\n- **摩擦系数**：地面摩擦 μ∈[0.3, 1.0]\n- **碰撞参数**：restitution ∈[0.0, 0.5]\n- **障碍物随机放置**：每个 episode 随机生成 3-8 个障碍物\n\n## 3. 动力学层 (Dynamics DR)\n- **执行噪声**：action 加高斯噪声 σ∈[0, 0.1]\n- **延迟模拟**：随机 1-3 帧的 action delay\n- **里程计漂移**：累积误差模拟\n\n实现建议用 Habitat 的 `habitat.config` 配置系统，每个 episode reset 时随机采样参数。', timestamp: now - 5 * DAY + 90 },
    ],
  },
  {
    id: 6,
    title: '总结今日实验结果',
    category: 'experiment',
    project: 'embodied-nav',
    tags: ['实验', '总结', '知识库'],
    created_at: now - DAY + 10 * HOUR,
    summary: '总结了 PPO vs SAC 在导航任务上的对比实验结果',
    messages: [
      { role: 'user', content: '帮我总结今天的实验结果。PPO 和 SAC 在 HabitatNav-v2 上跑了 1000 个 episode 的评估。PPO success rate 78%, SPL 0.62; SAC success rate 71%, SPL 0.55。', timestamp: now - DAY + 10 * HOUR },
      { role: 'assistant', content: '## 实验总结：PPO vs SAC 导航性能对比\n\n**实验设置**\n- 环境：HabitatNav-v2\n- 评估 episodes：1000\n- 场景：Gibson 数据集 val split\n\n**结果对比**\n| 指标 | PPO | SAC | 差异 |\n|------|-----|-----|------|\n| Success Rate | 78% | 71% | +7% |\n| SPL | 0.62 | 0.55 | +0.07 |\n\n**分析**\n1. PPO 在 success rate 和 SPL 上均优于 SAC，这与 Habitat Challenge 的经验一致\n2. PPO 的优势主要来自更稳定的策略更新（clipping 机制）\n3. SAC 在长距离导航上表现更差，可能是 entropy regularization 导致过度探索\n\n**下一步建议**\n- 以 PPO 作为基线，继续优化 reward shaping\n- 尝试 DD-PPO 分布式训练提升样本效率\n- 加入 auxiliary tasks（depth prediction）提升视觉表征\n\n已写入知识库。', timestamp: now - DAY + 10 * HOUR + 30 },
    ],
  },
  {
    id: 7,
    title: 'TDD 引导导航规划器开发',
    category: 'review',
    project: 'embodied-nav',
    tags: ['TDD', '导航', '测试'],
    created_at: now - 6 * DAY,
    summary: '使用 TDD 方法开发导航规划器的路径平滑模块',
    messages: [
      { role: 'user', content: '我要给 nav_planner 加一个路径平滑功能，用 TDD 的方式来开发。帮我先设计测试用例。', timestamp: now - 6 * DAY },
      { role: 'assistant', content: '好的，先写测试再实现。路径平滑的核心测试用例：\n\n```python\nimport pytest\nimport numpy as np\nfrom nav_planner.path_smoother import smooth_path\n\nclass TestPathSmoother:\n    def test_straight_path_unchanged(self):\n        """直线路径不应被修改"""\n        path = np.array([[0,0], [1,0], [2,0], [3,0]])\n        result = smooth_path(path)\n        np.testing.assert_array_almost_equal(result, path)\n    \n    def test_sharp_turn_smoothed(self):\n        """90度急转弯应被平滑"""\n        path = np.array([[0,0], [1,0], [1,1]])\n        result = smooth_path(path)\n        # 平滑后中间点应偏移\n        assert result[1][0] < 1.0\n        assert result[1][1] > 0.0\n    \n    def test_preserves_start_end(self):\n        """起点和终点不应改变"""\n        path = np.array([[0,0], [1,1], [2,0], [3,1]])\n        result = smooth_path(path)\n        np.testing.assert_array_equal(result[0], path[0])\n        np.testing.assert_array_equal(result[-1], path[-1])\n    \n    def test_obstacle_avoidance(self):\n        """平滑后路径不应穿过障碍物"""\n        path = np.array([[0,0], [1,0], [2,0]])\n        obstacles = [np.array([1.5, 0.3])]\n        result = smooth_path(path, obstacles=obstacles)\n        # 验证所有点到障碍物距离 > safety_margin\n        for point in result:\n            for obs in obstacles:\n                assert np.linalg.norm(point - obs) > 0.2\n```\n\n先跑这些测试（应该全部 FAIL），然后我们再实现 `smooth_path` 函数。', timestamp: now - 6 * DAY + 45 },
    ],
  },
  {
    id: 8,
    title: '对比 Habitat 和 iGibson 仿真环境',
    category: 'learning',
    project: 'paper-reproduce',
    tags: ['仿真', 'Habitat', 'iGibson', '对比'],
    created_at: now - 7 * DAY,
    summary: '对比了 Habitat 和 iGibson 两个仿真环境的优劣，决定使用 Habitat',
    messages: [
      { role: 'user', content: '我在选仿真环境，Habitat 和 iGibson 各有什么优劣？我的任务是室内视觉导航。', timestamp: now - 7 * DAY },
      { role: 'assistant', content: '两个环境我都用过，给你详细对比：\n\n## Habitat\n**优势**：\n- 渲染速度极快（GPU 加速，单 GPU 可达 10000+ FPS）\n- 社区活跃，Meta AI 持续维护\n- Habitat Challenge 提供标准 benchmark\n- 支持 Gibson/MP3D/HM3D 多个数据集\n\n**劣势**：\n- 物理仿真较弱（不适合操作任务）\n- 安装配置复杂（需要编译 habitat-sim）\n\n## iGibson\n**优势**：\n- 物理仿真更真实（基于 PyBullet）\n- 支持交互式物体操作\n- 内置多种机器人模型\n\n**劣势**：\n- 渲染速度慢（约 100-300 FPS）\n- 社区较小，更新频率低\n- 场景数量有限\n\n## 建议\n你的任务是**视觉导航**，不涉及物体操作，所以 **Habitat 是更好的选择**：\n1. 渲染速度快 → 训练效率高\n2. 标准 benchmark → 方便与 SOTA 对比\n3. HM3D 数据集有 800+ 场景 → 泛化性好\n\n如果后续要做 navigation + manipulation，再考虑 iGibson 或 Habitat 3.0。', timestamp: now - 7 * DAY + 60 },
    ],
  },
  {
    id: 9,
    title: '设计 Habitat 环境的 reward function',
    category: 'architecture',
    project: 'embodied-nav',
    tags: ['Habitat', 'reward', '强化学习'],
    created_at: now - 8 * DAY,
    summary: '设计了多层次的导航奖励函数，包含距离奖励、探索奖励和安全奖励',
    messages: [
      { role: 'user', content: '帮我设计一个更好的 Habitat 导航 reward function，现在的太简单了只有距离奖励。', timestamp: now - 8 * DAY },
      { role: 'assistant', content: '好的，我建议设计一个多层次的奖励函数：\n\n## 1. 距离奖励（基础）\n```python\nr_dist = (prev_geo_dist - curr_geo_dist) * 1.0\n```\n\n## 2. 探索奖励（鼓励覆盖新区域）\n```python\nr_explore = 0.1 if visited_new_cell else 0.0\n```\n\n## 3. 安全奖励（避免碰撞）\n```python\nr_safety = -0.05 if collision else 0.0\n```\n\n## 4. 效率奖励（鼓励短路径）\n```python\nr_efficiency = -0.01  # 每步惩罚\n```\n\n## 5. 成功奖励\n```python\nr_success = 10.0 if success else 0.0\n```\n\n最终：`reward = r_dist + r_explore + r_safety + r_efficiency + r_success`\n\n关键是各项权重的平衡，建议先用这个配置训练，然后根据 agent 行为调整。', timestamp: now - 8 * DAY + 45 },
      { role: 'user', content: '探索奖励怎么实现？怎么判断是否访问了新区域？', timestamp: now - 8 * DAY + 300 },
      { role: 'assistant', content: '用一个 occupancy grid 来追踪已访问区域：\n\n```python\nclass ExplorationTracker:\n    def __init__(self, resolution=0.5):\n        self.visited = set()\n        self.resolution = resolution\n    \n    def update(self, position):\n        cell = (int(position[0] / self.resolution),\n                int(position[2] / self.resolution))\n        is_new = cell not in self.visited\n        self.visited.add(cell)\n        return is_new\n    \n    def reset(self):\n        self.visited.clear()\n```\n\nresolution=0.5 表示 50cm 的网格，太细会导致奖励太密集，太粗会失去意义。\n\n在 episode reset 时调用 `tracker.reset()`。', timestamp: now - 8 * DAY + 330 },
    ],
  },
  {
    id: 10,
    title: '分析 SAC 和 TD3 在连续控制任务上的差异',
    category: 'paper',
    project: 'grasp-policy',
    tags: ['SAC', 'TD3', '连续控制', '论文'],
    created_at: now - 9 * DAY,
    summary: '对比了 SAC 和 TD3 两种算法在机械臂连续控制任务上的表现差异',
    messages: [
      { role: 'user', content: '我在做机械臂抓取，SAC 和 TD3 哪个更适合？帮我分析下两者的差异。', timestamp: now - 9 * DAY },
      { role: 'assistant', content: '## SAC vs TD3 对比分析\n\n### 核心区别\n- **SAC**：最大熵框架，自动调节 entropy coefficient，鼓励探索\n- **TD3**：确定性策略 + 双 Q 网络 + 延迟更新，更保守\n\n### 在机械臂抓取任务上\n\n| 维度 | SAC | TD3 |\n|------|-----|-----|\n| 探索能力 | 强（entropy bonus） | 弱（依赖噪声） |\n| 样本效率 | 中等 | 较高 |\n| 训练稳定性 | 好 | 好 |\n| 超参敏感度 | 低（自动调 alpha） | 中等 |\n| 适合场景 | 多模态解、需要探索 | 单一最优解 |\n\n### 建议\n抓取任务通常有**多种可行的抓取姿态**，这是多模态问题，**SAC 更适合**。\n\nTD3 适合那种只有一个最优解的任务（比如精确轨迹跟踪）。\n\n不过建议两个都跑一下做对比，作为论文的 baseline。', timestamp: now - 9 * DAY + 60 },
    ],
  },
  {
    id: 11,
    title: '帮我写一个 ROS2 的 action server',
    category: 'architecture',
    project: 'ros2-workspace',
    tags: ['ROS2', 'action server', '导航'],
    created_at: now - 10 * DAY,
    summary: '实现了一个 ROS2 action server 用于导航任务的执行和反馈',
    messages: [
      { role: 'user', content: '帮我写一个 ROS2 的 action server，用于执行导航到目标点的任务，需要有进度反馈。', timestamp: now - 10 * DAY },
      { role: 'assistant', content: '```python\nimport rclpy\nfrom rclpy.action import ActionServer\nfrom rclpy.node import Node\nfrom nav2_msgs.action import NavigateToPose\nimport math\n\nclass NavActionServer(Node):\n    def __init__(self):\n        super().__init__("nav_action_server")\n        self._action_server = ActionServer(\n            self, NavigateToPose, "navigate_to_pose",\n            self.execute_callback\n        )\n        self.get_logger().info("Navigation action server started")\n    \n    async def execute_callback(self, goal_handle):\n        self.get_logger().info("Executing navigation goal...")\n        feedback_msg = NavigateToPose.Feedback()\n        \n        target = goal_handle.request.pose.pose.position\n        # 模拟导航过程\n        for i in range(100):\n            # 计算剩余距离\n            feedback_msg.distance_remaining = \\\n                math.sqrt((target.x - i*0.1)**2 + (target.y)**2)\n            goal_handle.publish_feedback(feedback_msg)\n            await asyncio.sleep(0.1)\n        \n        goal_handle.succeed()\n        result = NavigateToPose.Result()\n        return result\n```\n\n关键点：\n1. 用 `async` 回调支持非阻塞执行\n2. 通过 `publish_feedback` 实时反馈进度\n3. 可以在回调中检查 `goal_handle.is_cancel_requested` 支持取消', timestamp: now - 10 * DAY + 60 },
    ],
  },
  {
    id: 12,
    title: 'Review sim2real transfer 代码',
    category: 'review',
    project: 'sim2real-transfer',
    tags: ['代码审查', 'sim2real', 'domain randomization'],
    created_at: now - 11 * DAY,
    summary: '审查了 sim2real transfer 的 domain randomization 实现代码',
    messages: [
      { role: 'user', content: '帮我 review 一下 sim2real 的 domain randomization 代码，主要是视觉随机化部分。', timestamp: now - 11 * DAY },
      { role: 'assistant', content: '看了你的代码，几个问题：\n\n**1. 随机化范围太窄 (Critical)**\n你的光照随机化只在 [0.8, 1.2] 范围，这远不够。真实环境光照变化很大，建议 [0.3, 2.0]。\n\n**2. 纹理随机化缺失 (High)**\n你只做了颜色抖动，没有纹理替换。建议加入：\n```python\ndef randomize_texture(mesh, texture_pool):\n    idx = np.random.randint(len(texture_pool))\n    mesh.visual.material.image = texture_pool[idx]\n```\n\n**3. 相机内参没有随机化 (Medium)**\n真实相机和仿真相机的 FOV、畸变参数不同，建议加入：\n- FOV: [60, 90] 度\n- 径向畸变: k1 ~ U(-0.1, 0.1)\n\n**4. 随机化时机 (Low)**\n你在每个 step 都随机化，太频繁了。建议每个 episode 开始时随机化一次就够了。', timestamp: now - 11 * DAY + 60 },
    ],
  },
  {
    id: 13,
    title: '整理本周实验数据，生成对比表格',
    category: 'experiment',
    project: 'embodied-nav',
    tags: ['实验', '数据整理', '对比'],
    created_at: now - 2 * DAY + 8 * HOUR,
    summary: '整理了一周的导航实验数据，生成了多维度对比表格',
    messages: [
      { role: 'user', content: '帮我整理这周的实验数据。PPO 跑了 3 个配置，SAC 跑了 2 个配置，都在 HabitatNav-v2 上。', timestamp: now - 2 * DAY + 8 * HOUR },
      { role: 'assistant', content: '## 本周实验数据汇总\n\n| 配置 | 算法 | LR | Entropy | Success Rate | SPL | Avg Steps |\n|------|------|-----|---------|-------------|-----|-----------|\n| PPO-v1 | PPO | 2.5e-4 | 0.01 | 78% | 0.62 | 142 |\n| PPO-v2 | PPO | 2.5e-4 | 0.02 | 81% | 0.65 | 135 |\n| PPO-v3 | PPO | 1e-4 | 0.02 | 76% | 0.60 | 151 |\n| SAC-v1 | SAC | 3e-4 | auto | 71% | 0.55 | 168 |\n| SAC-v2 | SAC | 1e-4 | auto | 73% | 0.57 | 160 |\n\n**关键发现**：\n1. PPO-v2 是目前最优配置（entropy=0.02 很关键）\n2. 降低 LR 对 PPO 帮助不大，反而降低了性能\n3. SAC 整体不如 PPO，但 SAC-v2 的 LR 调低后有改善\n\n**下一步建议**：\n- 基于 PPO-v2 继续优化\n- 尝试加入 auxiliary task（depth prediction）\n- 增加训练 epoch 到 1000 看是否还能提升', timestamp: now - 2 * DAY + 8 * HOUR + 45 },
    ],
  },
  {
    id: 14,
    title: '讨论 ViT 在视觉导航中的应用前景',
    category: 'learning',
    project: 'paper-reproduce',
    tags: ['ViT', '视觉导航', 'Transformer'],
    created_at: now - 12 * DAY,
    summary: '探讨了 Vision Transformer 替代 CNN 作为导航视觉编码器的可行性',
    messages: [
      { role: 'user', content: '最近 ViT 很火，能不能用 ViT 替代 ResNet 作为导航的视觉编码器？', timestamp: now - 12 * DAY },
      { role: 'assistant', content: '这是个好问题，目前学术界确实在探索这个方向。\n\n## ViT 用于导航的优劣\n\n**优势**：\n- 全局注意力机制，能捕获长距离空间关系\n- 在大规模预训练后泛化能力强\n- 最新的 DINOv2 提供了很好的视觉特征\n\n**劣势**：\n- 计算量大，推理速度慢（对实时导航是问题）\n- 需要大量数据预训练\n- 对小目标的感知不如 CNN\n\n## 最新进展\n- **VC-1**（Meta, 2023）：用 MAE 预训练的 ViT，在 Habitat 导航上超过 ResNet\n- **EmbCLIP**：用 CLIP 的视觉编码器做导航，zero-shot 能力强\n- **NaviLLM**：直接用 LLM + ViT 做端到端导航\n\n## 建议\n如果你的 GPU 资源充足，可以试试用 **ViT-B/16 + DINOv2 预训练权重** 替代 ResNet-18。预计 success rate 能提升 3-5%，但推理速度会慢 2-3 倍。\n\n折中方案：用 **MobileViT** 或 **EfficientViT**，兼顾精度和速度。', timestamp: now - 12 * DAY + 60 },
    ],
  },
  {
    id: 15,
    title: '调试 CUDA out of memory 问题',
    category: 'debug',
    project: 'embodied-nav',
    tags: ['CUDA', 'OOM', '调试', 'GPU'],
    created_at: now - 3 * DAY + 6 * HOUR,
    summary: '排查并解决了训练过程中的 CUDA OOM 问题',
    messages: [
      { role: 'user', content: '训练到 epoch 50 左右就 CUDA out of memory 了，但刚开始是正常的。怎么回事？', timestamp: now - 3 * DAY + 6 * HOUR },
      { role: 'assistant', content: '训练中途 OOM 通常是**显存泄漏**，不是模型本身太大。常见原因：\n\n**1. 计算图未释放（最常见）**\n```python\n# 错误：loss 保留了计算图\nlosses.append(loss)\n\n# 正确：只保留数值\nlosses.append(loss.item())\n```\n\n**2. 梯度累积未清零**\n确保每个 batch 后调用 `optimizer.zero_grad()`\n\n**3. TensorBoard 日志写入 tensor**\n```python\n# 错误\nwriter.add_scalar("loss", loss, step)\n\n# 正确\nwriter.add_scalar("loss", loss.item(), step)\n```\n\n**排查方法**：\n```python\nimport torch\nprint(torch.cuda.memory_summary())\n```\n\n在每个 epoch 结束时打印显存使用，看是否持续增长。如果是，就是泄漏。\n\n另外加上 `torch.cuda.empty_cache()` 在每个 epoch 结束时调用，虽然不能解决根本问题，但能缓解。', timestamp: now - 3 * DAY + 6 * HOUR + 30 },
      { role: 'user', content: '找到了！是我把 loss append 到列表里了，没有用 .item()。改了之后稳定了。', timestamp: now - 3 * DAY + 7 * HOUR },
      { role: 'assistant', content: '经典问题。建议你加一个 memory monitor 工具函数：\n\n```python\ndef log_gpu_memory(tag=""):\n    allocated = torch.cuda.memory_allocated() / 1024**3\n    reserved = torch.cuda.memory_reserved() / 1024**3\n    print(f"[GPU {tag}] Allocated: {allocated:.2f}GB, Reserved: {reserved:.2f}GB")\n```\n\n在训练循环的关键位置调用，方便以后快速定位类似问题。', timestamp: now - 3 * DAY + 7 * HOUR + 15 },
    ],
  },
  {
    id: 16,
    title: '设计点云抓取策略的网络架构',
    category: 'architecture',
    project: 'grasp-policy',
    tags: ['点云', '网络架构', 'PointNet++'],
    created_at: now - 13 * DAY,
    summary: '设计了基于 PointNet++ 的抓取策略网络，包含特征提取和抓取姿态预测',
    messages: [
      { role: 'user', content: '帮我设计一个基于点云的抓取策略网络，输入是桌面物体的点云，输出是抓取姿态。', timestamp: now - 13 * DAY },
      { role: 'assistant', content: '## 网络架构设计\n\n### 输入\n- 点云: (N, 3) 或 (N, 6) 带法向量\n- 降采样到 2048 个点\n\n### 特征提取（PointNet++）\n```\nInput (2048, 3)\n  → SA Layer 1: 512 points, radius=0.1, [64, 64, 128]\n  → SA Layer 2: 128 points, radius=0.2, [128, 128, 256]\n  → SA Layer 3: 32 points, radius=0.4, [256, 256, 512]\n  → Global Feature: (1, 512)\n```\n\n### 抓取姿态预测头\n```\nGlobal Feature (512)\n  → FC(512, 256) + ReLU + Dropout(0.3)\n  → FC(256, 128) + ReLU\n  → 分支1: FC(128, 3) → 抓取位置 (x, y, z)\n  → 分支2: FC(128, 4) → 抓取朝向 (quaternion)\n  → 分支3: FC(128, 1) → 抓取宽度 (gripper width)\n  → 分支4: FC(128, 1) → 抓取质量分数 (sigmoid)\n```\n\n### 损失函数\n```python\nloss = L1(pos_pred, pos_gt) + \\\n       quaternion_loss(quat_pred, quat_gt) + \\\n       L1(width_pred, width_gt) + \\\n       BCE(quality_pred, quality_gt)\n```\n\n建议用 **Contact-GraspNet** 的数据集做训练，有 17k+ 标注的抓取姿态。', timestamp: now - 13 * DAY + 60 },
    ],
  },
]

// 知识库文档
export const mockDocuments: OpenClawDocument[] = [
  {
    id: 1,
    title: '3月18日任务：完成 PointNav 基线实验',
    type: 'daily_task',
    content: '## 今日任务\n\n1. 在 HabitatNav-v2 环境中完成 PPO 基线训练（500 epochs）\n2. 评估 PPO vs SAC 在 Gibson val split 上的性能\n3. 记录实验结果，更新论文 Table 1\n\n## 完成情况\n- [x] PPO 训练完成，best success rate 78%\n- [x] SAC 训练完成，best success rate 71%\n- [x] 实验结果已记录\n- [ ] 论文 Table 1 待更新\n\n## 明日计划\n- 尝试 DD-PPO 分布式训练\n- 加入 depth prediction auxiliary task',
    tags: ['任务', '实验', 'PointNav'],
    created_at: now - DAY,
    source_session_id: 6,
  },
  {
    id: 2,
    title: '论文笔记：Habitat 2.0 环境配置要点',
    type: 'paper_note',
    content: '## Habitat 2.0 关键配置\n\n### 环境安装\n```bash\nconda create -n habitat python=3.9\npip install habitat-sim==0.3.0 --extra-index-url https://aihabitat.org/packages/habitat-sim\npip install habitat-lab==0.3.0\n```\n\n### 数据集配置\n- Gibson: 72 个场景，适合快速验证\n- MP3D: 90 个场景，更大更复杂\n- HM3D: 800+ 场景，推荐用于最终训练\n\n### 性能优化\n- 使用 `habitat.simulator.habitat_sim_v0.gpu_gpu=True` 开启 GPU 渲染\n- batch size 建议 4-8（取决于 GPU 显存）\n- 使用 `VectorEnv` 并行化环境',
    tags: ['Habitat', '配置', '论文'],
    created_at: now - 5 * DAY,
    source_session_id: 8,
  },
  {
    id: 3,
    title: '实验日志：PPO vs SAC 导航对比',
    type: 'experiment_log',
    content: '## 实验设置\n- 环境：HabitatNav-v2 (Gibson val split)\n- 训练：500 epochs, lr=2.5e-4\n- 评估：1000 episodes\n\n## 结果\n| 指标 | PPO | SAC |\n|------|-----|-----|\n| Success Rate | 78% | 71% |\n| SPL | 0.62 | 0.55 |\n| Avg Path Length | 8.3m | 9.1m |\n| Avg Episode Steps | 142 | 168 |\n\n## 结论\nPPO 在所有指标上优于 SAC，主要优势在于策略稳定性。SAC 的 entropy regularization 在导航任务中导致过度探索。\n\n## 训练曲线\n- PPO: reward 在 epoch 100 开始稳定上升，epoch 300 收敛\n- SAC: reward 波动较大，epoch 400 才基本收敛',
    tags: ['PPO', 'SAC', '对比实验'],
    created_at: now - DAY,
    source_session_id: 6,
  },
  {
    id: 4,
    title: '会议纪要：组会讨论 sim2real gap',
    type: 'meeting_note',
    content: '## 组会纪要 - 2026.03.15\n\n### 参会人员\n导师、李同学、张同学、王同学\n\n### 讨论内容\n1. **sim2real gap 现状**：仿真 85% → 真实 30%，gap 太大\n2. **导师建议**：\n   - 先做 visual domain randomization\n   - 考虑用 real2sim 的方式缩小 gap\n   - 参考 NVIDIA 的 DR 论文\n3. **分工**：\n   - 李同学：实现 visual DR（光照、纹理、噪声）\n   - 张同学：实现 dynamics DR（摩擦、延迟）\n   - 王同学：搭建真实环境测试平台\n\n### 下次会议\n3月22日，汇报 DR 实验结果',
    tags: ['组会', 'sim2real', '讨论'],
    created_at: now - 4 * DAY,
    source_session_id: 5,
  },
  {
    id: 5,
    title: '3月17日任务：ROS2 导航栈调试',
    type: 'daily_task',
    content: '## 今日任务\n\n1. 修复 tf2 坐标变换超时问题\n2. 测试 nav2 导航栈在真实机器人上的表现\n3. 记录 odometry 漂移数据\n\n## 完成情况\n- [x] tf2 问题已修复（frame 名称带了多余的 /）\n- [x] nav2 基本功能正常\n- [ ] odometry 漂移数据收集中（需要更长时间）\n\n## 遇到的问题\n- nav2 的 costmap 更新频率太低，导致避障反应慢\n- 建议调整 `update_frequency` 从 5Hz 到 10Hz',
    tags: ['ROS2', '导航', '调试'],
    created_at: now - 2 * DAY,
    source_session_id: 4,
  },
  {
    id: 6,
    title: '论文笔记：PointNav 视觉编码器设计',
    type: 'paper_note',
    content: '## PointNav 核心创新\n\n### 视觉编码器\n- ResNet-18 backbone + depth prediction auxiliary task\n- 深度估计辅助任务显著提升空间理解\n\n### Reward Shaping\n- 基于 geodesic distance 的密集奖励\n- reward = delta_d * alpha + success_reward\n- alpha=1.0 平衡探索和利用\n\n### DD-PPO 训练\n- 64 GPU 并行训练\n- 独立收集经验 + gradient averaging\n- 比标准 PPO 快 10x\n\n### 复现要点\n- geodesic distance 用 Habitat API 直接获取\n- NavMesh cell_size=0.05 保证精度\n- 注意处理不可达情况（返回 inf）',
    tags: ['PointNav', '论文', '视觉编码器'],
    created_at: now - 2 * DAY + 2 * HOUR,
    source_session_id: 1,
  },
  {
    id: 7,
    title: '实验日志：Reward Function 消融实验',
    type: 'experiment_log',
    content: '## 消融实验：多层次奖励函数\n\n### 实验配置\n- 基础环境：HabitatNav-v2\n- 训练 epoch：300\n- 评估 episode：500\n\n### 结果\n| 配置 | Success Rate | SPL |\n|------|-------------|-----|\n| 仅距离奖励 | 72% | 0.56 |\n| +探索奖励 | 76% | 0.59 |\n| +安全奖励 | 78% | 0.61 |\n| +效率惩罚 | 81% | 0.65 |\n| 全部（最终） | 81% | 0.65 |\n\n### 结论\n探索奖励和效率惩罚贡献最大，安全奖励对 SPL 有帮助',
    tags: ['消融实验', 'reward', '导航'],
    created_at: now - 8 * DAY,
    source_session_id: 9,
  },
  {
    id: 8,
    title: '3月15日任务：sim2real DR 实现',
    type: 'daily_task',
    content: '## 今日任务\n\n1. 实现视觉层 domain randomization\n2. 测试光照和纹理随机化效果\n3. 收集真实环境测试数据\n\n## 完成情况\n- [x] 光照随机化实现（范围 [0.3, 2.0]）\n- [x] 纹理随机化实现（20 种纹理池）\n- [x] 相机噪声添加\n- [ ] 真实环境数据收集（设备占用中）\n\n## 问题记录\n- 纹理随机化导致渲染速度下降 15%\n- 需要优化纹理加载策略',
    tags: ['sim2real', 'DR', '任务'],
    created_at: now - 4 * DAY,
    source_session_id: 12,
  },
  {
    id: 9,
    title: '论文笔记：ViT 在具身导航中的应用',
    type: 'paper_note',
    content: '## ViT for Embodied Navigation\n\n### 相关工作\n- VC-1 (Meta, 2023): MAE 预训练 ViT，超过 ResNet\n- EmbCLIP: CLIP 视觉编码器 + 导航策略\n- NaviLLM: LLM + ViT 端到端导航\n\n### ViT 优势\n- 全局注意力捕获长距离空间关系\n- 大规模预训练后泛化能力强\n- DINOv2 提供优质视觉特征\n\n### ViT 劣势\n- 推理速度慢（比 ResNet 慢 2-3x）\n- 对小目标感知不如 CNN\n\n### 折中方案\n- MobileViT: 轻量级，适合实时导航\n- EfficientViT: 兼顾精度和速度\n\n### 实验计划\n用 ViT-B/16 + DINOv2 权重替代 ResNet-18，预期 +3-5% SR',
    tags: ['ViT', 'Transformer', '导航', '论文'],
    created_at: now - 12 * DAY,
    source_session_id: 14,
  },
  {
    id: 10,
    title: '会议纪要：中期汇报准备',
    type: 'meeting_note',
    content: '## 组会纪要 - 2026.03.12\n\n### 中期汇报内容规划\n1. **研究进展**：PPO 导航基线 81% SR\n2. **sim2real 方案**：三层 DR 设计\n3. **下一步计划**：ViT 编码器 + DD-PPO\n\n### 导师反馈\n- 建议加入 object navigation 任务\n- sim2real 实验要有真实机器人数据\n- 论文投稿目标：IROS 2026\n\n### 时间节点\n- 3月底：完成 DR 实验\n- 4月中：完成 ViT 实验\n- 5月初：论文初稿\n- 5月15日：IROS 截稿',
    tags: ['组会', '中期汇报', '计划'],
    created_at: now - 7 * DAY,
    source_session_id: 6,
  },
]

// 行为模式 - 带学习演化过程
export const mockPatterns: BehaviorPattern[] = [
  {
    id: 1,
    name: '实验前先写测试',
    category: 'coding',
    description: '在实现新的 RL 算法或策略网络前，先编写评估测试用例，确保实验可复现',
    confidence: 92,
    evidence_count: 47,
    learned_from: '分析 30 天内 pytest 调用和代码提交顺序',
    rule: '新实验代码必须先有对应的 test_*.py 文件',
    created_at: now - 25 * DAY,
    status: 'exportable',
    evolution: [
      { date: '03-01', confidence: 15, event_description: '首次观察到 test 文件先于实现文件创建' },
      { date: '03-03', confidence: 22, event_description: '第二次观察到相同模式' },
      { date: '03-05', confidence: 35, event_description: '连续 3 天遵循 test-first 模式' },
      { date: '03-07', confidence: 42, event_description: '在 nav_planner 模块中再次确认' },
      { date: '03-10', confidence: 58, event_description: 'OpenClaw TDD 引导会话确认了该模式' },
      { date: '03-12', confidence: 65, event_description: '开始在新项目中主动使用' },
      { date: '03-14', confidence: 75, event_description: '在 grasp-policy 项目中也观察到相同模式' },
      { date: '03-16', confidence: 82, event_description: 'sim2real 项目也遵循该模式' },
      { date: '03-17', confidence: 87, event_description: '跨项目一致性验证通过' },
      { date: '03-19', confidence: 92, event_description: '30 天内 47 次证据，模式稳定' },
    ],
    rules: [
      { id: 1, name: '测试文件命名', description: '测试文件必须以 test_ 开头', trigger: '创建新的 .py 文件', action: '检查是否存在对应的 test_ 文件', example: 'test_ppo_agent.py 对应 ppo_agent.py' },
      { id: 2, name: '测试先行', description: '测试文件的创建时间必须早于实现文件', trigger: 'git commit 包含新模块', action: '验证 test 文件 commit 时间更早', example: 'test_reward.py 在 reward.py 之前提交' },
      { id: 3, name: '覆盖率检查', description: '新模块的测试覆盖率不低于 80%', trigger: 'pytest 执行完成', action: '检查 coverage 报告', example: 'pytest --cov=nav_planner --cov-fail-under=80' },
    ],
    executions: [
      { id: 1, pattern_id: 1, timestamp: now - 2 * DAY, trigger_event: '创建 reward_shaping.py', action_taken: '检测到 test_reward_shaping.py 已存在', result: 'success' },
      { id: 2, pattern_id: 1, timestamp: now - 4 * DAY, trigger_event: '创建 path_smoother.py', action_taken: 'TDD 引导先创建测试', result: 'success' },
      { id: 3, pattern_id: 1, timestamp: now - 6 * DAY, trigger_event: '创建 visual_encoder.py', action_taken: '未检测到测试文件，提醒用户', result: 'modified' },
    ],
    applicable_scenarios: ['新 RL 算法实现', '策略网络开发', '工具函数编写', '数据处理模块'],
    slug: 'test-before-experiment',
    trigger: { when: '创建新的实验代码文件', globs: ['**/train*.py', '**/agent*.py'], event: 'file_create', context: ['RL 训练', '策略网络'] },
    body: '## 实验前先写测试\n\n在实现新的 RL 算法前，先编写评估测试用例。',
    source: 'auto',
    confidence_level: 'very_high',
    learned_from_data: [{ context: 'pytest 调用分析', insight: '47 次观察到 test 文件先于实现文件创建', confidence: 92 }],
  },
  {
    id: 2,
    name: 'Conventional Commits 规范',
    category: 'git',
    description: '所有 Git 提交使用 feat/fix/refactor/docs/test 前缀，保持提交历史清晰',
    confidence: 88,
    evidence_count: 156,
    learned_from: '分析 30 天内 Git 提交记录',
    rule: '提交信息必须以 feat:|fix:|refactor:|docs:|test:|chore: 开头',
    created_at: now - 28 * DAY,
    status: 'exportable',
    evolution: [
      { date: '02-20', confidence: 20, event_description: '发现大部分提交遵循 conventional commits' },
      { date: '02-23', confidence: 30, event_description: '统计 30 次提交，25 次符合规范' },
      { date: '02-25', confidence: 45, event_description: '统计 50 次提交，42 次符合规范' },
      { date: '02-28', confidence: 55, event_description: '开始在所有项目中使用' },
      { date: '03-02', confidence: 65, event_description: '100 次提交中 89 次符合' },
      { date: '03-06', confidence: 72, event_description: '不符合的主要是 WIP 类型' },
      { date: '03-10', confidence: 80, event_description: '不符合的提交主要是 WIP 类型' },
      { date: '03-14', confidence: 85, event_description: '开始自动提示不规范的提交' },
      { date: '03-18', confidence: 88, event_description: '156 次提交验证，模式确认' },
    ],
    rules: [
      { id: 4, name: '前缀检查', description: '提交信息必须以规范前缀开头', trigger: 'git commit', action: '检查 commit message 格式', example: 'feat: add PPO reward shaping' },
      { id: 5, name: '范围标注', description: '建议在前缀后加范围', trigger: 'git commit', action: '提示添加 scope', example: 'fix(nav): resolve tf2 timeout' },
      { id: 6, name: 'WIP 提醒', description: 'WIP 提交需要在合并前 squash', trigger: 'git merge', action: '检查是否有 WIP 提交', example: 'WIP 提交应在 merge 前整理' },
    ],
    executions: [
      { id: 4, pattern_id: 2, timestamp: now - DAY, trigger_event: 'git commit "add new feature"', action_taken: '提示缺少前缀，建议改为 feat:', result: 'modified' },
      { id: 5, pattern_id: 2, timestamp: now - 2 * DAY, trigger_event: 'git commit "feat: add DR module"', action_taken: '格式正确，通过', result: 'success' },
    ],
    applicable_scenarios: ['所有 Git 项目', '团队协作', '开源贡献', 'CI/CD 集成'],
    slug: 'conventional-commits', trigger: 'git commit 执行时', body: null, source: 'auto', confidence_level: 'high', learned_from_data: null,
  },
  {
    id: 3,
    name: '实验结果即时记录',
    category: 'collaboration',
    description: '每次实验完成后立即通过 OpenClaw 生成总结并写入知识库，不拖延',
    confidence: 78,
    evidence_count: 23,
    learned_from: '分析 OpenClaw 实验总结会话和知识库写入时间',
    rule: '实验完成后 30 分钟内必须生成总结文档',
    created_at: now - 20 * DAY,
    status: 'confirmed',
    evolution: [
      { date: '03-01', confidence: 10, event_description: '首次观察到实验后立即调用 OpenClaw 总结' },
      { date: '03-04', confidence: 20, event_description: '第二次观察到相同行为' },
      { date: '03-06', confidence: 30, event_description: '5 次实验中 3 次在 30 分钟内总结' },
      { date: '03-09', confidence: 42, event_description: '开始形成习惯' },
      { date: '03-12', confidence: 55, event_description: '知识库文档创建时间与实验结束时间高度相关' },
      { date: '03-14', confidence: 63, event_description: '连续 5 天保持即时记录' },
      { date: '03-16', confidence: 70, event_description: '连续一周保持即时记录习惯' },
      { date: '03-19', confidence: 78, event_description: '23 次证据，模式基本确认' },
    ],
    rules: [
      { id: 7, name: '时间窗口', description: '实验结束后 30 分钟内生成总结', trigger: '训练脚本执行完成', action: '提醒用户记录实验结果', example: 'PPO 训练完成 → 提醒生成总结' },
      { id: 8, name: '模板使用', description: '使用标准实验总结模板', trigger: 'OpenClaw 总结会话', action: '自动填充实验参数', example: '自动提取 lr, epochs, metrics' },
    ],
    executions: [
      { id: 6, pattern_id: 3, timestamp: now - DAY, trigger_event: 'PPO-v2 训练完成', action_taken: '30 分钟内生成实验总结', result: 'success' },
      { id: 7, pattern_id: 3, timestamp: now - 3 * DAY, trigger_event: 'SAC 训练完成', action_taken: '超过 30 分钟才记录', result: 'modified' },
    ],
    applicable_scenarios: ['RL 训练实验', '消融实验', '对比实验', '超参搜索'],
    slug: 'instant-experiment-log', trigger: '训练脚本执行完成', body: null, source: 'auto', confidence_level: 'high', learned_from_data: null,
  },
  {
    id: 4,
    name: 'AI 辅助代码审查',
    category: 'review',
    description: '在合并分支前通过 OpenClaw 进行代码审查，重点关注算法正确性和性能',
    confidence: 83,
    evidence_count: 34,
    learned_from: '分析 OpenClaw code-review 调用与 Git merge 的时间关系',
    rule: '合并前必须完成至少一次 OpenClaw 代码审查',
    created_at: now - 22 * DAY,
    status: 'exportable',
    evolution: [
      { date: '02-26', confidence: 18, event_description: '首次观察到 merge 前调用 code-review' },
      { date: '03-01', confidence: 28, event_description: '第三次观察到相同模式' },
      { date: '03-03', confidence: 40, event_description: '8 次 merge 中 6 次有 review' },
      { date: '03-06', confidence: 50, event_description: '开始主动请求 review' },
      { date: '03-08', confidence: 60, event_description: '开始在 grasp-policy 项目中也使用' },
      { date: '03-11', confidence: 68, event_description: 'review 发现了 2 个关键 bug' },
      { date: '03-14', confidence: 75, event_description: '跨项目验证，review 覆盖率 85%' },
      { date: '03-17', confidence: 80, event_description: '团队成员也开始采用' },
      { date: '03-19', confidence: 83, event_description: '34 次证据，模式稳定' },
    ],
    rules: [
      { id: 9, name: 'merge 前审查', description: '合并分支前必须有 review 记录', trigger: 'git merge 或 PR 创建', action: '检查是否有对应的 review 会话', example: 'merge feat/ppo-reward 前需要 review' },
      { id: 10, name: '关注点', description: '审查重点：算法正确性、性能、边界条件', trigger: 'OpenClaw code-review', action: '自动生成审查清单', example: '检查 reward 计算、梯度裁剪、OOM 风险' },
    ],
    executions: [
      { id: 8, pattern_id: 4, timestamp: now - 3 * DAY, trigger_event: 'merge feat/visual-dr', action_taken: 'OpenClaw review 发现纹理随机化范围问题', result: 'success' },
      { id: 9, pattern_id: 4, timestamp: now - 5 * DAY, trigger_event: 'merge fix/tf2-transform', action_taken: '快速修复，跳过了 review', result: 'skipped' },
    ],
    applicable_scenarios: ['分支合并', 'PR 审查', '算法实现验证', '性能关键代码'],
    slug: 'ai-code-review', trigger: 'git merge 或 PR 创建', body: null, source: 'auto', confidence_level: 'high', learned_from_data: null,
  },
  {
    id: 5,
    name: '训练前环境检查',
    category: 'devops',
    description: '启动 RL 训练前先检查 GPU 状态、磁盘空间和依赖版本，避免训练中断',
    confidence: 65,
    evidence_count: 18,
    learned_from: '分析 nvidia-smi 和 train.py 的调用时序',
    rule: '训练脚本启动前必须执行环境检查脚本',
    created_at: now - 15 * DAY,
    status: 'confirmed',
    evolution: [
      { date: '03-05', confidence: 12, event_description: '观察到训练前经常调用 nvidia-smi' },
      { date: '03-07', confidence: 20, event_description: '发现还会检查磁盘空间' },
      { date: '03-10', confidence: 30, event_description: '发现还会检查磁盘空间' },
      { date: '03-12', confidence: 40, event_description: '一次 OOM 后检查频率增加' },
      { date: '03-14', confidence: 48, event_description: '一次训练因 OOM 中断后，检查频率增加' },
      { date: '03-16', confidence: 55, event_description: '开始编写自动检查脚本' },
      { date: '03-18', confidence: 65, event_description: '18 次证据，模式逐渐稳定' },
    ],
    rules: [
      { id: 11, name: 'GPU 检查', description: '检查 GPU 显存是否充足', trigger: '执行 train.py', action: '运行 nvidia-smi 检查', example: 'nvidia-smi 确认显存 > 8GB 可用' },
      { id: 12, name: '磁盘检查', description: '检查磁盘空间是否充足', trigger: '执行 train.py', action: '检查 /data 分区剩余空间', example: 'df -h 确认 > 50GB 可用' },
      { id: 13, name: '依赖版本', description: '确认关键依赖版本一致', trigger: '执行 train.py', action: '检查 PyTorch/CUDA 版本', example: 'python -c "import torch; print(torch.__version__)"' },
    ],
    executions: [
      { id: 10, pattern_id: 5, timestamp: now - DAY, trigger_event: '启动 PPO 训练', action_taken: 'GPU 检查通过，开始训练', result: 'success' },
      { id: 11, pattern_id: 5, timestamp: now - 3 * DAY, trigger_event: '启动 SAC 训练', action_taken: '发现 GPU 被占用，等待释放', result: 'modified' },
    ],
    applicable_scenarios: ['RL 训练', '模型评估', '大规模实验', '分布式训练'],
    slug: 'pre-train-env-check', trigger: null, body: null, source: 'auto', confidence_level: 'medium', learned_from_data: null,
  },
  {
    id: 6,
    name: '论文驱动开发',
    category: 'coding',
    description: '新功能开发前先阅读相关论文，通过 OpenClaw 讨论后再编码实现',
    confidence: 52,
    evidence_count: 11,
    learned_from: '分析 OpenClaw 论文讨论会话与后续代码提交的关联',
    rule: '新算法实现前应有对应的论文分析会话',
    created_at: now - 10 * DAY,
    status: 'learning',
    evolution: [
      { date: '03-10', confidence: 15, event_description: '观察到 PointNav 论文讨论后开始编码' },
      { date: '03-12', confidence: 25, event_description: 'sim2real DR 也是先看论文' },
      { date: '03-14', confidence: 32, event_description: 'sim2real 方案也是先讨论论文再实现' },
      { date: '03-16', confidence: 42, event_description: 'ViT 导航也遵循该模式' },
      { date: '03-18', confidence: 52, event_description: '11 次证据，模式仍在学习中' },
    ],
    rules: [
      { id: 14, name: '论文先行', description: '新算法实现前需要有论文分析', trigger: '创建新的算法模块', action: '检查是否有对应的论文讨论会话', example: 'PPO reward shaping 前先分析 PointNav 论文' },
    ],
    executions: [
      { id: 12, pattern_id: 6, timestamp: now - 2 * DAY, trigger_event: '开始实现 ViT 编码器', action_taken: '检测到已有 ViT 论文讨论会话', result: 'success' },
    ],
    applicable_scenarios: ['新算法实现', '方案设计', '技术选型', '论文复现'],
    slug: 'paper-first-design', trigger: null, body: null, source: 'auto', confidence_level: 'medium', learned_from_data: null,
  },
  {
    id: 7,
    name: 'Conda 环境隔离',
    category: 'devops',
    description: '每个项目使用独立的 Conda 环境，避免依赖冲突',
    confidence: 75,
    evidence_count: 28,
    learned_from: '分析 conda activate 调用和项目切换的关联',
    rule: '切换项目时必须激活对应的 Conda 环境',
    created_at: now - 20 * DAY,
    status: 'confirmed',
    evolution: [
      { date: '03-01', confidence: 15, event_description: '观察到频繁使用 conda activate' },
      { date: '03-05', confidence: 30, event_description: '每个项目对应不同环境' },
      { date: '03-08', confidence: 45, event_description: '一次依赖冲突后更加严格' },
      { date: '03-12', confidence: 58, event_description: '开始使用 environment.yml 管理' },
      { date: '03-15', confidence: 68, event_description: '所有项目都有 environment.yml' },
      { date: '03-18', confidence: 75, event_description: '28 次证据，模式确认' },
    ],
    rules: [
      { id: 15, name: '环境切换', description: '切换项目时激活对应环境', trigger: 'cd 到项目目录', action: '自动 conda activate', example: 'cd embodied-nav → conda activate habitat' },
      { id: 16, name: '环境文件', description: '每个项目必须有 environment.yml', trigger: '创建新项目', action: '生成 environment.yml', example: 'conda env export > environment.yml' },
    ],
    executions: [
      { id: 13, pattern_id: 7, timestamp: now - DAY, trigger_event: '切换到 ros2-workspace', action_taken: '自动激活 ros2 环境', result: 'success' },
    ],
    applicable_scenarios: ['多项目开发', 'Python 项目', 'ML 实验', 'ROS2 开发'],
    slug: 'conda-env-isolation', trigger: null, body: null, source: 'auto', confidence_level: 'high', learned_from_data: null,
  },
  {
    id: 8,
    name: '分支命名规范',
    category: 'git',
    description: '分支名使用 feat/fix/exp 前缀加简短描述，保持仓库整洁',
    confidence: 70,
    evidence_count: 42,
    learned_from: '分析 Git 分支创建和命名模式',
    rule: '分支名必须以 feat/|fix/|exp/|refactor/ 开头',
    created_at: now - 18 * DAY,
    status: 'confirmed',
    evolution: [
      { date: '03-02', confidence: 18, event_description: '发现大部分分支遵循命名规范' },
      { date: '03-06', confidence: 32, event_description: '统计 20 个分支，16 个符合' },
      { date: '03-10', confidence: 48, event_description: '新增 exp/ 前缀用于实验分支' },
      { date: '03-14', confidence: 60, event_description: '团队开始统一使用' },
      { date: '03-18', confidence: 70, event_description: '42 次证据，模式确认' },
    ],
    rules: [
      { id: 17, name: '前缀规范', description: '分支名必须有规范前缀', trigger: 'git checkout -b', action: '检查分支名格式', example: 'feat/ppo-reward, exp/domain-rand' },
    ],
    executions: [
      { id: 14, pattern_id: 8, timestamp: now - 2 * DAY, trigger_event: 'git checkout -b new-feature', action_taken: '提示添加前缀', result: 'modified' },
    ],
    applicable_scenarios: ['所有 Git 项目', '团队协作', '实验管理'],
    slug: 'branch-naming', trigger: null, body: null, source: 'auto', confidence_level: 'medium', learned_from_data: null,
  },
  {
    id: 9,
    name: '实验超参记录',
    category: 'collaboration',
    description: '每次实验都完整记录超参数配置，使用 YAML 配置文件管理',
    confidence: 60,
    evidence_count: 15,
    learned_from: '分析实验配置文件和训练脚本参数',
    rule: '训练脚本必须从 YAML 配置文件读取超参数',
    created_at: now - 12 * DAY,
    status: 'learning',
    evolution: [
      { date: '03-08', confidence: 12, event_description: '观察到开始使用 config.yaml' },
      { date: '03-11', confidence: 25, event_description: '多个实验使用配置文件' },
      { date: '03-14', confidence: 40, event_description: '开始用 hydra 管理配置' },
      { date: '03-17', confidence: 52, event_description: '配置文件覆盖率提升' },
      { date: '03-19', confidence: 60, event_description: '15 次证据，模式学习中' },
    ],
    rules: [
      { id: 18, name: '配置文件', description: '实验参数必须在配置文件中', trigger: '启动训练', action: '检查是否使用配置文件', example: 'python train.py --config configs/ppo_v2.yaml' },
    ],
    executions: [
      { id: 15, pattern_id: 9, timestamp: now - DAY, trigger_event: '启动新实验', action_taken: '检测到使用命令行参数，建议改用配置文件', result: 'modified' },
    ],
    applicable_scenarios: ['RL 训练', '超参搜索', '消融实验', '可复现研究'],
    slug: 'experiment-config-yaml', trigger: null, body: null, source: 'auto', confidence_level: 'medium', learned_from_data: null,
  },
  {
    id: 10,
    name: '代码提交前 lint 检查',
    category: 'coding',
    description: '提交代码前运行 linter 和 type checker，确保代码质量',
    confidence: 45,
    evidence_count: 9,
    learned_from: '分析 flake8/mypy 调用与 git commit 的时序关系',
    rule: '提交前必须通过 flake8 和 mypy 检查',
    created_at: now - 8 * DAY,
    status: 'learning',
    evolution: [
      { date: '03-12', confidence: 10, event_description: '首次观察到提交前运行 flake8' },
      { date: '03-15', confidence: 22, event_description: '开始加入 mypy 检查' },
      { date: '03-17', confidence: 35, event_description: '在 pre-commit hook 中配置' },
      { date: '03-19', confidence: 45, event_description: '9 次证据，模式学习中' },
    ],
    rules: [
      { id: 19, name: 'lint 检查', description: '提交前运行 flake8', trigger: 'git commit', action: '执行 flake8 检查', example: 'flake8 src/ --max-line-length=120' },
    ],
    executions: [
      { id: 16, pattern_id: 10, timestamp: now - DAY, trigger_event: 'git commit', action_taken: 'flake8 发现 2 个问题，已修复', result: 'success' },
    ],
    applicable_scenarios: ['Python 项目', '代码提交', 'CI/CD'],
    slug: 'lint-before-commit', trigger: null, body: null, source: 'auto', confidence_level: 'medium', learned_from_data: null,
  },
  {
    id: 99,
    name: '代码开发与Git提交规范 (完整工作流)',
    category: 'git',
    description: 'ShrimpFlow 从开发者日常编码中学习到的完整行为规范：包括仓库初始化、分支管理、PR 驱动合并、迭代开发循环、Conventional Commits、代码审查流程。该模式已被验证可自主驱动完整项目开发。',
    confidence: 96,
    evidence_count: 312,
    learned_from: '分析 60 天内全量 Git 操作、代码编辑、PR 流程和 OpenClaw 协作记录',
    rule: '遵循完整的代码开发生命周期：初始化 → 分支开发 → 测试 → PR 审查 → 合并 → 发布',
    created_at: now - 60 * DAY,
    status: 'exportable',
    evolution: [
      { date: '01-20', confidence: 8, event_description: '首次观察到仓库初始化遵循固定模板' },
      { date: '01-25', confidence: 15, event_description: '发现分支命名遵循 feat/fix/exp 前缀' },
      { date: '02-01', confidence: 25, event_description: '确认 PR 驱动的合并工作流' },
      { date: '02-05', confidence: 35, event_description: '迭代开发循环模式初步成型' },
      { date: '02-10', confidence: 45, event_description: '跨项目验证：embodied-nav 和 grasp-policy 一致' },
      { date: '02-15', confidence: 55, event_description: 'Conventional Commits 规范与分支策略关联确认' },
      { date: '02-20', confidence: 65, event_description: '代码审查流程模式稳定' },
      { date: '02-25', confidence: 72, event_description: 'sim2real-transfer 项目完整验证' },
      { date: '03-01', confidence: 80, event_description: '200+ 次证据累积，模式高度稳定' },
      { date: '03-05', confidence: 85, event_description: '自主执行验证：成功驱动 OmniStack 项目开发' },
      { date: '03-10', confidence: 90, event_description: '完整项目生命周期验证通过' },
      { date: '03-15', confidence: 96, event_description: '312 条证据，模式确认可导出' },
    ],
    rules: [
      { id: 100, name: '仓库初始化模板', description: '新项目必须包含 README、.gitignore、LICENSE、CI 配置', trigger: '创建新仓库', action: '按模板初始化项目结构', example: 'git init + 模板文件生成' },
      { id: 101, name: '分支命名规范', description: '功能分支 feat/、修复分支 fix/、实验分支 exp/', trigger: '创建新分支', action: '检查分支名前缀', example: 'feat/ppo-reward, fix/tf2-transform, exp/domain-rand' },
      { id: 102, name: 'PR 驱动合并', description: '所有代码变更必须通过 PR 合并，禁止直接 push main', trigger: '代码准备合并', action: '创建 PR 并请求审查', example: 'gh pr create --title "feat: add reward shaping"' },
      { id: 103, name: '迭代开发循环', description: '每个迭代包含：编码 → 测试 → 审查 → 合并 → 部署', trigger: '开始新迭代', action: '按循环步骤执行', example: '迭代 1-4 完成后合并 PR' },
      { id: 104, name: 'Commit Message 规范', description: '使用 feat/fix/refactor/docs/test/chore 前缀', trigger: 'git commit', action: '验证 commit message 格式', example: 'feat: implement SAC algorithm for continuous control' },
    ],
    executions: [
      { id: 100, pattern_id: 99, timestamp: now - 1 * DAY, trigger_event: '自主开发 OmniStack 项目', action_taken: '完整执行仓库初始化 → 迭代开发 → PR 合并流程', result: 'success' },
      { id: 101, pattern_id: 99, timestamp: now - 3 * DAY, trigger_event: '新建 sim2real-transfer 分支', action_taken: '自动使用 exp/ 前缀命名', result: 'success' },
      { id: 102, pattern_id: 99, timestamp: now - 5 * DAY, trigger_event: 'PR #42 代码审查', action_taken: '按审查流程完成 review 并合并', result: 'success' },
    ],
    applicable_scenarios: ['新项目启动', '团队协作开发', '开源项目管理', 'CI/CD 流水线', '代码质量保障'],
    slug: 'full-dev-lifecycle', trigger: '创建新项目', body: null, source: 'auto', confidence_level: 'very_high', learned_from_data: null,
  },
]

// 团队 Workflow
export const mockWorkflows: TeamWorkflow[] = [
  {
    id: 1,
    name: '具身智能实验规范',
    description: '包含实验前测试、结果即时记录和代码审查流程，适用于 RL 实验开发',
    patterns: [1, 3, 4],
    target_team: '具身智能实验室',
    status: 'active',
    created_at: now - 5 * DAY,
    steps: [
      { pattern: 'test-before-experiment', when: '开始新实验实现', gate: '测试文件已创建且可运行' },
      { inline: '实现实验代码，确保测试通过', when: '测试框架就绪' },
      { pattern: 'instant-experiment-log', when: '训练脚本执行完成', gate: '实验总结已写入知识库' },
      { pattern: 'ai-code-review', when: '准备合并分支', gate: 'review 无 critical 问题' },
    ],
  },
  {
    id: 2,
    name: 'ROS2 开发流程',
    description: '训练前环境检查和 Git 规范，确保机器人软件开发质量',
    patterns: [2, 5, 7],
    target_team: '机器人开发组',
    status: 'distributed',
    created_at: now - 3 * DAY,
    steps: [
      { pattern: 'conventional-commits', when: 'git commit' },
      { inline: 'colcon build 编译验证', when: '代码修改完成' },
    ],
  },
  {
    id: 3,
    name: '新人入职研究指南',
    description: '整合所有核心研究模式，帮助新同学快速融入实验室研究节奏',
    patterns: [1, 2, 3, 4, 6],
    target_team: '全体成员',
    status: 'draft',
    created_at: now - DAY,
    steps: [
      { inline: '阅读实验室代码规范文档', when: '入职第一天' },
      { pattern: 'conventional-commits', when: '首次提交代码' },
      { pattern: 'test-before-experiment', when: '首次编写实验代码' },
    ],
  },
  {
    id: 4,
    name: '论文写作工作流',
    description: '从实验到论文的完整流程：实验记录 → 数据整理 → 论文撰写 → 代码审查',
    patterns: [3, 6, 9],
    target_team: '研究生',
    status: 'active',
    created_at: now - 4 * DAY,
    steps: [
      { pattern: 'instant-experiment-log', when: '实验完成' },
      { inline: '整理实验数据，生成对比表格和图表', when: '所有实验完成' },
      { parallel: [
        { inline: '同行内部审阅', when: '初稿完成' },
        { inline: 'AI 辅助语法检查', when: '初稿完成' },
      ] },
    ],
  },
  {
    id: 5,
    name: 'AI 项目启动模板',
    description: '新 AI 项目的标准启动流程：环境隔离 → 分支规范 → TDD → 代码审查',
    patterns: [1, 2, 7, 8, 10],
    target_team: 'AI 开发组',
    status: 'draft',
    created_at: now - 2 * DAY,
    steps: [
      { inline: '创建独立 conda 环境', when: '项目启动' },
      { pattern: 'conventional-commits', when: '初始化 Git 仓库' },
      { pattern: 'test-before-experiment', when: '开始编码' },
    ],
  },
  {
    id: 6,
    name: '日常开发规范',
    description: '日常编码的基本规范：Git 规范 + lint 检查 + 环境管理',
    patterns: [2, 7, 8, 10],
    target_team: '全体成员',
    status: 'distributed',
    created_at: now - 6 * DAY,
    steps: [
      { pattern: 'conventional-commits', when: 'git commit' },
      { inline: 'lint 检查通过', when: '代码修改完成', gate: 'pylint score >= 8.0' },
    ],
  },
]

// 社区分享用户
export const mockProfiles: SharedProfile[] = [
  { id: 1, username: 'Peter Steinberger', avatar: 'PS', title: 'iOS 架构大师', bio: 'PSPDFKit 创始人，20年 iOS 开发经验', followers: 12400, patterns_count: 24 },
  { id: 2, username: 'Andrej Karpathy', avatar: 'AK', title: 'AI 研究员', bio: '前 Tesla AI 总监，深度学习先驱', followers: 89200, patterns_count: 18 },
  { id: 3, username: 'Linus Torvalds', avatar: 'LT', title: 'Git 之父', bio: 'Linux 和 Git 创始人', followers: 156000, patterns_count: 12 },
  { id: 4, username: 'Pieter Abbeel', avatar: 'PA', title: '机器人学教授', bio: 'UC Berkeley 教授，Covariant 联合创始人', followers: 34500, patterns_count: 15 },
  { id: 5, username: 'Chelsea Finn', avatar: 'CF', title: '元学习专家', bio: 'Stanford 教授，MAML 作者', followers: 28700, patterns_count: 11 },
  { id: 6, username: 'Yann LeCun', avatar: 'YL', title: 'AI 先驱', bio: 'Meta AI 首席科学家，图灵奖得主', followers: 210000, patterns_count: 20 },
  { id: 7, username: 'Sergey Levine', avatar: 'SL', title: 'RL 专家', bio: 'UC Berkeley 教授，机器人 RL 先驱', followers: 42100, patterns_count: 16 },
  { id: 8, username: 'Fei-Fei Li', avatar: 'FL', title: '计算机视觉专家', bio: 'Stanford HAI 联合主任，ImageNet 创始人', followers: 67800, patterns_count: 14 },
]

// 简化的模式（用于社区分享包）
const sp = (id: number, name: string, cat: BehaviorPattern['category'], desc: string, conf: number, rule: string): BehaviorPattern => ({
  id, name, category: cat, description: desc, confidence: conf, evidence_count: Math.floor(conf * 0.5),
  learned_from: '社区分享', rule, created_at: now - 30 * DAY, status: 'exportable' as const,
  evolution: [{ date: '01-01', confidence: conf, event_description: '导入时已确认' }],
  rules: [], executions: [], applicable_scenarios: [],
  slug: null, trigger: null, body: null, source: 'imported', confidence_level: null, learned_from_data: null,
})

// 社区分享模式包
export const mockSharedPacks: SharedPatternPack[] = [
  {
    id: 1,
    author: mockProfiles[0],
    name: "Peter's iOS Architecture Workflow",
    description: '20年 iOS 开发经验总结的架构模式，包含 MVVM、依赖注入、模块化设计等最佳实践',
    category: 'coding',
    downloads: 8420,
    stars: 2150,
    tags: ['iOS', 'Swift', '架构', 'MVVM'],
    created_at: now - 20 * DAY,
    patterns: [
      sp(101, 'MVVM 严格分层', 'coding', 'View 层不直接访问 Model，必须通过 ViewModel', 95, 'View 中禁止 import Model 层'),
      sp(102, '依赖注入优先', 'coding', '所有依赖通过构造函数注入，不使用单例', 92, '禁止在类内部直接实例化依赖'),
      sp(103, 'Protocol 驱动设计', 'coding', '核心接口先定义 Protocol，再实现具体类', 88, '新模块必须先有 Protocol 定义'),
    ],
  },
  {
    id: 2,
    author: mockProfiles[1],
    name: 'ML Research Best Practices',
    description: '深度学习研究的最佳实践，从实验设计到论文写作的完整工作流',
    category: 'coding',
    downloads: 15600,
    stars: 4820,
    tags: ['ML', '深度学习', '研究', '实验'],
    created_at: now - 15 * DAY,
    patterns: [
      sp(201, '实验可复现性', 'coding', '所有实验必须固定随机种子，记录完整环境信息', 96, '训练脚本必须设置 seed 并记录到日志'),
      sp(202, '渐进式实验', 'coding', '从最简单的 baseline 开始，逐步增加复杂度', 94, '新想法先在小数据集上验证'),
      sp(203, '消融实验规范', 'collaboration', '每个创新点必须有对应的消融实验', 91, '论文提交前必须完成所有消融实验'),
    ],
  },
  {
    id: 3,
    author: mockProfiles[2],
    name: 'Clean Git Workflow',
    description: 'Git 工作流的黄金标准，包含分支策略、提交规范和代码审查流程',
    category: 'git',
    downloads: 32100,
    stars: 9870,
    tags: ['Git', '工作流', '分支', '规范'],
    created_at: now - 25 * DAY,
    patterns: [
      sp(301, '原子提交', 'git', '每个提交只做一件事，保持提交历史清晰', 98, '单个提交不超过 300 行改动'),
      sp(302, '分支保护', 'git', 'main 分支禁止直接推送，必须通过 PR', 97, 'main 分支设置 branch protection'),
      sp(303, 'Rebase 优先', 'git', '合并前先 rebase，保持线性历史', 90, 'merge 前执行 git rebase main'),
    ],
  },
  {
    id: 4,
    author: mockProfiles[3],
    name: 'Robotics RL Development',
    description: '机器人强化学习开发的完整工作流，从仿真到真实部署',
    category: 'coding',
    downloads: 6780,
    stars: 1920,
    tags: ['机器人', 'RL', 'sim2real', 'ROS'],
    created_at: now - 18 * DAY,
    patterns: [
      sp(401, 'Sim-first 开发', 'coding', '所有算法先在仿真中验证，再部署到真实机器人', 93, '真实部署前仿真 success rate > 90%'),
      sp(402, 'Safety-aware RL', 'coding', '训练时加入安全约束，避免危险动作', 90, 'reward 中必须包含安全惩罚项'),
      sp(403, 'DR 标准化', 'devops', 'Domain Randomization 参数必须可配置', 85, 'DR 参数通过 YAML 配置文件管理'),
    ],
  },
  {
    id: 5,
    author: mockProfiles[4],
    name: 'Meta-Learning Research Flow',
    description: '元学习研究的标准流程，包含 few-shot 实验设计和评估规范',
    category: 'coding',
    downloads: 4320,
    stars: 1450,
    tags: ['元学习', 'few-shot', 'MAML', '研究'],
    created_at: now - 12 * DAY,
    patterns: [
      sp(501, 'N-way K-shot 标准评估', 'coding', '使用标准的 N-way K-shot 评估协议', 95, '评估必须报告 5-way 1-shot 和 5-way 5-shot'),
      sp(502, '置信区间报告', 'collaboration', '所有实验结果必须报告 95% 置信区间', 92, '至少运行 600 个 episode 计算置信区间'),
    ],
  },
  {
    id: 6,
    author: mockProfiles[5],
    name: 'Self-Supervised Learning Patterns',
    description: '自监督学习的研究模式，包含对比学习、掩码预测等方法论',
    category: 'coding',
    downloads: 21400,
    stars: 6530,
    tags: ['自监督', '对比学习', 'MAE', 'DINO'],
    created_at: now - 22 * DAY,
    patterns: [
      sp(601, '数据增强一致性', 'coding', '对比学习中两个 view 的增强策略必须一致', 94, '增强管道必须对称设计'),
      sp(602, '线性探测评估', 'coding', '预训练模型必须用线性探测评估特征质量', 96, '冻结 backbone，只训练线性分类头'),
      sp(603, '多尺度评估', 'review', '在多个下游任务上评估泛化能力', 88, '至少在 3 个不同任务上评估'),
    ],
  },
  {
    id: 7,
    author: mockProfiles[6],
    name: 'Robot RL from Scratch',
    description: '从零开始的机器人 RL 开发指南，覆盖环境搭建到策略部署',
    category: 'devops',
    downloads: 9870,
    stars: 3210,
    tags: ['机器人', 'RL', '教程', '部署'],
    created_at: now - 16 * DAY,
    patterns: [
      sp(701, '环境标准化', 'devops', '使用 Gym 接口封装所有环境', 95, '所有环境必须实现 reset/step/render'),
      sp(702, '奖励工程', 'coding', '奖励函数必须可配置，支持消融', 90, '奖励各项权重通过配置文件管理'),
      sp(703, '训练监控', 'devops', '训练过程必须有实时监控', 88, '使用 TensorBoard/W&B 记录所有指标'),
    ],
  },
  {
    id: 8,
    author: mockProfiles[7],
    name: 'Computer Vision Research Standards',
    description: '计算机视觉研究的标准规范，从数据集准备到模型评估',
    category: 'coding',
    downloads: 18900,
    stars: 5670,
    tags: ['CV', '视觉', '数据集', '评估'],
    created_at: now - 19 * DAY,
    patterns: [
      sp(801, '数据集划分规范', 'coding', 'train/val/test 严格分离，无数据泄漏', 97, '划分后验证无重叠样本'),
      sp(802, '多指标评估', 'review', '不只看 accuracy，还要看 precision/recall/F1', 93, '评估报告必须包含混淆矩阵'),
      sp(803, '可视化验证', 'review', '模型预测结果必须可视化检查', 90, '每次评估生成预测可视化样本'),
    ],
  },
]

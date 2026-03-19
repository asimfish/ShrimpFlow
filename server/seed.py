import json
import time
import random
from collections import defaultdict
from datetime import datetime, timezone

from db import SessionLocal
from models.event import DevEvent
from models.skill import Skill
from models.pattern import BehaviorPattern
from models.openclaw import OpenClawSession, OpenClawDocument
from models.digest import DailySummary
from models.workflow import TeamWorkflow
from models.community import SharedProfile, SharedPatternPack

# 时间常量
NOW = int(time.time())
DAY = 86400
HOUR = 3600

# 项目和分支
PROJECTS = ['embodied-nav', 'grasp-policy', 'ros2-workspace', 'paper-reproduce', 'sim2real-transfer']
BRANCHES = ['main', 'feat/ppo-reward', 'fix/tf2-transform', 'dev', 'feat/habitat-env', 'exp/domain-rand']

# action 模板
OPENCLAW_ACTIONS = [
    {'action': 'openclaw chat: "帮我分析 PointNav 论文的核心创新点"', 'semantic': '请求 OpenClaw 分析导航论文', 'tags': ['openclaw', 'paper'], 'session_id': 1},
    {'action': 'openclaw chat: "PPO 训练 reward 不收敛，帮我排查"', 'semantic': 'OpenClaw 协助调试 RL 训练', 'tags': ['openclaw', 'debug'], 'session_id': 2},
    {'action': 'openclaw skill: code-review on grasp_policy/model.py', 'semantic': 'OpenClaw 审查抓取策略代码', 'tags': ['openclaw', 'review'], 'session_id': 3},
    {'action': 'openclaw chat: "ROS2 tf2 坐标变换报错，帮我调试"', 'semantic': 'OpenClaw 调试 ROS2 坐标变换', 'tags': ['openclaw', 'debug'], 'session_id': 4},
    {'action': 'openclaw chat: "设计 sim2real domain randomization 方案"', 'semantic': 'OpenClaw 辅助设计仿真迁移方案', 'tags': ['openclaw', 'architecture'], 'session_id': 5},
    {'action': 'openclaw chat: "总结今天实验结果，写入知识库"', 'semantic': 'OpenClaw 生成实验总结', 'tags': ['openclaw', 'summary'], 'session_id': 6},
    {'action': 'openclaw skill: tdd-guide for nav_planner', 'semantic': 'OpenClaw TDD 引导导航规划器开发', 'tags': ['openclaw', 'tdd'], 'session_id': 7},
    {'action': 'openclaw chat: "对比 Habitat 和 iGibson 仿真环境的优劣"', 'semantic': 'OpenClaw 对比仿真环境', 'tags': ['openclaw', 'learning'], 'session_id': 8},
    {'action': 'openclaw chat: "帮我设计 Habitat 环境的 reward function"', 'semantic': 'OpenClaw 辅助设计奖励函数', 'tags': ['openclaw', 'architecture'], 'session_id': 9},
    {'action': 'openclaw chat: "分析 SAC 和 TD3 在连续控制任务上的差异"', 'semantic': 'OpenClaw 分析 RL 算法差异', 'tags': ['openclaw', 'paper'], 'session_id': 10},
    {'action': 'openclaw chat: "帮我写一个 ROS2 的 action server"', 'semantic': 'OpenClaw 辅助 ROS2 开发', 'tags': ['openclaw', 'architecture'], 'session_id': 11},
    {'action': 'openclaw skill: code-review on sim2real/visual_dr.py', 'semantic': 'OpenClaw 审查 sim2real 代码', 'tags': ['openclaw', 'review'], 'session_id': 12},
    {'action': 'openclaw chat: "整理本周实验数据，生成对比表格"', 'semantic': 'OpenClaw 整理实验数据', 'tags': ['openclaw', 'experiment'], 'session_id': 13},
    {'action': 'openclaw chat: "讨论 ViT 在视觉导航中的应用前景"', 'semantic': 'OpenClaw 讨论前沿技术', 'tags': ['openclaw', 'learning'], 'session_id': 14},
    {'action': 'openclaw chat: "帮我调试 CUDA out of memory 问题"', 'semantic': 'OpenClaw 调试 GPU 内存问题', 'tags': ['openclaw', 'debug'], 'session_id': 15},
]

TERMINAL_ACTIONS = [
    {'action': 'python train.py --env HabitatNav-v2 --epochs 200 --lr 3e-4', 'semantic': '训练视觉导航 PPO 策略', 'tags': ['ml', 'training']},
    {'action': 'roslaunch manipulation_pkg grasp_demo.launch', 'semantic': '启动机械臂抓取演示', 'tags': ['ros', 'manipulation']},
    {'action': 'gazebo --verbose worlds/tabletop.world', 'semantic': '启动 Gazebo 桌面仿真环境', 'tags': ['simulation', 'gazebo']},
    {'action': 'colcon build --packages-select nav_planner', 'semantic': '编译 ROS2 导航规划包', 'tags': ['ros2', 'build']},
    {'action': 'tensorboard --logdir runs/ppo_nav_0318', 'semantic': '查看训练曲线', 'tags': ['ml', 'visualization']},
    {'action': 'ssh robot@192.168.1.100 "rostopic echo /joint_states"', 'semantic': '远程查看机器人关节状态', 'tags': ['robot', 'ssh']},
    {'action': 'pytest tests/test_policy.py -v', 'semantic': '运行策略网络单元测试', 'tags': ['test', 'python']},
    {'action': 'python eval.py --checkpoint best_model.pt --episodes 100', 'semantic': '评估最优模型性能', 'tags': ['ml', 'evaluation']},
    {'action': 'pip install habitat-sim==0.3.0', 'semantic': '安装 Habitat 仿真器', 'tags': ['dependency', 'python']},
    {'action': 'nvidia-smi', 'semantic': '检查 GPU 使用情况', 'tags': ['gpu', 'monitoring']},
]

GIT_ACTIONS = [
    {'action': 'commit: feat: implement PPO reward shaping for navigation', 'semantic': '提交导航奖励塑形功能', 'tags': ['git', 'feature']},
    {'action': 'commit: fix: resolve tf2 lookup timeout in grasp pipeline', 'semantic': '修复抓取流水线坐标变换超时', 'tags': ['git', 'bugfix']},
    {'action': 'commit: refactor: extract point cloud preprocessing utils', 'semantic': '重构点云预处理工具', 'tags': ['git', 'refactor']},
    {'action': 'commit: docs: add experiment results for PPO vs SAC', 'semantic': '记录 PPO vs SAC 实验结果', 'tags': ['git', 'docs']},
    {'action': 'commit: feat: add domain randomization for sim2real', 'semantic': '添加域随机化仿真迁移', 'tags': ['git', 'feature']},
    {'action': 'merge: feat/ppo-reward into main', 'semantic': '合并 PPO 奖励分支', 'tags': ['git', 'merge']},
    {'action': 'commit: test: add unit tests for nav_planner', 'semantic': '添加导航规划器单元测试', 'tags': ['git', 'test']},
]

CLAUDE_CODE_ACTIONS = [
    {'action': 'claude: Edit src/models/ppo_agent.py', 'semantic': 'Claude Code 编辑 PPO 智能体', 'tags': ['claude', 'edit']},
    {'action': 'claude: Bash python -m pytest tests/ -v', 'semantic': 'Claude Code 运行测试套件', 'tags': ['claude', 'test']},
    {'action': 'claude: Grep "reward_function" src/', 'semantic': 'Claude Code 搜索奖励函数', 'tags': ['claude', 'search']},
]


# 来源分布: openclaw 35%, terminal 25%, git 20%, claude_code 15%, env 5%
def _pick_source():
    r = random.random()
    if r < 0.35:
        return 'openclaw'
    if r < 0.60:
        return 'terminal'
    if r < 0.80:
        return 'git'
    if r < 0.95:
        return 'claude_code'
    return 'env'


def _generate_event_data(source):
    project = random.choice(PROJECTS)
    branch = random.choice(BRANCHES)
    base = {'directory': f'/home/liyufeng/research/{project}', 'project': project, 'branch': branch}

    if source == 'openclaw':
        d = random.choice(OPENCLAW_ACTIONS)
        return {**base, 'action': d['action'], 'semantic': d['semantic'], 'tags': d['tags'],
                'exit_code': 0, 'duration_ms': 2000 + random.randint(0, 30000), 'openclaw_session_id': d['session_id']}
    if source == 'terminal':
        d = random.choice(TERMINAL_ACTIONS)
        exit_code = 1 if random.random() > 0.9 else 0
        return {**base, 'action': d['action'], 'semantic': d['semantic'], 'tags': d['tags'],
                'exit_code': exit_code, 'duration_ms': 100 + random.randint(0, 10000)}
    if source == 'git':
        d = random.choice(GIT_ACTIONS)
        return {**base, 'action': d['action'], 'semantic': d['semantic'], 'tags': d['tags'],
                'exit_code': 0, 'duration_ms': 50 + random.randint(0, 500)}
    if source == 'claude_code':
        d = random.choice(CLAUDE_CODE_ACTIONS)
        return {**base, 'action': d['action'], 'semantic': d['semantic'], 'tags': d['tags'],
                'exit_code': 0, 'duration_ms': 500 + random.randint(0, 5000)}
    # env
    return {**base, 'action': 'env snapshot: CUDA 12.4 / PyTorch 2.3 / ROS2 Humble',
            'semantic': '环境变更检测', 'tags': ['env'], 'exit_code': 0, 'duration_ms': 0}


def _seed_events(db):
    # 30 天数据, 每天 20-60 个事件
    events = []
    eid = 1
    for day in range(29, -1, -1):
        base_ts = NOW - day * DAY
        events_per_day = 20 + random.randint(0, 40)
        for _ in range(events_per_day):
            ts = base_ts + random.randint(0, 12 * HOUR) + 8 * HOUR
            source = _pick_source()
            data = _generate_event_data(source)
            events.append(DevEvent(
                id=eid,
                timestamp=ts,
                source=source,
                action=data['action'],
                directory=data['directory'],
                project=data['project'],
                branch=data['branch'],
                exit_code=data['exit_code'],
                duration_ms=data['duration_ms'],
                semantic=data['semantic'],
                tags=json.dumps(data['tags'] + ['seed']),
                openclaw_session_id=data.get('openclaw_session_id'),
            ))
            eid += 1
    events.sort(key=lambda e: e.timestamp)
    db.add_all(events)
    return events


def _seed_skills(db):
    skills = [
        Skill(id=1, name='OpenClaw', category='openclaw', level=85, total_uses=420, last_used=NOW - 300, first_seen=NOW - 25 * DAY),
        Skill(id=2, name='Python', category='language', level=82, total_uses=380, last_used=NOW - 600, first_seen=NOW - 29 * DAY),
        Skill(id=3, name='PyTorch', category='framework', level=78, total_uses=310, last_used=NOW - 1200, first_seen=NOW - 28 * DAY),
        Skill(id=4, name='ROS2', category='framework', level=72, total_uses=260, last_used=NOW - 1800, first_seen=NOW - 27 * DAY),
        Skill(id=5, name='Git', category='vcs', level=70, total_uses=240, last_used=NOW - 900, first_seen=NOW - 29 * DAY),
        Skill(id=6, name='Gazebo', category='tool', level=65, total_uses=180, last_used=NOW - 2 * HOUR, first_seen=NOW - 25 * DAY),
        Skill(id=7, name='Habitat', category='tool', level=60, total_uses=150, last_used=NOW - 4 * HOUR, first_seen=NOW - 20 * DAY),
        Skill(id=8, name='Docker', category='devops', level=55, total_uses=95, last_used=NOW - DAY, first_seen=NOW - 20 * DAY),
        Skill(id=9, name='TensorBoard', category='tool', level=52, total_uses=88, last_used=NOW - 3 * HOUR, first_seen=NOW - 26 * DAY),
        Skill(id=10, name='Claude Code', category='openclaw', level=58, total_uses=140, last_used=NOW - 1200, first_seen=NOW - 20 * DAY),
        Skill(id=11, name='C++', category='language', level=48, total_uses=75, last_used=NOW - 2 * DAY, first_seen=NOW - 29 * DAY),
        Skill(id=12, name='CUDA', category='language', level=42, total_uses=55, last_used=NOW - 3 * DAY, first_seen=NOW - 22 * DAY),
        Skill(id=13, name='SSH', category='network', level=45, total_uses=60, last_used=NOW - 5 * HOUR, first_seen=NOW - 29 * DAY),
        Skill(id=14, name='NumPy', category='framework', level=68, total_uses=200, last_used=NOW - 2 * HOUR, first_seen=NOW - 29 * DAY),
        Skill(id=15, name='Open3D', category='framework', level=35, total_uses=30, last_used=NOW - 5 * DAY, first_seen=NOW - 15 * DAY),
    ]
    db.add_all(skills)


def _seed_sessions(db):
    sessions = [
        OpenClawSession(
            id=1, title='分析 PointNav 论文核心创新点', category='paper', project='paper-reproduce',
            tags=json.dumps(['论文', '导航', 'PointNav']), created_at=NOW - 2 * DAY,
            summary='深入分析了 PointNav 论文的视觉编码器设计和奖励函数创新',
            messages=json.dumps([
                {'role': 'user', 'content': '帮我分析这篇 PointNav 论文的核心创新点，特别是它的视觉编码器设计和 reward shaping 策略。', 'timestamp': NOW - 2 * DAY},
                {'role': 'assistant', 'content': '这篇论文的核心创新有三点：\n\n1. **视觉编码器**：采用 ResNet-18 作为 backbone，但关键创新在于引入了 depth prediction auxiliary task，让编码器同时学习深度估计，这显著提升了导航策略对空间结构的理解。\n\n2. **Reward Shaping**：不同于传统的稀疏奖励（只在到达目标时给正奖励），论文设计了基于 geodesic distance 的密集奖励：\n   - 每步奖励 = Δd(geodesic) × α + success_reward\n   - 其中 α=1.0 用于平衡探索和利用\n\n3. **训练策略**：采用 DD-PPO（Decentralized Distributed PPO），在 64 个 GPU 上并行训练，每个 worker 独立收集经验，通过 gradient averaging 同步。\n\n建议你在复现时重点关注 reward shaping 部分，这是性能提升的关键。', 'timestamp': NOW - 2 * DAY + 30},
                {'role': 'user', 'content': '那 geodesic distance 具体怎么计算的？在 Habitat 环境里有现成的 API 吗？', 'timestamp': NOW - 2 * DAY + 120},
                {'role': 'assistant', 'content': 'Habitat 提供了现成的 API：\n\n```python\n# 获取 geodesic distance\ngeo_dist = env.sim.geodesic_distance(\n    position_a=agent_position,\n    position_b=goal_position\n)\n```\n\n底层实现是基于 NavMesh 的最短路径计算。注意几个坑：\n- 如果两点之间不可达，返回 `inf`，需要处理这种情况\n- NavMesh 的精度取决于 mesh 的分辨率，建议用 `navmesh_settings.cell_size=0.05`\n- 计算开销不大，每步调用不会成为瓶颈\n\n你的 reward function 可以这样写：\n```python\ndef compute_reward(prev_dist, curr_dist, success):\n    reward = prev_dist - curr_dist  # 接近目标为正\n    if success:\n        reward += 10.0  # success bonus\n    reward -= 0.01  # step penalty\n    return reward\n```', 'timestamp': NOW - 2 * DAY + 150},
            ]),
        ),
        OpenClawSession(
            id=2, title='PPO 训练 reward 不收敛排查', category='debug', project='embodied-nav',
            tags=json.dumps(['PPO', '训练', '调试']), created_at=NOW - DAY,
            summary='排查了 PPO 训练不收敛问题，发现是 reward normalization 和 learning rate 的问题',
            messages=json.dumps([
                {'role': 'user', 'content': '我的 PPO 训练跑了 500 个 epoch，reward 一直在 -2 到 0 之间震荡，完全不收敛。loss 也在跳。帮我排查一下。', 'timestamp': NOW - DAY},
                {'role': 'assistant', 'content': '典型的 PPO 不收敛问题，我们逐步排查：\n\n**1. 先看 reward 分布**\n你的 reward range 是 [-2, 0]，这说明 agent 基本没有成功到达目标。先确认：\n- 目标距离是否合理？初始距离太远会导致探索困难\n- success rate 是多少？如果接近 0%，说明任务太难\n\n**2. 检查 hyperparameters**\n常见问题：\n- `lr` 太大导致策略崩溃，建议 `2.5e-4`\n- `clip_param` 建议 `0.1`（不是默认的 0.2）\n- `num_steps` 太短，导航任务建议至少 `128`\n- `entropy_coef` 太小，建议 `0.01` 保持探索\n\n**3. Reward normalization**\n你有做 reward normalization 吗？PPO 对 reward scale 很敏感。\n\n先把这些信息发给我看看。', 'timestamp': NOW - DAY + 30},
                {'role': 'user', 'content': '我的 lr 是 1e-3，clip 是 0.2，没有做 reward normalization。初始距离大概 5-15 米。', 'timestamp': NOW - DAY + 180},
                {'role': 'assistant', 'content': '找到问题了，主要是两个：\n\n**问题 1: lr 太大**\n`1e-3` 对 PPO 来说太激进了，会导致策略更新过大，KL divergence 爆炸。改成 `2.5e-4`。\n\n**问题 2: 缺少 reward normalization**\n这是最关键的。加上 running mean/std normalization：\n\n```python\nclass RunningMeanStd:\n    def __init__(self):\n        self.mean = 0.0\n        self.var = 1.0\n        self.count = 1e-4\n    \n    def update(self, x):\n        batch_mean = np.mean(x)\n        batch_var = np.var(x)\n        batch_count = len(x)\n        self.update_from_moments(batch_mean, batch_var, batch_count)\n    \n    def normalize(self, x):\n        return (x - self.mean) / np.sqrt(self.var + 1e-8)\n```\n\n改完这两个，重新训练应该能看到明显改善。另外建议加上 gradient clipping `max_grad_norm=0.5`。', 'timestamp': NOW - DAY + 210},
                {'role': 'user', 'content': '改了之后 reward 开始上升了！但是到 epoch 200 左右又开始下降，是过拟合了吗？', 'timestamp': NOW - DAY + HOUR},
                {'role': 'assistant', 'content': '不太像过拟合，更像是 **policy collapse**。PPO 在训练中期容易出现策略退化。\n\n建议：\n1. **增大 entropy coefficient** 到 `0.02`，防止策略过早收敛\n2. **使用 learning rate schedule**：线性衰减到 0\n3. **增加训练环境多样性**：用多个不同的 scene 训练\n\n```python\n# LR schedule\ndef lr_lambda(epoch):\n    return 1.0 - epoch / total_epochs\n\nscheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)\n```\n\n另外检查一下 value function 的 loss 是否也在震荡，如果是的话可能需要增大 `value_loss_coef`。', 'timestamp': NOW - DAY + HOUR + 30},
            ]),
        ),
        OpenClawSession(
            id=3, title='Review grasp policy 代码', category='review', project='grasp-policy',
            tags=json.dumps(['代码审查', '抓取', '策略']), created_at=NOW - 3 * DAY,
            summary='审查了抓取策略代码，发现了点云处理和 action space 设计的问题',
            messages=json.dumps([
                {'role': 'user', 'content': '帮我 review 一下 grasp_policy/model.py 的代码，特别关注网络结构和 action space 设计。', 'timestamp': NOW - 3 * DAY},
                {'role': 'assistant', 'content': '看了你的代码，有几个问题需要注意：\n\n**1. 点云预处理 (Critical)**\n你直接把原始点云喂进 PointNet，但没有做 voxel downsampling。10万个点的计算量太大，建议先降采样到 2048 个点：\n```python\nimport open3d as o3d\npcd = o3d.geometry.PointCloud()\npcd.points = o3d.utility.Vector3dVector(points)\npcd = pcd.voxel_down_sample(voxel_size=0.005)\n```\n\n**2. Action Space 设计 (High)**\n你用的是连续 6-DoF action space (x,y,z,roll,pitch,yaw)，但 yaw 的范围是 [-π, π]，这会导致 boundary 问题。建议用 quaternion 表示旋转，或者把 yaw 拆成 sin/cos 两个维度。\n\n**3. Reward 设计 (Medium)**\n抓取成功只给 +1 奖励太稀疏了。建议加入中间奖励：\n- 接近物体: +0.1 × Δdistance\n- 手指闭合时接触物体: +0.3\n- 成功抬起: +1.0\n\n**4. 网络结构 (Low)**\nPointNet 的 feature 维度 1024 对于抓取任务可能过大，512 就够了。', 'timestamp': NOW - 3 * DAY + 60},
            ]),
        ),
        OpenClawSession(
            id=4, title='ROS2 tf2 坐标变换调试', category='debug', project='ros2-workspace',
            tags=json.dumps(['ROS2', 'tf2', '调试']), created_at=NOW - 4 * DAY,
            summary='解决了 ROS2 tf2 坐标变换超时问题，原因是 static transform publisher 启动顺序',
            messages=json.dumps([
                {'role': 'user', 'content': 'ROS2 的 tf2 坐标变换一直报 LookupException: "base_link" passed to lookupTransform argument target_frame does not exist。但我明明发布了 static transform。', 'timestamp': NOW - 4 * DAY},
                {'role': 'assistant', 'content': '这个问题通常是 **启动顺序** 导致的。tf2 的 buffer 需要时间来接收 transform。\n\n排查步骤：\n\n1. **确认 transform 是否在发布**：\n```bash\nros2 topic echo /tf_static\n```\n\n2. **检查 frame 名称**：注意有没有多余的 `/` 前缀。ROS2 的 frame 不应该以 `/` 开头：\n```python\n# 错误\ntarget_frame = "/base_link"\n# 正确\ntarget_frame = "base_link"\n```\n\n3. **增加 timeout**：\n```python\ntry:\n    transform = tf_buffer.lookup_transform(\n        "base_link", "camera_link",\n        rclpy.time.Time(),\n        timeout=rclpy.duration.Duration(seconds=2.0)\n    )\nexcept TransformException as e:\n    self.get_logger().warn(f"Transform not available: {e}")\n```\n\n4. **确保 static_transform_publisher 先启动**：在 launch 文件中设置依赖。\n\n最常见的原因就是第 2 点，frame 名称带了 `/`。', 'timestamp': NOW - 4 * DAY + 45},
            ]),
        ),
        OpenClawSession(
            id=5, title='设计 sim2real domain randomization 方案', category='architecture', project='sim2real-transfer',
            tags=json.dumps(['sim2real', 'domain randomization', '方案设计']), created_at=NOW - 5 * DAY,
            summary='设计了完整的 domain randomization 方案，覆盖视觉、物理和动力学三个层面',
            messages=json.dumps([
                {'role': 'user', 'content': '我的导航策略在 Habitat 仿真中 success rate 85%，但部署到真实机器人上只有 30%。帮我设计一个 sim2real 的 domain randomization 方案。', 'timestamp': NOW - 5 * DAY},
                {'role': 'assistant', 'content': 'sim2real gap 55% 确实很大。我建议从三个层面做 domain randomization：\n\n## 1. 视觉层 (Visual DR)\n- **光照随机化**：随机调整环境光强度 [0.3, 1.5]、色温 [3000K, 7000K]\n- **纹理随机化**：墙面、地面纹理随机替换\n- **相机噪声**：添加高斯噪声 σ∈[0, 0.05]，模拟真实相机\n- **色彩抖动**：brightness/contrast/saturation 各 ±20%\n\n## 2. 物理层 (Physics DR)\n- **摩擦系数**：地面摩擦 μ∈[0.3, 1.0]\n- **碰撞参数**：restitution ∈[0.0, 0.5]\n- **障碍物随机放置**：每个 episode 随机生成 3-8 个障碍物\n\n## 3. 动力学层 (Dynamics DR)\n- **执行噪声**：action 加高斯噪声 σ∈[0, 0.1]\n- **延迟模拟**：随机 1-3 帧的 action delay\n- **里程计漂移**：累积误差模拟\n\n实现建议用 Habitat 的 `habitat.config` 配置系统，每个 episode reset 时随机采样参数。', 'timestamp': NOW - 5 * DAY + 90},
            ]),
        ),
        OpenClawSession(
            id=6, title='总结今日实验结果', category='experiment', project='embodied-nav',
            tags=json.dumps(['实验', '总结', '知识库']), created_at=NOW - DAY + 10 * HOUR,
            summary='总结了 PPO vs SAC 在导航任务上的对比实验结果',
            messages=json.dumps([
                {'role': 'user', 'content': '帮我总结今天的实验结果。PPO 和 SAC 在 HabitatNav-v2 上跑了 1000 个 episode 的评估。PPO success rate 78%, SPL 0.62; SAC success rate 71%, SPL 0.55。', 'timestamp': NOW - DAY + 10 * HOUR},
                {'role': 'assistant', 'content': '## 实验总结：PPO vs SAC 导航性能对比\n\n**实验设置**\n- 环境：HabitatNav-v2\n- 评估 episodes：1000\n- 场景：Gibson 数据集 val split\n\n**结果对比**\n| 指标 | PPO | SAC | 差异 |\n|------|-----|-----|------|\n| Success Rate | 78% | 71% | +7% |\n| SPL | 0.62 | 0.55 | +0.07 |\n\n**分析**\n1. PPO 在 success rate 和 SPL 上均优于 SAC，这与 Habitat Challenge 的经验一致\n2. PPO 的优势主要来自更稳定的策略更新（clipping 机制）\n3. SAC 在长距离导航上表现更差，可能是 entropy regularization 导致过度探索\n\n**下一步建议**\n- 以 PPO 作为基线，继续优化 reward shaping\n- 尝试 DD-PPO 分布式训练提升样本效率\n- 加入 auxiliary tasks（depth prediction）提升视觉表征\n\n已写入知识库。', 'timestamp': NOW - DAY + 10 * HOUR + 30},
            ]),
        ),
        OpenClawSession(
            id=7, title='TDD 引导导航规划器开发', category='review', project='embodied-nav',
            tags=json.dumps(['TDD', '导航', '测试']), created_at=NOW - 6 * DAY,
            summary='使用 TDD 方法开发导航规划器的路径平滑模块',
            messages=json.dumps([
                {'role': 'user', 'content': '我要给 nav_planner 加一个路径平滑功能，用 TDD 的方式来开发。帮我先设计测试用例。', 'timestamp': NOW - 6 * DAY},
                {'role': 'assistant', 'content': '好的，先写测试再实现。路径平滑的核心测试用例：\n\n```python\nimport pytest\nimport numpy as np\nfrom nav_planner.path_smoother import smooth_path\n\nclass TestPathSmoother:\n    def test_straight_path_unchanged(self):\n        """直线路径不应被修改"""\n        path = np.array([[0,0], [1,0], [2,0], [3,0]])\n        result = smooth_path(path)\n        np.testing.assert_array_almost_equal(result, path)\n    \n    def test_sharp_turn_smoothed(self):\n        """90度急转弯应被平滑"""\n        path = np.array([[0,0], [1,0], [1,1]])\n        result = smooth_path(path)\n        # 平滑后中间点应偏移\n        assert result[1][0] < 1.0\n        assert result[1][1] > 0.0\n    \n    def test_preserves_start_end(self):\n        """起点和终点不应改变"""\n        path = np.array([[0,0], [1,1], [2,0], [3,1]])\n        result = smooth_path(path)\n        np.testing.assert_array_equal(result[0], path[0])\n        np.testing.assert_array_equal(result[-1], path[-1])\n    \n    def test_obstacle_avoidance(self):\n        """平滑后路径不应穿过障碍物"""\n        path = np.array([[0,0], [1,0], [2,0]])\n        obstacles = [np.array([1.5, 0.3])]\n        result = smooth_path(path, obstacles=obstacles)\n        # 验证所有点到障碍物距离 > safety_margin\n        for point in result:\n            for obs in obstacles:\n                assert np.linalg.norm(point - obs) > 0.2\n```\n\n先跑这些测试（应该全部 FAIL），然后我们再实现 `smooth_path` 函数。', 'timestamp': NOW - 6 * DAY + 45},
            ]),
        ),
        OpenClawSession(
            id=8, title='对比 Habitat 和 iGibson 仿真环境', category='learning', project='paper-reproduce',
            tags=json.dumps(['仿真', 'Habitat', 'iGibson', '对比']), created_at=NOW - 7 * DAY,
            summary='对比了 Habitat 和 iGibson 两个仿真环境的优劣，决定使用 Habitat',
            messages=json.dumps([
                {'role': 'user', 'content': '我在选仿真环境，Habitat 和 iGibson 各有什么优劣？我的任务是室内视觉导航。', 'timestamp': NOW - 7 * DAY},
                {'role': 'assistant', 'content': '两个环境我都用过，给你详细对比：\n\n## Habitat\n**优势**：\n- 渲染速度极快（GPU 加速，单 GPU 可达 10000+ FPS）\n- 社区活跃，Meta AI 持续维护\n- Habitat Challenge 提供标准 benchmark\n- 支持 Gibson/MP3D/HM3D 多个数据集\n\n**劣势**：\n- 物理仿真较弱（不适合操作任务）\n- 安装配置复杂（需要编译 habitat-sim）\n\n## iGibson\n**优势**：\n- 物理仿真更真实（基于 PyBullet）\n- 支持交互式物体操作\n- 内置多种机器人模型\n\n**劣势**：\n- 渲染速度慢（约 100-300 FPS）\n- 社区较小，更新频率低\n- 场景数量有限\n\n## 建议\n你的任务是**视觉导航**，不涉及物体操作，所以 **Habitat 是更好的选择**：\n1. 渲染速度快 → 训练效率高\n2. 标准 benchmark → 方便与 SOTA 对比\n3. HM3D 数据集有 800+ 场景 → 泛化性好\n\n如果后续要做 navigation + manipulation，再考虑 iGibson 或 Habitat 3.0。', 'timestamp': NOW - 7 * DAY + 60},
            ]),
        ),
        OpenClawSession(
            id=9, title='设计 Habitat 环境的 reward function', category='architecture', project='embodied-nav',
            tags=json.dumps(['Habitat', 'reward', '强化学习']), created_at=NOW - 8 * DAY,
            summary='设计了多层次的导航奖励函数，包含距离奖励、探索奖励和安全奖励',
            messages=json.dumps([
                {'role': 'user', 'content': '帮我设计一个更好的 Habitat 导航 reward function，现在的太简单了只有距离奖励。', 'timestamp': NOW - 8 * DAY},
                {'role': 'assistant', 'content': '好的，我建议设计一个多层次的奖励函数：\n\n## 1. 距离奖励（基础）\n```python\nr_dist = (prev_geo_dist - curr_geo_dist) * 1.0\n```\n\n## 2. 探索奖励（鼓励覆盖新区域）\n```python\nr_explore = 0.1 if visited_new_cell else 0.0\n```\n\n## 3. 安全奖励（避免碰撞）\n```python\nr_safety = -0.05 if collision else 0.0\n```\n\n## 4. 效率奖励（鼓励短路径）\n```python\nr_efficiency = -0.01  # 每步惩罚\n```\n\n## 5. 成功奖励\n```python\nr_success = 10.0 if success else 0.0\n```\n\n最终：`reward = r_dist + r_explore + r_safety + r_efficiency + r_success`\n\n关键是各项权重的平衡，建议先用这个配置训练，然后根据 agent 行为调整。', 'timestamp': NOW - 8 * DAY + 45},
                {'role': 'user', 'content': '探索奖励怎么实现？怎么判断是否访问了新区域？', 'timestamp': NOW - 8 * DAY + 300},
                {'role': 'assistant', 'content': '用一个 occupancy grid 来追踪已访问区域：\n\n```python\nclass ExplorationTracker:\n    def __init__(self, resolution=0.5):\n        self.visited = set()\n        self.resolution = resolution\n    \n    def update(self, position):\n        cell = (int(position[0] / self.resolution),\n                int(position[2] / self.resolution))\n        is_new = cell not in self.visited\n        self.visited.add(cell)\n        return is_new\n    \n    def reset(self):\n        self.visited.clear()\n```\n\nresolution=0.5 表示 50cm 的网格，太细会导致奖励太密集，太粗会失去意义。\n\n在 episode reset 时调用 `tracker.reset()`。', 'timestamp': NOW - 8 * DAY + 330},
            ]),
        ),
        OpenClawSession(
            id=10, title='分析 SAC 和 TD3 在连续控制任务上的差异', category='paper', project='grasp-policy',
            tags=json.dumps(['SAC', 'TD3', '连续控制', '论文']), created_at=NOW - 9 * DAY,
            summary='对比了 SAC 和 TD3 两种算法在机械臂连续控制任务上的表现差异',
            messages=json.dumps([
                {'role': 'user', 'content': '我在做机械臂抓取，SAC 和 TD3 哪个更适合？帮我分析下两者的差异。', 'timestamp': NOW - 9 * DAY},
                {'role': 'assistant', 'content': '## SAC vs TD3 对比分析\n\n### 核心区别\n- **SAC**：最大熵框架，自动调节 entropy coefficient，鼓励探索\n- **TD3**：确定性策略 + 双 Q 网络 + 延迟更新，更保守\n\n### 在机械臂抓取任务上\n\n| 维度 | SAC | TD3 |\n|------|-----|-----|\n| 探索能力 | 强（entropy bonus） | 弱（依赖噪声） |\n| 样本效率 | 中等 | 较高 |\n| 训练稳定性 | 好 | 好 |\n| 超参敏感度 | 低（自动调 alpha） | 中等 |\n| 适合场景 | 多模态解、需要探索 | 单一最优解 |\n\n### 建议\n抓取任务通常有**多种可行的抓取姿态**，这是多模态问题，**SAC 更适合**。\n\nTD3 适合那种只有一个最优解的任务（比如精确轨迹跟踪）。\n\n不过建议两个都跑一下做对比，作为论文的 baseline。', 'timestamp': NOW - 9 * DAY + 60},
            ]),
        ),
        OpenClawSession(
            id=11, title='帮我写一个 ROS2 的 action server', category='architecture', project='ros2-workspace',
            tags=json.dumps(['ROS2', 'action server', '导航']), created_at=NOW - 10 * DAY,
            summary='实现了一个 ROS2 action server 用于导航任务的执行和反馈',
            messages=json.dumps([
                {'role': 'user', 'content': '帮我写一个 ROS2 的 action server，用于执行导航到目标点的任务，需要有进度反馈。', 'timestamp': NOW - 10 * DAY},
                {'role': 'assistant', 'content': '```python\nimport rclpy\nfrom rclpy.action import ActionServer\nfrom rclpy.node import Node\nfrom nav2_msgs.action import NavigateToPose\nimport math\n\nclass NavActionServer(Node):\n    def __init__(self):\n        super().__init__("nav_action_server")\n        self._action_server = ActionServer(\n            self, NavigateToPose, "navigate_to_pose",\n            self.execute_callback\n        )\n        self.get_logger().info("Navigation action server started")\n    \n    async def execute_callback(self, goal_handle):\n        self.get_logger().info("Executing navigation goal...")\n        feedback_msg = NavigateToPose.Feedback()\n        \n        target = goal_handle.request.pose.pose.position\n        # 模拟导航过程\n        for i in range(100):\n            # 计算剩余距离\n            feedback_msg.distance_remaining = \\\n                math.sqrt((target.x - i*0.1)**2 + (target.y)**2)\n            goal_handle.publish_feedback(feedback_msg)\n            await asyncio.sleep(0.1)\n        \n        goal_handle.succeed()\n        result = NavigateToPose.Result()\n        return result\n```\n\n关键点：\n1. 用 `async` 回调支持非阻塞执行\n2. 通过 `publish_feedback` 实时反馈进度\n3. 可以在回调中检查 `goal_handle.is_cancel_requested` 支持取消', 'timestamp': NOW - 10 * DAY + 60},
            ]),
        ),
        OpenClawSession(
            id=12, title='Review sim2real transfer 代码', category='review', project='sim2real-transfer',
            tags=json.dumps(['代码审查', 'sim2real', 'domain randomization']), created_at=NOW - 11 * DAY,
            summary='审查了 sim2real transfer 的 domain randomization 实现代码',
            messages=json.dumps([
                {'role': 'user', 'content': '帮我 review 一下 sim2real 的 domain randomization 代码，主要是视觉随机化部分。', 'timestamp': NOW - 11 * DAY},
                {'role': 'assistant', 'content': '看了你的代码，几个问题：\n\n**1. 随机化范围太窄 (Critical)**\n你的光照随机化只在 [0.8, 1.2] 范围，这远不够。真实环境光照变化很大，建议 [0.3, 2.0]。\n\n**2. 纹理随机化缺失 (High)**\n你只做了颜色抖动，没有纹理替换。建议加入：\n```python\ndef randomize_texture(mesh, texture_pool):\n    idx = np.random.randint(len(texture_pool))\n    mesh.visual.material.image = texture_pool[idx]\n```\n\n**3. 相机内参没有随机化 (Medium)**\n真实相机和仿真相机的 FOV、畸变参数不同，建议加入：\n- FOV: [60, 90] 度\n- 径向畸变: k1 ~ U(-0.1, 0.1)\n\n**4. 随机化时机 (Low)**\n你在每个 step 都随机化，太频繁了。建议每个 episode 开始时随机化一次就够了。', 'timestamp': NOW - 11 * DAY + 60},
            ]),
        ),
        OpenClawSession(
            id=13, title='整理本周实验数据，生成对比表格', category='experiment', project='embodied-nav',
            tags=json.dumps(['实验', '数据整理', '对比']), created_at=NOW - 2 * DAY + 8 * HOUR,
            summary='整理了一周的导航实验数据，生成了多维度对比表格',
            messages=json.dumps([
                {'role': 'user', 'content': '帮我整理这周的实验数据。PPO 跑了 3 个配置，SAC 跑了 2 个配置，都在 HabitatNav-v2 上。', 'timestamp': NOW - 2 * DAY + 8 * HOUR},
                {'role': 'assistant', 'content': '## 本周实验数据汇总\n\n| 配置 | 算法 | LR | Entropy | Success Rate | SPL | Avg Steps |\n|------|------|-----|---------|-------------|-----|-----------|\n| PPO-v1 | PPO | 2.5e-4 | 0.01 | 78% | 0.62 | 142 |\n| PPO-v2 | PPO | 2.5e-4 | 0.02 | 81% | 0.65 | 135 |\n| PPO-v3 | PPO | 1e-4 | 0.02 | 76% | 0.60 | 151 |\n| SAC-v1 | SAC | 3e-4 | auto | 71% | 0.55 | 168 |\n| SAC-v2 | SAC | 1e-4 | auto | 73% | 0.57 | 160 |\n\n**关键发现**：\n1. PPO-v2 是目前最优配置（entropy=0.02 很关键）\n2. 降低 LR 对 PPO 帮助不大，反而降低了性能\n3. SAC 整体不如 PPO，但 SAC-v2 的 LR 调低后有改善\n\n**下一步建议**：\n- 基于 PPO-v2 继续优化\n- 尝试加入 auxiliary task（depth prediction）\n- 增加训练 epoch 到 1000 看是否还能提升', 'timestamp': NOW - 2 * DAY + 8 * HOUR + 45},
            ]),
        ),
        OpenClawSession(
            id=14, title='讨论 ViT 在视觉导航中的应用前景', category='learning', project='paper-reproduce',
            tags=json.dumps(['ViT', '视觉导航', 'Transformer']), created_at=NOW - 12 * DAY,
            summary='探讨了 Vision Transformer 替代 CNN 作为导航视觉编码器的可行性',
            messages=json.dumps([
                {'role': 'user', 'content': '最近 ViT 很火，能不能用 ViT 替代 ResNet 作为导航的视觉编码器？', 'timestamp': NOW - 12 * DAY},
                {'role': 'assistant', 'content': '这是个好问题，目前学术界确实在探索这个方向。\n\n## ViT 用于导航的优劣\n\n**优势**：\n- 全局注意力机制，能捕获长距离空间关系\n- 在大规模预训练后泛化能力强\n- 最新的 DINOv2 提供了很好的视觉特征\n\n**劣势**：\n- 计算量大，推理速度慢（对实时导航是问题）\n- 需要大量数据预训练\n- 对小目标的感知不如 CNN\n\n## 最新进展\n- **VC-1**（Meta, 2023）：用 MAE 预训练的 ViT，在 Habitat 导航上超过 ResNet\n- **EmbCLIP**：用 CLIP 的视觉编码器做导航，zero-shot 能力强\n- **NaviLLM**：直接用 LLM + ViT 做端到端导航\n\n## 建议\n如果你的 GPU 资源充足，可以试试用 **ViT-B/16 + DINOv2 预训练权重** 替代 ResNet-18。预计 success rate 能提升 3-5%，但推理速度会慢 2-3 倍。\n\n折中方案：用 **MobileViT** 或 **EfficientViT**，兼顾精度和速度。', 'timestamp': NOW - 12 * DAY + 60},
            ]),
        ),
        OpenClawSession(
            id=15, title='调试 CUDA out of memory 问题', category='debug', project='embodied-nav',
            tags=json.dumps(['CUDA', 'OOM', '调试', 'GPU']), created_at=NOW - 3 * DAY + 6 * HOUR,
            summary='排查并解决了训练过程中的 CUDA OOM 问题',
            messages=json.dumps([
                {'role': 'user', 'content': '训练到 epoch 50 左右就 CUDA out of memory 了，但刚开始是正常的。怎么回事？', 'timestamp': NOW - 3 * DAY + 6 * HOUR},
                {'role': 'assistant', 'content': '训练中途 OOM 通常是**显存泄漏**，不是模型本身太大。常见原因：\n\n**1. 计算图未释放（最常见）**\n```python\n# 错误：loss 保留了计算图\nlosses.append(loss)\n\n# 正确：只保留数值\nlosses.append(loss.item())\n```\n\n**2. 梯度累积未清零**\n确保每个 batch 后调用 `optimizer.zero_grad()`\n\n**3. TensorBoard 日志写入 tensor**\n```python\n# 错误\nwriter.add_scalar("loss", loss, step)\n\n# 正确\nwriter.add_scalar("loss", loss.item(), step)\n```\n\n**排查方法**：\n```python\nimport torch\nprint(torch.cuda.memory_summary())\n```\n\n在每个 epoch 结束时打印显存使用，看是否持续增长。如果是，就是泄漏。\n\n另外加上 `torch.cuda.empty_cache()` 在每个 epoch 结束时调用，虽然不能解决根本问题，但能缓解。', 'timestamp': NOW - 3 * DAY + 6 * HOUR + 30},
                {'role': 'user', 'content': '找到了！是我把 loss append 到列表里了，没有用 .item()。改了之后稳定了。', 'timestamp': NOW - 3 * DAY + 7 * HOUR},
                {'role': 'assistant', 'content': '经典问题。建议你加一个 memory monitor 工具函数：\n\n```python\ndef log_gpu_memory(tag=""):\n    allocated = torch.cuda.memory_allocated() / 1024**3\n    reserved = torch.cuda.memory_reserved() / 1024**3\n    print(f"[GPU {tag}] Allocated: {allocated:.2f}GB, Reserved: {reserved:.2f}GB")\n```\n\n在训练循环的关键位置调用，方便以后快速定位类似问题。', 'timestamp': NOW - 3 * DAY + 7 * HOUR + 15},
            ]),
        ),
        OpenClawSession(
            id=16, title='设计点云抓取策略的网络架构', category='architecture', project='grasp-policy',
            tags=json.dumps(['点云', '网络架构', 'PointNet++']), created_at=NOW - 13 * DAY,
            summary='设计了基于 PointNet++ 的抓取策略网络，包含特征提取和抓取姿态预测',
            messages=json.dumps([
                {'role': 'user', 'content': '帮我设计一个基于点云的抓取策略网络，输入是桌面物体的点云，输出是抓取姿态。', 'timestamp': NOW - 13 * DAY},
                {'role': 'assistant', 'content': '## 网络架构设计\n\n### 输入\n- 点云: (N, 3) 或 (N, 6) 带法向量\n- 降采样到 2048 个点\n\n### 特征提取（PointNet++）\n```\nInput (2048, 3)\n  → SA Layer 1: 512 points, radius=0.1, [64, 64, 128]\n  → SA Layer 2: 128 points, radius=0.2, [128, 128, 256]\n  → SA Layer 3: 32 points, radius=0.4, [256, 256, 512]\n  → Global Feature: (1, 512)\n```\n\n### 抓取姿态预测头\n```\nGlobal Feature (512)\n  → FC(512, 256) + ReLU + Dropout(0.3)\n  → FC(256, 128) + ReLU\n  → 分支1: FC(128, 3) → 抓取位置 (x, y, z)\n  → 分支2: FC(128, 4) → 抓取朝向 (quaternion)\n  → 分支3: FC(128, 1) → 抓取宽度 (gripper width)\n  → 分支4: FC(128, 1) → 抓取质量分数 (sigmoid)\n```\n\n### 损失函数\n```python\nloss = L1(pos_pred, pos_gt) + \\\n       quaternion_loss(quat_pred, quat_gt) + \\\n       L1(width_pred, width_gt) + \\\n       BCE(quality_pred, quality_gt)\n```\n\n建议用 **Contact-GraspNet** 的数据集做训练，有 17k+ 标注的抓取姿态。', 'timestamp': NOW - 13 * DAY + 60},
            ]),
        ),
    ]
    db.add_all(sessions)


def _seed_documents(db):
    documents = [
        OpenClawDocument(id=1, title='3月18日任务：完成 PointNav 基线实验', type='daily_task',
            content='## 今日任务\n\n1. 在 HabitatNav-v2 环境中完成 PPO 基线训练（500 epochs）\n2. 评估 PPO vs SAC 在 Gibson val split 上的性能\n3. 记录实验结果，更新论文 Table 1\n\n## 完成情况\n- [x] PPO 训练完成，best success rate 78%\n- [x] SAC 训练完成，best success rate 71%\n- [x] 实验结果已记录\n- [ ] 论文 Table 1 待更新\n\n## 明日计划\n- 尝试 DD-PPO 分布式训练\n- 加入 depth prediction auxiliary task',
            tags=json.dumps(['任务', '实验', 'PointNav']), created_at=NOW - DAY, source_session_id=6),
        OpenClawDocument(id=2, title='论文笔记：Habitat 2.0 环境配置要点', type='paper_note',
            content='## Habitat 2.0 关键配置\n\n### 环境安装\n```bash\nconda create -n habitat python=3.9\npip install habitat-sim==0.3.0 --extra-index-url https://aihabitat.org/packages/habitat-sim\npip install habitat-lab==0.3.0\n```\n\n### 数据集配置\n- Gibson: 72 个场景，适合快速验证\n- MP3D: 90 个场景，更大更复杂\n- HM3D: 800+ 场景，推荐用于最终训练\n\n### 性能优化\n- 使用 `habitat.simulator.habitat_sim_v0.gpu_gpu=True` 开启 GPU 渲染\n- batch size 建议 4-8（取决于 GPU 显存）\n- 使用 `VectorEnv` 并行化环境',
            tags=json.dumps(['Habitat', '配置', '论文']), created_at=NOW - 5 * DAY, source_session_id=8),
        OpenClawDocument(id=3, title='实验日志：PPO vs SAC 导航对比', type='experiment_log',
            content='## 实验设置\n- 环境：HabitatNav-v2 (Gibson val split)\n- 训练：500 epochs, lr=2.5e-4\n- 评估：1000 episodes\n\n## 结果\n| 指标 | PPO | SAC |\n|------|-----|-----|\n| Success Rate | 78% | 71% |\n| SPL | 0.62 | 0.55 |\n| Avg Path Length | 8.3m | 9.1m |\n| Avg Episode Steps | 142 | 168 |\n\n## 结论\nPPO 在所有指标上优于 SAC，主要优势在于策略稳定性。SAC 的 entropy regularization 在导航任务中导致过度探索。\n\n## 训练曲线\n- PPO: reward 在 epoch 100 开始稳定上升，epoch 300 收敛\n- SAC: reward 波动较大，epoch 400 才基本收敛',
            tags=json.dumps(['PPO', 'SAC', '对比实验']), created_at=NOW - DAY, source_session_id=6),
        OpenClawDocument(id=4, title='会议纪要：组会讨论 sim2real gap', type='meeting_note',
            content='## 组会纪要 - 2026.03.15\n\n### 参会人员\n导师、李同学、张同学、王同学\n\n### 讨论内容\n1. **sim2real gap 现状**：仿真 85% → 真实 30%，gap 太大\n2. **导师建议**：\n   - 先做 visual domain randomization\n   - 考虑用 real2sim 的方式缩小 gap\n   - 参考 NVIDIA 的 DR 论文\n3. **分工**：\n   - 李同学：实现 visual DR（光照、纹理、噪声）\n   - 张同学：实现 dynamics DR（摩擦、延迟）\n   - 王同学：搭建真实环境测试平台\n\n### 下次会议\n3月22日，汇报 DR 实验结果',
            tags=json.dumps(['组会', 'sim2real', '讨论']), created_at=NOW - 4 * DAY, source_session_id=5),
        OpenClawDocument(id=5, title='3月17日任务：ROS2 导航栈调试', type='daily_task',
            content='## 今日任务\n\n1. 修复 tf2 坐标变换超时问题\n2. 测试 nav2 导航栈在真实机器人上的表现\n3. 记录 odometry 漂移数据\n\n## 完成情况\n- [x] tf2 问题已修复（frame 名称带了多余的 /）\n- [x] nav2 基本功能正常\n- [ ] odometry 漂移数据收集中（需要更长时间）\n\n## 遇到的问题\n- nav2 的 costmap 更新频率太低，导致避障反应慢\n- 建议调整 `update_frequency` 从 5Hz 到 10Hz',
            tags=json.dumps(['ROS2', '导航', '调试']), created_at=NOW - 2 * DAY, source_session_id=4),
        OpenClawDocument(id=6, title='论文笔记：PointNav 视觉编码器设计', type='paper_note',
            content='## PointNav 核心创新\n\n### 视觉编码器\n- ResNet-18 backbone + depth prediction auxiliary task\n- 深度估计辅助任务显著提升空间理解\n\n### Reward Shaping\n- 基于 geodesic distance 的密集奖励\n- reward = delta_d * alpha + success_reward\n- alpha=1.0 平衡探索和利用\n\n### DD-PPO 训练\n- 64 GPU 并行训练\n- 独立收集经验 + gradient averaging\n- 比标准 PPO 快 10x\n\n### 复现要点\n- geodesic distance 用 Habitat API 直接获取\n- NavMesh cell_size=0.05 保证精度\n- 注意处理不可达情况（返回 inf）',
            tags=json.dumps(['PointNav', '论文', '视觉编码器']), created_at=NOW - 2 * DAY + 2 * HOUR, source_session_id=1),
        OpenClawDocument(id=7, title='实验日志：Reward Function 消融实验', type='experiment_log',
            content='## 消融实验：多层次奖励函数\n\n### 实验配置\n- 基础环境：HabitatNav-v2\n- 训练 epoch：300\n- 评估 episode：500\n\n### 结果\n| 配置 | Success Rate | SPL |\n|------|-------------|-----|\n| 仅距离奖励 | 72% | 0.56 |\n| +探索奖励 | 76% | 0.59 |\n| +安全奖励 | 78% | 0.61 |\n| +效率惩罚 | 81% | 0.65 |\n| 全部（最终） | 81% | 0.65 |\n\n### 结论\n探索奖励和效率惩罚贡献最大，安全奖励对 SPL 有帮助',
            tags=json.dumps(['消融实验', 'reward', '导航']), created_at=NOW - 8 * DAY, source_session_id=9),
        OpenClawDocument(id=8, title='3月15日任务：sim2real DR 实现', type='daily_task',
            content='## 今日任务\n\n1. 实现视觉层 domain randomization\n2. 测试光照和纹理随机化效果\n3. 收集真实环境测试数据\n\n## 完成情况\n- [x] 光照随机化实现（范围 [0.3, 2.0]）\n- [x] 纹理随机化实现（20 种纹理池）\n- [x] 相机噪声添加\n- [ ] 真实环境数据收集（设备占用中）\n\n## 问题记录\n- 纹理随机化导致渲染速度下降 15%\n- 需要优化纹理加载策略',
            tags=json.dumps(['sim2real', 'DR', '任务']), created_at=NOW - 4 * DAY, source_session_id=12),
        OpenClawDocument(id=9, title='论文笔记：ViT 在具身导航中的应用', type='paper_note',
            content='## ViT for Embodied Navigation\n\n### 相关工作\n- VC-1 (Meta, 2023): MAE 预训练 ViT，超过 ResNet\n- EmbCLIP: CLIP 视觉编码器 + 导航策略\n- NaviLLM: LLM + ViT 端到端导航\n\n### ViT 优势\n- 全局注意力捕获长距离空间关系\n- 大规模预训练后泛化能力强\n- DINOv2 提供优质视觉特征\n\n### ViT 劣势\n- 推理速度慢（比 ResNet 慢 2-3x）\n- 对小目标感知不如 CNN\n\n### 折中方案\n- MobileViT: 轻量级，适合实时导航\n- EfficientViT: 兼顾精度和速度\n\n### 实验计划\n用 ViT-B/16 + DINOv2 权重替代 ResNet-18，预期 +3-5% SR',
            tags=json.dumps(['ViT', 'Transformer', '导航', '论文']), created_at=NOW - 12 * DAY, source_session_id=14),
        OpenClawDocument(id=10, title='会议纪要：中期汇报准备', type='meeting_note',
            content='## 组会纪要 - 2026.03.12\n\n### 中期汇报内容规划\n1. **研究进展**：PPO 导航基线 81% SR\n2. **sim2real 方案**：三层 DR 设计\n3. **下一步计划**：ViT 编码器 + DD-PPO\n\n### 导师反馈\n- 建议加入 object navigation 任务\n- sim2real 实验要有真实机器人数据\n- 论文投稿目标：IROS 2026\n\n### 时间节点\n- 3月底：完成 DR 实验\n- 4月中：完成 ViT 实验\n- 5月初：论文初稿\n- 5月15日：IROS 截稿',
            tags=json.dumps(['组会', '中期汇报', '计划']), created_at=NOW - 7 * DAY, source_session_id=6),
    ]
    db.add_all(documents)


def _seed_patterns(db):
    patterns = [
        BehaviorPattern(
            id=1, name='实验前先写测试', category='coding',
            description='在实现新的 RL 算法或策略网络前，先编写评估测试用例，确保实验可复现',
            confidence=92, evidence_count=47,
            learned_from='分析 30 天内 pytest 调用和代码提交顺序',
            rule='新实验代码必须先有对应的 test_*.py 文件',
            created_at=NOW - 25 * DAY, status='exportable',
            evolution=json.dumps([
                {'date': '03-01', 'confidence': 15, 'event_description': '首次观察到 test 文件先于实现文件创建'},
                {'date': '03-03', 'confidence': 22, 'event_description': '第二次观察到相同模式'},
                {'date': '03-05', 'confidence': 35, 'event_description': '连续 3 天遵循 test-first 模式'},
                {'date': '03-07', 'confidence': 42, 'event_description': '在 nav_planner 模块中再次确认'},
                {'date': '03-10', 'confidence': 58, 'event_description': 'OpenClaw TDD 引导会话确认了该模式'},
                {'date': '03-12', 'confidence': 65, 'event_description': '开始在新项目中主动使用'},
                {'date': '03-14', 'confidence': 75, 'event_description': '在 grasp-policy 项目中也观察到相同模式'},
                {'date': '03-16', 'confidence': 82, 'event_description': 'sim2real 项目也遵循该模式'},
                {'date': '03-17', 'confidence': 87, 'event_description': '跨项目一致性验证通过'},
                {'date': '03-19', 'confidence': 92, 'event_description': '30 天内 47 次证据，模式稳定'},
            ]),
            rules=json.dumps([
                {'id': 1, 'name': '测试文件命名', 'description': '测试文件必须以 test_ 开头', 'trigger': '创建新的 .py 文件', 'action': '检查是否存在对应的 test_ 文件', 'example': 'test_ppo_agent.py 对应 ppo_agent.py'},
                {'id': 2, 'name': '测试先行', 'description': '测试文件的创建时间必须早于实现文件', 'trigger': 'git commit 包含新模块', 'action': '验证 test 文件 commit 时间更早', 'example': 'test_reward.py 在 reward.py 之前提交'},
                {'id': 3, 'name': '覆盖率检查', 'description': '新模块的测试覆盖率不低于 80%', 'trigger': 'pytest 执行完成', 'action': '检查 coverage 报告', 'example': 'pytest --cov=nav_planner --cov-fail-under=80'},
            ]),
            executions=json.dumps([
                {'id': 1, 'pattern_id': 1, 'timestamp': NOW - 2 * DAY, 'trigger_event': '创建 reward_shaping.py', 'action_taken': '检测到 test_reward_shaping.py 已存在', 'result': 'success'},
                {'id': 2, 'pattern_id': 1, 'timestamp': NOW - 4 * DAY, 'trigger_event': '创建 path_smoother.py', 'action_taken': 'TDD 引导先创建测试', 'result': 'success'},
                {'id': 3, 'pattern_id': 1, 'timestamp': NOW - 6 * DAY, 'trigger_event': '创建 visual_encoder.py', 'action_taken': '未检测到测试文件，提醒用户', 'result': 'modified'},
            ]),
            applicable_scenarios=json.dumps(['新 RL 算法实现', '策略网络开发', '工具函数编写', '数据处理模块']),
        ),
        BehaviorPattern(
            id=2, name='Conventional Commits 规范', category='git',
            description='所有 Git 提交使用 feat/fix/refactor/docs/test 前缀，保持提交历史清晰',
            confidence=88, evidence_count=156,
            learned_from='分析 30 天内 Git 提交记录',
            rule='提交信息必须以 feat:|fix:|refactor:|docs:|test:|chore: 开头',
            created_at=NOW - 28 * DAY, status='exportable',
            evolution=json.dumps([
                {'date': '02-20', 'confidence': 20, 'event_description': '发现大部分提交遵循 conventional commits'},
                {'date': '02-23', 'confidence': 30, 'event_description': '统计 30 次提交，25 次符合规范'},
                {'date': '02-25', 'confidence': 45, 'event_description': '统计 50 次提交，42 次符合规范'},
                {'date': '02-28', 'confidence': 55, 'event_description': '开始在所有项目中使用'},
                {'date': '03-02', 'confidence': 65, 'event_description': '100 次提交中 89 次符合'},
                {'date': '03-06', 'confidence': 72, 'event_description': '不符合的主要是 WIP 类型'},
                {'date': '03-10', 'confidence': 80, 'event_description': '不符合的提交主要是 WIP 类型'},
                {'date': '03-14', 'confidence': 85, 'event_description': '开始自动提示不规范的提交'},
                {'date': '03-18', 'confidence': 88, 'event_description': '156 次提交验证，模式确认'},
            ]),
            rules=json.dumps([
                {'id': 4, 'name': '前缀检查', 'description': '提交信息必须以规范前缀开头', 'trigger': 'git commit', 'action': '检查 commit message 格式', 'example': 'feat: add PPO reward shaping'},
                {'id': 5, 'name': '范围标注', 'description': '建议在前缀后加范围', 'trigger': 'git commit', 'action': '提示添加 scope', 'example': 'fix(nav): resolve tf2 timeout'},
                {'id': 6, 'name': 'WIP 提醒', 'description': 'WIP 提交需要在合并前 squash', 'trigger': 'git merge', 'action': '检查是否有 WIP 提交', 'example': 'WIP 提交应在 merge 前整理'},
            ]),
            executions=json.dumps([
                {'id': 4, 'pattern_id': 2, 'timestamp': NOW - DAY, 'trigger_event': 'git commit "add new feature"', 'action_taken': '提示缺少前缀，建议改为 feat:', 'result': 'modified'},
                {'id': 5, 'pattern_id': 2, 'timestamp': NOW - 2 * DAY, 'trigger_event': 'git commit "feat: add DR module"', 'action_taken': '格式正确，通过', 'result': 'success'},
            ]),
            applicable_scenarios=json.dumps(['所有 Git 项目', '团队协作', '开源贡献', 'CI/CD 集成']),
        ),
        BehaviorPattern(
            id=3, name='实验结果即时记录', category='collaboration',
            description='每次实验完成后立即通过 OpenClaw 生成总结并写入知识库，不拖延',
            confidence=78, evidence_count=23,
            learned_from='分析 OpenClaw 实验总结会话和知识库写入时间',
            rule='实验完成后 30 分钟内必须生成总结文档',
            created_at=NOW - 20 * DAY, status='confirmed',
            evolution=json.dumps([
                {'date': '03-01', 'confidence': 10, 'event_description': '首次观察到实验后立即调用 OpenClaw 总结'},
                {'date': '03-04', 'confidence': 20, 'event_description': '第二次观察到相同行为'},
                {'date': '03-06', 'confidence': 30, 'event_description': '5 次实验中 3 次在 30 分钟内总结'},
                {'date': '03-09', 'confidence': 42, 'event_description': '开始形成习惯'},
                {'date': '03-12', 'confidence': 55, 'event_description': '知识库文档创建时间与实验结束时间高度相关'},
                {'date': '03-14', 'confidence': 63, 'event_description': '连续 5 天保持即时记录'},
                {'date': '03-16', 'confidence': 70, 'event_description': '连续一周保持即时记录习惯'},
                {'date': '03-19', 'confidence': 78, 'event_description': '23 次证据，模式基本确认'},
            ]),
            rules=json.dumps([
                {'id': 7, 'name': '时间窗口', 'description': '实验结束后 30 分钟内生成总结', 'trigger': '训练脚本执行完成', 'action': '提醒用户记录实验结果', 'example': 'PPO 训练完成 → 提醒生成总结'},
                {'id': 8, 'name': '模板使用', 'description': '使用标准实验总结模板', 'trigger': 'OpenClaw 总结会话', 'action': '自动填充实验参数', 'example': '自动提取 lr, epochs, metrics'},
            ]),
            executions=json.dumps([
                {'id': 6, 'pattern_id': 3, 'timestamp': NOW - DAY, 'trigger_event': 'PPO-v2 训练完成', 'action_taken': '30 分钟内生成实验总结', 'result': 'success'},
                {'id': 7, 'pattern_id': 3, 'timestamp': NOW - 3 * DAY, 'trigger_event': 'SAC 训练完成', 'action_taken': '超过 30 分钟才记录', 'result': 'modified'},
            ]),
            applicable_scenarios=json.dumps(['RL 训练实验', '消融实验', '对比实验', '超参搜索']),
        ),
        BehaviorPattern(
            id=4, name='AI 辅助代码审查', category='review',
            description='在合并分支前通过 OpenClaw 进行代码审查，重点关注算法正确性和性能',
            confidence=83, evidence_count=34,
            learned_from='分析 OpenClaw code-review 调用与 Git merge 的时间关系',
            rule='合并前必须完成至少一次 OpenClaw 代码审查',
            created_at=NOW - 22 * DAY, status='exportable',
            evolution=json.dumps([
                {'date': '02-26', 'confidence': 18, 'event_description': '首次观察到 merge 前调用 code-review'},
                {'date': '03-01', 'confidence': 28, 'event_description': '第三次观察到相同模式'},
                {'date': '03-03', 'confidence': 40, 'event_description': '8 次 merge 中 6 次有 review'},
                {'date': '03-06', 'confidence': 50, 'event_description': '开始主动请求 review'},
                {'date': '03-08', 'confidence': 60, 'event_description': '开始在 grasp-policy 项目中也使用'},
                {'date': '03-11', 'confidence': 68, 'event_description': 'review 发现了 2 个关键 bug'},
                {'date': '03-14', 'confidence': 75, 'event_description': '跨项目验证，review 覆盖率 85%'},
                {'date': '03-17', 'confidence': 80, 'event_description': '团队成员也开始采用'},
                {'date': '03-19', 'confidence': 83, 'event_description': '34 次证据，模式稳定'},
            ]),
            rules=json.dumps([
                {'id': 9, 'name': 'merge 前审查', 'description': '合并分支前必须有 review 记录', 'trigger': 'git merge 或 PR 创建', 'action': '检查是否有对应的 review 会话', 'example': 'merge feat/ppo-reward 前需要 review'},
                {'id': 10, 'name': '关注点', 'description': '审查重点：算法正确性、性能、边界条件', 'trigger': 'OpenClaw code-review', 'action': '自动生成审查清单', 'example': '检查 reward 计算、梯度裁剪、OOM 风险'},
            ]),
            executions=json.dumps([
                {'id': 8, 'pattern_id': 4, 'timestamp': NOW - 3 * DAY, 'trigger_event': 'merge feat/visual-dr', 'action_taken': 'OpenClaw review 发现纹理随机化范围问题', 'result': 'success'},
                {'id': 9, 'pattern_id': 4, 'timestamp': NOW - 5 * DAY, 'trigger_event': 'merge fix/tf2-transform', 'action_taken': '快速修复，跳过了 review', 'result': 'skipped'},
            ]),
            applicable_scenarios=json.dumps(['分支合并', 'PR 审查', '算法实现验证', '性能关键代码']),
        ),
        BehaviorPattern(
            id=5, name='训练前环境检查', category='devops',
            description='启动 RL 训练前先检查 GPU 状态、磁盘空间和依赖版本，避免训练中断',
            confidence=65, evidence_count=18,
            learned_from='分析 nvidia-smi 和 train.py 的调用时序',
            rule='训练脚本启动前必须执行环境检查脚本',
            created_at=NOW - 15 * DAY, status='confirmed',
            evolution=json.dumps([
                {'date': '03-05', 'confidence': 12, 'event_description': '观察到训练前经常调用 nvidia-smi'},
                {'date': '03-07', 'confidence': 20, 'event_description': '发现还会检查磁盘空间'},
                {'date': '03-10', 'confidence': 30, 'event_description': '发现还会检查磁盘空间'},
                {'date': '03-12', 'confidence': 40, 'event_description': '一次 OOM 后检查频率增加'},
                {'date': '03-14', 'confidence': 48, 'event_description': '一次训练因 OOM 中断后，检查频率增加'},
                {'date': '03-16', 'confidence': 55, 'event_description': '开始编写自动检查脚本'},
                {'date': '03-18', 'confidence': 65, 'event_description': '18 次证据，模式逐渐稳定'},
            ]),
            rules=json.dumps([
                {'id': 11, 'name': 'GPU 检查', 'description': '检查 GPU 显存是否充足', 'trigger': '执行 train.py', 'action': '运行 nvidia-smi 检查', 'example': 'nvidia-smi 确认显存 > 8GB 可用'},
                {'id': 12, 'name': '磁盘检查', 'description': '检查磁盘空间是否充足', 'trigger': '执行 train.py', 'action': '检查 /data 分区剩余空间', 'example': 'df -h 确认 > 50GB 可用'},
                {'id': 13, 'name': '依赖版本', 'description': '确认关键依赖版本一致', 'trigger': '执行 train.py', 'action': '检查 PyTorch/CUDA 版本', 'example': 'python -c "import torch; print(torch.__version__)"'},
            ]),
            executions=json.dumps([
                {'id': 10, 'pattern_id': 5, 'timestamp': NOW - DAY, 'trigger_event': '启动 PPO 训练', 'action_taken': 'GPU 检查通过，开始训练', 'result': 'success'},
                {'id': 11, 'pattern_id': 5, 'timestamp': NOW - 3 * DAY, 'trigger_event': '启动 SAC 训练', 'action_taken': '发现 GPU 被占用，等待释放', 'result': 'modified'},
            ]),
            applicable_scenarios=json.dumps(['RL 训练', '模型评估', '大规模实验', '分布式训练']),
        ),
        BehaviorPattern(
            id=6, name='论文驱动开发', category='coding',
            description='新功能开发前先阅读相关论文，通过 OpenClaw 讨论后再编码实现',
            confidence=52, evidence_count=11,
            learned_from='分析 OpenClaw 论文讨论会话与后续代码提交的关联',
            rule='新算法实现前应有对应的论文分析会话',
            created_at=NOW - 10 * DAY, status='learning',
            evolution=json.dumps([
                {'date': '03-10', 'confidence': 15, 'event_description': '观察到 PointNav 论文讨论后开始编码'},
                {'date': '03-12', 'confidence': 25, 'event_description': 'sim2real DR 也是先看论文'},
                {'date': '03-14', 'confidence': 32, 'event_description': 'sim2real 方案也是先讨论论文再实现'},
                {'date': '03-16', 'confidence': 42, 'event_description': 'ViT 导航也遵循该模式'},
                {'date': '03-18', 'confidence': 52, 'event_description': '11 次证据，模式仍在学习中'},
            ]),
            rules=json.dumps([
                {'id': 14, 'name': '论文先行', 'description': '新算法实现前需要有论文分析', 'trigger': '创建新的算法模块', 'action': '检查是否有对应的论文讨论会话', 'example': 'PPO reward shaping 前先分析 PointNav 论文'},
            ]),
            executions=json.dumps([
                {'id': 12, 'pattern_id': 6, 'timestamp': NOW - 2 * DAY, 'trigger_event': '开始实现 ViT 编码器', 'action_taken': '检测到已有 ViT 论文讨论会话', 'result': 'success'},
            ]),
            applicable_scenarios=json.dumps(['新算法实现', '方案设计', '技术选型', '论文复现']),
        ),
        BehaviorPattern(
            id=7, name='Conda 环境隔离', category='devops',
            description='每个项目使用独立的 Conda 环境，避免依赖冲突',
            confidence=75, evidence_count=28,
            learned_from='分析 conda activate 调用和项目切换的关联',
            rule='切换项目时必须激活对应的 Conda 环境',
            created_at=NOW - 20 * DAY, status='confirmed',
            evolution=json.dumps([
                {'date': '03-01', 'confidence': 15, 'event_description': '观察到频繁使用 conda activate'},
                {'date': '03-05', 'confidence': 30, 'event_description': '每个项目对应不同环境'},
                {'date': '03-08', 'confidence': 45, 'event_description': '一次依赖冲突后更加严格'},
                {'date': '03-12', 'confidence': 58, 'event_description': '开始使用 environment.yml 管理'},
                {'date': '03-15', 'confidence': 68, 'event_description': '所有项目都有 environment.yml'},
                {'date': '03-18', 'confidence': 75, 'event_description': '28 次证据，模式确认'},
            ]),
            rules=json.dumps([
                {'id': 15, 'name': '环境切换', 'description': '切换项目时激活对应环境', 'trigger': 'cd 到项目目录', 'action': '自动 conda activate', 'example': 'cd embodied-nav → conda activate habitat'},
                {'id': 16, 'name': '环境文件', 'description': '每个项目必须有 environment.yml', 'trigger': '创建新项目', 'action': '生成 environment.yml', 'example': 'conda env export > environment.yml'},
            ]),
            executions=json.dumps([
                {'id': 13, 'pattern_id': 7, 'timestamp': NOW - DAY, 'trigger_event': '切换到 ros2-workspace', 'action_taken': '自动激活 ros2 环境', 'result': 'success'},
            ]),
            applicable_scenarios=json.dumps(['多项目开发', 'Python 项目', 'ML 实验', 'ROS2 开发']),
        ),
        BehaviorPattern(
            id=8, name='分支命名规范', category='git',
            description='分支名使用 feat/fix/exp 前缀加简短描述，保持仓库整洁',
            confidence=70, evidence_count=42,
            learned_from='分析 Git 分支创建和命名模式',
            rule='分支名必须以 feat/|fix/|exp/|refactor/ 开头',
            created_at=NOW - 18 * DAY, status='confirmed',
            evolution=json.dumps([
                {'date': '03-02', 'confidence': 18, 'event_description': '发现大部分分支遵循命名规范'},
                {'date': '03-06', 'confidence': 32, 'event_description': '统计 20 个分支，16 个符合'},
                {'date': '03-10', 'confidence': 48, 'event_description': '新增 exp/ 前缀用于实验分支'},
                {'date': '03-14', 'confidence': 60, 'event_description': '团队开始统一使用'},
                {'date': '03-18', 'confidence': 70, 'event_description': '42 次证据，模式确认'},
            ]),
            rules=json.dumps([
                {'id': 17, 'name': '前缀规范', 'description': '分支名必须有规范前缀', 'trigger': 'git checkout -b', 'action': '检查分支名格式', 'example': 'feat/ppo-reward, exp/domain-rand'},
            ]),
            executions=json.dumps([
                {'id': 14, 'pattern_id': 8, 'timestamp': NOW - 2 * DAY, 'trigger_event': 'git checkout -b new-feature', 'action_taken': '提示添加前缀', 'result': 'modified'},
            ]),
            applicable_scenarios=json.dumps(['所有 Git 项目', '团队协作', '实验管理']),
        ),
        BehaviorPattern(
            id=9, name='实验超参记录', category='collaboration',
            description='每次实验都完整记录超参数配置，使用 YAML 配置文件管理',
            confidence=60, evidence_count=15,
            learned_from='分析实验配置文件和训练脚本参数',
            rule='训练脚本必须从 YAML 配置文件读取超参数',
            created_at=NOW - 12 * DAY, status='learning',
            evolution=json.dumps([
                {'date': '03-08', 'confidence': 12, 'event_description': '观察到开始使用 config.yaml'},
                {'date': '03-11', 'confidence': 25, 'event_description': '多个实验使用配置文件'},
                {'date': '03-14', 'confidence': 40, 'event_description': '开始用 hydra 管理配置'},
                {'date': '03-17', 'confidence': 52, 'event_description': '配置文件覆盖率提升'},
                {'date': '03-19', 'confidence': 60, 'event_description': '15 次证据，模式学习中'},
            ]),
            rules=json.dumps([
                {'id': 18, 'name': '配置文件', 'description': '实验参数必须在配置文件中', 'trigger': '启动训练', 'action': '检查是否使用配置文件', 'example': 'python train.py --config configs/ppo_v2.yaml'},
            ]),
            executions=json.dumps([
                {'id': 15, 'pattern_id': 9, 'timestamp': NOW - DAY, 'trigger_event': '启动新实验', 'action_taken': '检测到使用命令行参数，建议改用配置文件', 'result': 'modified'},
            ]),
            applicable_scenarios=json.dumps(['RL 训练', '超参搜索', '消融实验', '可复现研究']),
        ),
        BehaviorPattern(
            id=10, name='代码提交前 lint 检查', category='coding',
            description='提交代码前运行 linter 和 type checker，确保代码质量',
            confidence=45, evidence_count=9,
            learned_from='分析 flake8/mypy 调用与 git commit 的时序关系',
            rule='提交前必须通过 flake8 和 mypy 检查',
            created_at=NOW - 8 * DAY, status='learning',
            evolution=json.dumps([
                {'date': '03-12', 'confidence': 10, 'event_description': '首次观察到提交前运行 flake8'},
                {'date': '03-15', 'confidence': 22, 'event_description': '开始加入 mypy 检查'},
                {'date': '03-17', 'confidence': 35, 'event_description': '在 pre-commit hook 中配置'},
                {'date': '03-19', 'confidence': 45, 'event_description': '9 次证据，模式学习中'},
            ]),
            rules=json.dumps([
                {'id': 19, 'name': 'lint 检查', 'description': '提交前运行 flake8', 'trigger': 'git commit', 'action': '执行 flake8 检查', 'example': 'flake8 src/ --max-line-length=120'},
            ]),
            executions=json.dumps([
                {'id': 16, 'pattern_id': 10, 'timestamp': NOW - DAY, 'trigger_event': 'git commit', 'action_taken': 'flake8 发现 2 个问题，已修复', 'result': 'success'},
            ]),
            applicable_scenarios=json.dumps(['Python 项目', '代码提交', 'CI/CD']),
        ),
        BehaviorPattern(
            id=99, name='代码开发与Git提交规范 (完整工作流)', category='git',
            description='ShrimpFlow 从开发者日常编码中学习到的完整行为规范：包括仓库初始化、分支管理、PR 驱动合并、迭代开发循环、Conventional Commits、代码审查流程。该模式已被验证可自主驱动完整项目开发。',
            confidence=96, evidence_count=312,
            learned_from='分析 60 天内全量 Git 操作、代码编辑、PR 流程和 OpenClaw 协作记录',
            rule='遵循完整的代码开发生命周期：初始化 → 分支开发 → 测试 → PR 审查 → 合并 → 发布',
            created_at=NOW - 60 * DAY, status='exportable',
            evolution=json.dumps([
                {'date': '01-20', 'confidence': 8, 'event_description': '首次观察到仓库初始化遵循固定模板'},
                {'date': '01-25', 'confidence': 15, 'event_description': '发现分支命名遵循 feat/fix/exp 前缀'},
                {'date': '02-01', 'confidence': 25, 'event_description': '确认 PR 驱动的合并工作流'},
                {'date': '02-05', 'confidence': 35, 'event_description': '迭代开发循环模式初步成型'},
                {'date': '02-10', 'confidence': 45, 'event_description': '跨项目验证：embodied-nav 和 grasp-policy 一致'},
                {'date': '02-15', 'confidence': 55, 'event_description': 'Conventional Commits 规范与分支策略关联确认'},
                {'date': '02-20', 'confidence': 65, 'event_description': '代码审查流程模式稳定'},
                {'date': '02-25', 'confidence': 72, 'event_description': 'sim2real-transfer 项目完整验证'},
                {'date': '03-01', 'confidence': 80, 'event_description': '200+ 次证据累积，模式高度稳定'},
                {'date': '03-05', 'confidence': 85, 'event_description': '自主执行验证：成功驱动 OmniStack 项目开发'},
                {'date': '03-10', 'confidence': 90, 'event_description': '完整项目生命周期验证通过'},
                {'date': '03-15', 'confidence': 96, 'event_description': '312 条证据，模式确认可导出'},
            ]),
            rules=json.dumps([
                {'id': 100, 'name': '仓库初始化模板', 'description': '新项目必须包含 README、.gitignore、LICENSE、CI 配置', 'trigger': '创建新仓库', 'action': '按模板初始化项目结构', 'example': 'git init + 模板文件生成'},
                {'id': 101, 'name': '分支命名规范', 'description': '功能分支 feat/、修复分支 fix/、实验分支 exp/', 'trigger': '创建新分支', 'action': '检查分支名前缀', 'example': 'feat/ppo-reward, fix/tf2-transform, exp/domain-rand'},
                {'id': 102, 'name': 'PR 驱动合并', 'description': '所有代码变更必须通过 PR 合并，禁止直接 push main', 'trigger': '代码准备合并', 'action': '创建 PR 并请求审查', 'example': 'gh pr create --title "feat: add reward shaping"'},
                {'id': 103, 'name': '迭代开发循环', 'description': '每个迭代包含：编码 → 测试 → 审查 → 合并 → 部署', 'trigger': '开始新迭代', 'action': '按循环步骤执行', 'example': '迭代 1-4 完成后合并 PR'},
                {'id': 104, 'name': 'Commit Message 规范', 'description': '使用 feat/fix/refactor/docs/test/chore 前缀', 'trigger': 'git commit', 'action': '验证 commit message 格式', 'example': 'feat: implement SAC algorithm for continuous control'},
            ]),
            executions=json.dumps([
                {'id': 100, 'pattern_id': 99, 'timestamp': NOW - 1 * DAY, 'trigger_event': '自主开发 OmniStack 项目', 'action_taken': '完整执行仓库初始化 → 迭代开发 → PR 合并流程', 'result': 'success'},
                {'id': 101, 'pattern_id': 99, 'timestamp': NOW - 3 * DAY, 'trigger_event': '新建 sim2real-transfer 分支', 'action_taken': '自动使用 exp/ 前缀命名', 'result': 'success'},
                {'id': 102, 'pattern_id': 99, 'timestamp': NOW - 5 * DAY, 'trigger_event': 'PR #42 代码审查', 'action_taken': '按审查流程完成 review 并合并', 'result': 'success'},
            ]),
            applicable_scenarios=json.dumps(['新项目启动', '团队协作开发', '开源项目管理', 'CI/CD 流水线', '代码质量保障']),
        ),
        BehaviorPattern(
            id=11, name='AI 辅助开发规范', category='coding',
            description='使用 Claude Code/Copilot 等 AI 工具辅助开发时遵循的最佳实践：先描述意图再生成代码，审查 AI 输出，保持人工主导',
            confidence=72, evidence_count=31,
            learned_from='分析 OpenClaw 会话、Copilot 接受率和 AI 生成代码的后续修改记录',
            rule='AI 生成的代码必须经过人工审查和测试后才能合并',
            created_at=NOW - 18 * DAY, status='confirmed',
            evolution=json.dumps([
                {'date': '02-28', 'confidence': 10, 'event_description': '首次观察到使用 AI 生成代码前先写注释描述意图'},
                {'date': '03-03', 'confidence': 20, 'event_description': '发现 Copilot 建议接受后都会手动修改'},
                {'date': '03-07', 'confidence': 35, 'event_description': 'OpenClaw 会话中反复确认 AI 输出的正确性'},
                {'date': '03-11', 'confidence': 50, 'event_description': '开始在 prompt 中加入项目上下文和约束条件'},
                {'date': '03-15', 'confidence': 62, 'event_description': 'AI 生成代码的测试覆盖率与手写代码一致'},
                {'date': '03-19', 'confidence': 72, 'event_description': '31 次证据，AI 辅助开发流程趋于稳定'},
            ]),
            rules=json.dumps([
                {'id': 20, 'name': '意图先行', 'description': '使用 AI 生成代码前先用注释描述意图和约束', 'trigger': '调用 AI 代码生成', 'action': '检查是否有上下文描述', 'example': '# 实现 PPO 的 GAE 优势估计，支持 batch 并行'},
                {'id': 21, 'name': 'AI 输出审查', 'description': 'AI 生成的代码必须逐行审查', 'trigger': 'AI 代码生成完成', 'action': '标记需要审查的代码段', 'example': '检查 AI 生成的 reward 计算逻辑是否正确'},
                {'id': 22, 'name': 'AI 代码测试', 'description': 'AI 生成的代码必须有对应测试', 'trigger': 'AI 代码合入', 'action': '检查是否有测试覆盖', 'example': 'AI 生成的 utils 函数必须有 unit test'},
            ]),
            executions=json.dumps([
                {'id': 17, 'pattern_id': 11, 'timestamp': NOW - 2 * DAY, 'trigger_event': 'Copilot 生成 reward shaping 函数', 'action_taken': '审查发现 discount factor 计算有误，手动修正', 'result': 'modified'},
                {'id': 18, 'pattern_id': 11, 'timestamp': NOW - 5 * DAY, 'trigger_event': 'OpenClaw 生成数据预处理管道', 'action_taken': '代码审查通过，补充了边界测试', 'result': 'success'},
            ]),
            applicable_scenarios=json.dumps(['AI 辅助编码', 'Copilot 使用', 'OpenClaw 代码生成', '代码补全审查', 'prompt 工程']),
        ),
        BehaviorPattern(
            id=12, name='文档驱动开发', category='collaboration',
            description='先编写设计文档和 API 说明再开始编码，确保团队对需求和接口达成共识后再实现',
            confidence=58, evidence_count=14,
            learned_from='分析 Markdown 文档创建时间与对应代码文件创建时间的先后关系',
            rule='新模块开发前必须先有设计文档或 API 说明',
            created_at=NOW - 14 * DAY, status='learning',
            evolution=json.dumps([
                {'date': '03-06', 'confidence': 8, 'event_description': '首次观察到 README 先于代码创建'},
                {'date': '03-09', 'confidence': 18, 'event_description': '发现 API 文档在接口实现前完成'},
                {'date': '03-12', 'confidence': 30, 'event_description': 'sim2real 模块的设计文档先于代码 3 天'},
                {'date': '03-15', 'confidence': 42, 'event_description': '开始使用 ADR 记录架构决策'},
                {'date': '03-18', 'confidence': 58, 'event_description': '14 次证据，文档先行模式逐渐形成'},
            ]),
            rules=json.dumps([
                {'id': 23, 'name': '设计文档先行', 'description': '新模块必须先有 design.md', 'trigger': '创建新模块目录', 'action': '检查是否存在设计文档', 'example': 'nav_planner/design.md 先于 nav_planner/planner.py'},
                {'id': 24, 'name': 'API 文档同步', 'description': 'API 变更时文档必须同步更新', 'trigger': '修改公开接口', 'action': '检查文档是否更新', 'example': '修改 train() 参数后更新 API.md'},
            ]),
            executions=json.dumps([
                {'id': 19, 'pattern_id': 12, 'timestamp': NOW - 3 * DAY, 'trigger_event': '创建 visual_encoder 模块', 'action_taken': '检测到设计文档已存在，符合规范', 'result': 'success'},
                {'id': 20, 'pattern_id': 12, 'timestamp': NOW - 6 * DAY, 'trigger_event': '创建 reward_utils 模块', 'action_taken': '未检测到设计文档，提醒用户先写文档', 'result': 'modified'},
            ]),
            applicable_scenarios=json.dumps(['新模块开发', 'API 设计', '架构决策', '团队协作']),
        ),
        BehaviorPattern(
            id=13, name='安全审计习惯', category='review',
            description='代码提交前进行安全检查，包括敏感信息扫描、依赖漏洞检测和权限验证',
            confidence=80, evidence_count=38,
            learned_from='分析 git-secrets、safety 扫描调用与 git commit 的时序关系',
            rule='提交前必须通过安全扫描，禁止提交含敏感信息的代码',
            created_at=NOW - 22 * DAY, status='confirmed',
            evolution=json.dumps([
                {'date': '02-26', 'confidence': 12, 'event_description': '首次观察到提交前运行 git-secrets scan'},
                {'date': '03-01', 'confidence': 22, 'event_description': '发现还会运行 safety check 检查依赖漏洞'},
                {'date': '03-05', 'confidence': 35, 'event_description': '一次 API key 泄漏事件后检查频率大幅增加'},
                {'date': '03-09', 'confidence': 50, 'event_description': '在 pre-commit hook 中集成安全扫描'},
                {'date': '03-13', 'confidence': 65, 'event_description': '开始使用 .gitignore 模板排除敏感文件'},
                {'date': '03-17', 'confidence': 80, 'event_description': '38 次证据，安全检查已成为固定流程'},
            ]),
            rules=json.dumps([
                {'id': 25, 'name': '敏感信息扫描', 'description': '提交前扫描代码中的密钥和凭证', 'trigger': 'git commit', 'action': '运行 git-secrets scan', 'example': 'git secrets --scan 检查 API key 泄漏'},
                {'id': 26, 'name': '依赖漏洞检测', 'description': '定期检查依赖库的已知漏洞', 'trigger': '更新 requirements.txt', 'action': '运行 safety check', 'example': 'safety check -r requirements.txt'},
                {'id': 27, 'name': '权限最小化', 'description': '配置文件中的权限必须遵循最小化原则', 'trigger': '修改配置文件', 'action': '审查权限设置', 'example': 'API token 只授予必要的 scope'},
            ]),
            executions=json.dumps([
                {'id': 21, 'pattern_id': 13, 'timestamp': NOW - DAY, 'trigger_event': 'git commit 包含 .env 引用', 'action_taken': '安全扫描拦截，移除硬编码的 API key', 'result': 'success'},
                {'id': 22, 'pattern_id': 13, 'timestamp': NOW - 4 * DAY, 'trigger_event': '更新 requirements.txt', 'action_taken': 'safety check 发现 Pillow 存在 CVE，升级版本', 'result': 'modified'},
            ]),
            applicable_scenarios=json.dumps(['代码提交', '依赖更新', '配置文件修改', '密钥管理', 'CI/CD 安全门禁']),
        ),
        BehaviorPattern(
            id=14, name='性能监控规范', category='devops',
            description='持续监控训练和推理的性能指标，设置告警阈值，在性能退化时及时发现并优化',
            confidence=68, evidence_count=22,
            learned_from='分析 TensorBoard 日志、W&B 面板访问和性能优化提交的关联',
            rule='训练过程必须有实时性能监控，关键指标设置告警阈值',
            created_at=NOW - 16 * DAY, status='confirmed',
            evolution=json.dumps([
                {'date': '03-04', 'confidence': 10, 'event_description': '观察到训练时频繁查看 TensorBoard'},
                {'date': '03-07', 'confidence': 22, 'event_description': '发现会在 W&B 中设置 alert'},
                {'date': '03-10', 'confidence': 35, 'event_description': '一次训练 loss 爆炸后开始设置早停机制'},
                {'date': '03-13', 'confidence': 48, 'event_description': '开始记录 GPU 利用率和内存占用'},
                {'date': '03-16', 'confidence': 58, 'event_description': '编写了自动化性能报告脚本'},
                {'date': '03-19', 'confidence': 68, 'event_description': '22 次证据，性能监控流程基本成型'},
            ]),
            rules=json.dumps([
                {'id': 28, 'name': '指标记录', 'description': '训练过程必须记录 loss、reward、GPU 利用率等关键指标', 'trigger': '启动训练脚本', 'action': '检查是否配置了监控工具', 'example': 'wandb.init(project="ppo-nav") 记录训练指标'},
                {'id': 29, 'name': '告警阈值', 'description': '关键指标必须设置告警阈值', 'trigger': '训练过程中', 'action': '检查指标是否超出阈值', 'example': 'loss > 10.0 或 GPU 利用率 < 30% 时告警'},
            ]),
            executions=json.dumps([
                {'id': 23, 'pattern_id': 14, 'timestamp': NOW - 2 * DAY, 'trigger_event': 'PPO 训练 loss 突增', 'action_taken': 'W&B alert 触发，自动保存 checkpoint 并通知', 'result': 'success'},
            ]),
            applicable_scenarios=json.dumps(['RL 训练监控', '模型推理性能', 'GPU 资源管理', '实验对比分析']),
        ),
        BehaviorPattern(
            id=15, name='代码复用模式', category='coding',
            description='将重复出现的逻辑抽象为可复用的工具函数和基类，跨项目共享通用组件',
            confidence=85, evidence_count=40,
            learned_from='分析跨项目的代码相似度和 utils 模块的引用频率',
            rule='相同逻辑出现 2 次以上必须抽象为公共模块',
            created_at=NOW - 24 * DAY, status='exportable',
            evolution=json.dumps([
                {'date': '02-24', 'confidence': 12, 'event_description': '发现多个项目中存在相似的数据加载代码'},
                {'date': '02-28', 'confidence': 25, 'event_description': '观察到开始将通用函数提取到 utils/'},
                {'date': '03-04', 'confidence': 40, 'event_description': '创建了跨项目共享的 common-utils 仓库'},
                {'date': '03-09', 'confidence': 55, 'event_description': '3 个项目开始引用 common-utils'},
                {'date': '03-14', 'confidence': 72, 'event_description': '抽象出通用的训练循环基类'},
                {'date': '03-19', 'confidence': 85, 'event_description': '40 次证据，复用模式已成为开发习惯'},
            ]),
            rules=json.dumps([
                {'id': 30, 'name': '重复检测', 'description': '相同逻辑出现 2 次以上必须抽象', 'trigger': '代码审查或新增代码', 'action': '检查是否有重复逻辑', 'example': '两个项目都有 normalize_obs()，应提取到 common-utils'},
                {'id': 31, 'name': '通用模块管理', 'description': '公共模块必须有文档和版本管理', 'trigger': '修改 common-utils', 'action': '更新版本号和 CHANGELOG', 'example': 'common-utils v1.2.0 新增 reward_utils'},
                {'id': 32, 'name': '接口稳定性', 'description': '公共模块的接口变更必须向后兼容', 'trigger': '修改公共接口', 'action': '检查是否有 breaking change', 'example': '新增参数使用默认值保持兼容'},
            ]),
            executions=json.dumps([
                {'id': 24, 'pattern_id': 15, 'timestamp': NOW - DAY, 'trigger_event': '在 sim2real 中发现与 embodied-nav 相同的坐标变换代码', 'action_taken': '提取到 common-utils/transforms.py', 'result': 'success'},
                {'id': 25, 'pattern_id': 15, 'timestamp': NOW - 4 * DAY, 'trigger_event': '代码审查发现重复的日志格式化逻辑', 'action_taken': '抽象为 common-utils/logging_utils.py', 'result': 'success'},
            ]),
            applicable_scenarios=json.dumps(['跨项目开发', '工具函数编写', '基类设计', '代码审查', '技术债务清理']),
        ),
        BehaviorPattern(
            id=16, name='持续集成规范', category='devops',
            description='维护 CI/CD 流水线，确保每次提交都经过自动化测试、lint 检查和构建验证',
            confidence=40, evidence_count=8,
            learned_from='分析 GitHub Actions 配置变更和 CI 失败后的修复行为',
            rule='每个项目必须配置 CI 流水线，PR 合并前必须通过所有 CI 检查',
            created_at=NOW - 10 * DAY, status='learning',
            evolution=json.dumps([
                {'date': '03-10', 'confidence': 8, 'event_description': '首次观察到为项目配置 GitHub Actions'},
                {'date': '03-13', 'confidence': 18, 'event_description': '在 CI 中加入 pytest 和 flake8'},
                {'date': '03-15', 'confidence': 25, 'event_description': 'CI 失败后立即修复而非跳过'},
                {'date': '03-18', 'confidence': 40, 'event_description': '8 次证据，CI 规范仍在学习中'},
            ]),
            rules=json.dumps([
                {'id': 33, 'name': 'CI 配置', 'description': '每个项目必须有 CI 配置文件', 'trigger': '创建新项目', 'action': '生成 .github/workflows/ci.yml', 'example': 'GitHub Actions 配置 pytest + flake8 + mypy'},
                {'id': 34, 'name': 'CI 门禁', 'description': 'PR 合并前必须通过所有 CI 检查', 'trigger': '创建 PR', 'action': '检查 CI 状态', 'example': 'CI 红灯时禁止合并 PR'},
            ]),
            executions=json.dumps([
                {'id': 26, 'pattern_id': 16, 'timestamp': NOW - 2 * DAY, 'trigger_event': 'PR #38 CI 失败', 'action_taken': '修复 flake8 报错后重新触发 CI', 'result': 'success'},
            ]),
            applicable_scenarios=json.dumps(['新项目配置', 'PR 合并流程', 'CI 失败修复']),
        ),
        BehaviorPattern(
            id=17, name='知识沉淀模式', category='collaboration',
            description='将开发过程中的经验教训、踩坑记录和最佳实践沉淀为团队知识库文档，便于传承和复用',
            confidence=92, evidence_count=45,
            learned_from='分析知识库文档创建频率、内容更新记录和团队成员引用情况',
            rule='重要的技术决策、踩坑经验和最佳实践必须在 24 小时内写入知识库',
            created_at=NOW - 26 * DAY, status='exportable',
            evolution=json.dumps([
                {'date': '02-22', 'confidence': 10, 'event_description': '首次观察到调试完成后写入踩坑记录'},
                {'date': '02-26', 'confidence': 22, 'event_description': '发现技术选型后会写决策文档'},
                {'date': '03-02', 'confidence': 38, 'event_description': '知识库文档开始被其他成员引用'},
                {'date': '03-07', 'confidence': 55, 'event_description': '建立了知识库模板和分类体系'},
                {'date': '03-12', 'confidence': 72, 'event_description': '新人入职时直接参考知识库上手'},
                {'date': '03-19', 'confidence': 92, 'event_description': '45 次证据，知识沉淀已成为团队文化'},
            ]),
            rules=json.dumps([
                {'id': 35, 'name': '及时记录', 'description': '重要经验必须在 24 小时内写入知识库', 'trigger': '解决复杂问题或做出技术决策', 'action': '创建知识库文档', 'example': '解决 CUDA OOM 后写入 GPU 内存优化指南'},
                {'id': 36, 'name': '模板规范', 'description': '知识库文档使用统一模板', 'trigger': '创建知识库文档', 'action': '使用标准模板填写', 'example': '模板包含：问题描述、原因分析、解决方案、参考链接'},
                {'id': 37, 'name': '定期回顾', 'description': '每周回顾知识库，更新过时内容', 'trigger': '每周五', 'action': '检查知识库文档时效性', 'example': '更新 PyTorch 版本升级后的兼容性说明'},
            ]),
            executions=json.dumps([
                {'id': 27, 'pattern_id': 17, 'timestamp': NOW - DAY, 'trigger_event': '解决 ROS2 tf2 坐标变换超时问题', 'action_taken': '在知识库中创建 tf2 调试指南', 'result': 'success'},
                {'id': 28, 'pattern_id': 17, 'timestamp': NOW - 3 * DAY, 'trigger_event': '完成 sim2real 方案选型', 'action_taken': '写入技术决策文档，记录选型理由和对比分析', 'result': 'success'},
            ]),
            applicable_scenarios=json.dumps(['问题排查总结', '技术决策记录', '新人入职指南', '最佳实践沉淀', '踩坑经验分享']),
        ),
    ]
    db.add_all(patterns)


def _seed_workflows(db):
    workflows = [
        TeamWorkflow(id=1, name='具身智能实验规范',
            description='包含实验前测试、结果即时记录和代码审查流程，适用于 RL 实验开发',
            patterns=json.dumps([1, 3, 4]), target_team='具身智能实验室', status='active', created_at=NOW - 5 * DAY),
        TeamWorkflow(id=2, name='ROS2 开发流程',
            description='训练前环境检查和 Git 规范，确保机器人软件开发质量',
            patterns=json.dumps([2, 5, 7]), target_team='机器人开发组', status='distributed', created_at=NOW - 3 * DAY),
        TeamWorkflow(id=3, name='新人入职研究指南',
            description='整合所有核心研究模式，帮助新同学快速融入实验室研究节奏',
            patterns=json.dumps([1, 2, 3, 4, 6]), target_team='全体成员', status='draft', created_at=NOW - DAY),
        TeamWorkflow(id=4, name='论文写作工作流',
            description='从实验到论文的完整流程：实验记录 → 数据整理 → 论文撰写 → 代码审查',
            patterns=json.dumps([3, 6, 9]), target_team='研究生', status='active', created_at=NOW - 4 * DAY),
        TeamWorkflow(id=5, name='AI 项目启动模板',
            description='新 AI 项目的标准启动流程：环境隔离 → 分支规范 → TDD → 代码审查',
            patterns=json.dumps([1, 2, 7, 8, 10]), target_team='AI 开发组', status='draft', created_at=NOW - 2 * DAY),
        TeamWorkflow(id=6, name='日常开发规范',
            description='日常编码的基本规范：Git 规范 + lint 检查 + 环境管理',
            patterns=json.dumps([2, 7, 8, 10]), target_team='全体成员', status='distributed', created_at=NOW - 6 * DAY),
    ]
    db.add_all(workflows)


def _seed_profiles(db):
    profiles = [
        SharedProfile(id=1, username='Peter Steinberger', avatar='PS', title='iOS 架构大师', bio='PSPDFKit 创始人，20年 iOS 开发经验', followers=12400, patterns_count=24),
        SharedProfile(id=2, username='Andrej Karpathy', avatar='AK', title='AI 研究员', bio='前 Tesla AI 总监，深度学习先驱', followers=89200, patterns_count=18),
        SharedProfile(id=3, username='Linus Torvalds', avatar='LT', title='Git 之父', bio='Linux 和 Git 创始人', followers=156000, patterns_count=12),
        SharedProfile(id=4, username='Pieter Abbeel', avatar='PA', title='机器人学教授', bio='UC Berkeley 教授，Covariant 联合创始人', followers=34500, patterns_count=15),
        SharedProfile(id=5, username='Chelsea Finn', avatar='CF', title='元学习专家', bio='Stanford 教授，MAML 作者', followers=28700, patterns_count=11),
        SharedProfile(id=6, username='Yann LeCun', avatar='YL', title='AI 先驱', bio='Meta AI 首席科学家，图灵奖得主', followers=210000, patterns_count=20),
        SharedProfile(id=7, username='Sergey Levine', avatar='SL', title='RL 专家', bio='UC Berkeley 教授，机器人 RL 先驱', followers=42100, patterns_count=16),
        SharedProfile(id=8, username='Fei-Fei Li', avatar='FL', title='计算机视觉专家', bio='Stanford HAI 联合主任，ImageNet 创始人', followers=67800, patterns_count=14),
    ]
    db.add_all(profiles)


# 简化的模式生成（用于社区分享包）
def _sp(pid, name, cat, desc, conf, rule):
    return {
        'id': pid, 'name': name, 'category': cat, 'description': desc,
        'confidence': conf, 'evidence_count': int(conf * 0.5),
        'learned_from': '社区分享', 'rule': rule, 'created_at': NOW - 30 * DAY,
        'status': 'exportable',
        'evolution': [{'date': '01-01', 'confidence': conf, 'event_description': '导入时已确认'}],
        'rules': [], 'executions': [], 'applicable_scenarios': [],
    }


def _seed_packs(db):
    packs = [
        SharedPatternPack(id=1, author_id=1, name="Peter's iOS Architecture Workflow",
            description='20年 iOS 开发经验总结的架构模式，包含 MVVM、依赖注入、模块化设计等最佳实践',
            category='coding', downloads=8420, stars=2150,
            tags=json.dumps(['iOS', 'Swift', '架构', 'MVVM']), created_at=NOW - 20 * DAY,
            patterns=json.dumps([
                _sp(101, 'MVVM 严格分层', 'coding', 'View 层不直接访问 Model，必须通过 ViewModel', 95, 'View 中禁止 import Model 层'),
                _sp(102, '依赖注入优先', 'coding', '所有依赖通过构造函数注入，不使用单例', 92, '禁止在类内部直接实例化依赖'),
                _sp(103, 'Protocol 驱动设计', 'coding', '核心接口先定义 Protocol，再实现具体类', 88, '新模块必须先有 Protocol 定义'),
            ])),
        SharedPatternPack(id=2, author_id=2, name='ML Research Best Practices',
            description='深度学习研究的最佳实践，从实验设计到论文写作的完整工作流',
            category='coding', downloads=15600, stars=4820,
            tags=json.dumps(['ML', '深度学习', '研究', '实验']), created_at=NOW - 15 * DAY,
            patterns=json.dumps([
                _sp(201, '实验可复现性', 'coding', '所有实验必须固定随机种子，记录完整环境信息', 96, '训练脚本必须设置 seed 并记录到日志'),
                _sp(202, '渐进式实验', 'coding', '从最简单的 baseline 开始，逐步增加复杂度', 94, '新想法先在小数据集上验证'),
                _sp(203, '消融实验规范', 'collaboration', '每个创新点必须有对应的消融实验', 91, '论文提交前必须完成所有消融实验'),
            ])),
        SharedPatternPack(id=3, author_id=3, name='Clean Git Workflow',
            description='Git 工作流的黄金标准，包含分支策略、提交规范和代码审查流程',
            category='git', downloads=32100, stars=9870,
            tags=json.dumps(['Git', '工作流', '分支', '规范']), created_at=NOW - 25 * DAY,
            patterns=json.dumps([
                _sp(301, '原子提交', 'git', '每个提交只做一件事，保持提交历史清晰', 98, '单个提交不超过 300 行改动'),
                _sp(302, '分支保护', 'git', 'main 分支禁止直接推送，必须通过 PR', 97, 'main 分支设置 branch protection'),
                _sp(303, 'Rebase 优先', 'git', '合并前先 rebase，保持线性历史', 90, 'merge 前执行 git rebase main'),
            ])),
        SharedPatternPack(id=4, author_id=4, name='Robotics RL Development',
            description='机器人强化学习开发的完整工作流，从仿真到真实部署',
            category='coding', downloads=6780, stars=1920,
            tags=json.dumps(['机器人', 'RL', 'sim2real', 'ROS']), created_at=NOW - 18 * DAY,
            patterns=json.dumps([
                _sp(401, 'Sim-first 开发', 'coding', '所有算法先在仿真中验证，再部署到真实机器人', 93, '真实部署前仿真 success rate > 90%'),
                _sp(402, 'Safety-aware RL', 'coding', '训练时加入安全约束，避免危险动作', 90, 'reward 中必须包含安全惩罚项'),
                _sp(403, 'DR 标准化', 'devops', 'Domain Randomization 参数必须可配置', 85, 'DR 参数通过 YAML 配置文件管理'),
            ])),
        SharedPatternPack(id=5, author_id=5, name='Meta-Learning Research Flow',
            description='元学习研究的标准流程，包含 few-shot 实验设计和评估规范',
            category='coding', downloads=4320, stars=1450,
            tags=json.dumps(['元学习', 'few-shot', 'MAML', '研究']), created_at=NOW - 12 * DAY,
            patterns=json.dumps([
                _sp(501, 'N-way K-shot 标准评估', 'coding', '使用标准的 N-way K-shot 评估协议', 95, '评估必须报告 5-way 1-shot 和 5-way 5-shot'),
                _sp(502, '置信区间报告', 'collaboration', '所有实验结果必须报告 95% 置信区间', 92, '至少运行 600 个 episode 计算置信区间'),
            ])),
        SharedPatternPack(id=6, author_id=6, name='Self-Supervised Learning Patterns',
            description='自监督学习的研究模式，包含对比学习、掩码预测等方法论',
            category='coding', downloads=21400, stars=6530,
            tags=json.dumps(['自监督', '对比学习', 'MAE', 'DINO']), created_at=NOW - 22 * DAY,
            patterns=json.dumps([
                _sp(601, '数据增强一致性', 'coding', '对比学习中两个 view 的增强策略必须一致', 94, '增强管道必须对称设计'),
                _sp(602, '线性探测评估', 'coding', '预训练模型必须用线性探测评估特征质量', 96, '冻结 backbone，只训练线性分类头'),
                _sp(603, '多尺度评估', 'review', '在多个下游任务上评估泛化能力', 88, '至少在 3 个不同任务上评估'),
            ])),
        SharedPatternPack(id=7, author_id=7, name='Robot RL from Scratch',
            description='从零开始的机器人 RL 开发指南，覆盖环境搭建到策略部署',
            category='devops', downloads=9870, stars=3210,
            tags=json.dumps(['机器人', 'RL', '教程', '部署']), created_at=NOW - 16 * DAY,
            patterns=json.dumps([
                _sp(701, '环境标准化', 'devops', '使用 Gym 接口封装所有环境', 95, '所有环境必须实现 reset/step/render'),
                _sp(702, '奖励工程', 'coding', '奖励函数必须可配置，支持消融', 90, '奖励各项权重通过配置文件管理'),
                _sp(703, '训练监控', 'devops', '训练过程必须有实时监控', 88, '使用 TensorBoard/W&B 记录所有指标'),
            ])),
        SharedPatternPack(id=8, author_id=8, name='Computer Vision Research Standards',
            description='计算机视觉研究的标准规范，从数据集准备到模型评估',
            category='coding', downloads=18900, stars=5670,
            tags=json.dumps(['CV', '视觉', '数据集', '评估']), created_at=NOW - 19 * DAY,
            patterns=json.dumps([
                _sp(801, '数据集划分规范', 'coding', 'train/val/test 严格分离，无数据泄漏', 97, '划分后验证无重叠样本'),
                _sp(802, '多指标评估', 'review', '不只看 accuracy，还要看 precision/recall/F1', 93, '评估报告必须包含混淆矩阵'),
                _sp(803, '可视化验证', 'review', '模型预测结果必须可视化检查', 90, '每次评估生成预测可视化样本'),
            ])),
    ]
    db.add_all(packs)


# 每日摘要模板
_SUMMARY_TEMPLATES = [
    '今天通过 OpenClaw 完成了 {openclaw} 次 AI 辅助研究，总共产生 {total} 个事件。主要集中在视觉导航策略训练和 ROS2 调试上。',
    '高效的一天！与 OpenClaw 进行了 {openclaw} 次交互，涵盖论文分析、RL 调参和仿真实验。共 {total} 个事件。',
    '今天重点使用 OpenClaw 进行 PPO 训练调试和代码审查，{openclaw} 次 AI 协作帮助解决了 reward shaping 问题。总事件 {total} 个。',
    '今天在 Habitat 仿真环境中完成了导航基线实验，OpenClaw 协助分析了 {openclaw} 次实验结果。总事件 {total} 个。',
]


def _seed_summaries(db, events):
    # 按日期聚合 events
    for i in range(30):
        day_offset = 29 - i
        day_start = NOW - day_offset * DAY
        day_end = day_start + DAY

        day_events = [e for e in events if day_start <= e.timestamp < day_end]
        dt = datetime.fromtimestamp(day_start, tz=timezone.utc)
        date_str = dt.strftime('%Y-%m-%d')

        project_counts = defaultdict(int)
        cmd_counts = defaultdict(int)
        openclaw_count = 0

        for e in day_events:
            project_counts[e.project] += 1
            if e.source == 'terminal':
                cmd = e.action.split(' ')[0]
                cmd_counts[cmd] += 1
            if e.source == 'openclaw':
                openclaw_count += 1

        top_projects = sorted(project_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_commands = sorted(cmd_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        total = len(day_events)
        if total == 0:
            ai_summary = '今天没有研究活动。'
        else:
            ai_summary = random.choice(_SUMMARY_TEMPLATES).format(openclaw=openclaw_count, total=total)

        db.add(DailySummary(
            date=date_str,
            event_count=total,
            top_projects=json.dumps([{'name': n, 'count': c} for n, c in top_projects]),
            top_commands=json.dumps([{'cmd': c, 'count': n} for c, n in top_commands]),
            ai_summary=ai_summary,
            openclaw_sessions=openclaw_count,
        ))


def seed_database():
    db = SessionLocal()
    try:
        # 已有数据则跳过
        if db.query(DevEvent).count() > 0:
            print("Database already seeded, skipping.")
            return

        print("Seeding database...")
        events = _seed_events(db)
        _seed_skills(db)
        _seed_summaries(db, events)
        _seed_sessions(db)
        _seed_documents(db)
        _seed_patterns(db)
        _seed_workflows(db)
        _seed_profiles(db)
        _seed_packs(db)
        db.commit()
        print("Database seeded successfully!")
    except Exception as e:
        db.rollback()
        print(f"Seed error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

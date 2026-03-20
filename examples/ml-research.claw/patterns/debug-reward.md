---
name: Reward 不收敛调试三板斧
confidence: very_high
category: debugging
trigger:
  when: "when RL training reward is not converging"
  event: error_encountered
  globs: ["**/train*.py", "**/rl/**/*.py"]
  context:
    - log contains 'reward' and ('nan' or 'diverge' or 'not converging')
    - training script is running or just failed
source: auto
evidence: 28
learned_from:
  - context: PPO 训练 CartPole reward 全为 0
    insight: 优先检查 reward function 是否正确连接到环境 step
    confidence: 0.95
  - context: SAC 训练 reward 出现 nan
    insight: nan 通常来自环境返回非法状态，检查 obs space 边界
    confidence: 0.88
---

# Reward 不收敛调试

训练 reward 不收敛时，按以下顺序排查。不要跳步，每步确认后再进下一步。

## 第一步：检查 reward scale

reward 的绝对值应该在合理范围内。如果 scale 太大（>100）或太小（<0.01），
归一化或调整 reward function。

```bash
python -c "
import torch
r = torch.load('rewards.pt')
print(f'mean: {r.mean():.4f}, std: {r.std():.4f}, min: {r.min():.4f}, max: {r.max():.4f}')
"
```

常见问题：
- reward 全是 0 → reward function 没接对
- reward 全是负数且很大 → penalty 项权重过高
- reward 有 nan → 环境 step 返回了非法状态

## 第二步：检查 episode length

episode 过短意味着 agent 很快就死了，学不到有效信号。

```bash
grep 'ep_len_mean' training.log | tail -20
```

如果 episode length < 50，考虑：
- 降低任务难度（curriculum learning）
- 增加 max_episode_steps
- 检查 done 条件是否过于严格

## 第三步：TensorBoard 对比 baseline

把当前 run 和已知正常的 baseline run 放在一起看。

```bash
tensorboard --logdir current:runs/current,baseline:runs/baseline --port 6006
```

重点对比：
- reward curve 的趋势（baseline 是上升的，当前是平的？）
- policy loss 的量级（差 10 倍以上说明学习率有问题）
- entropy（如果 entropy 快速降到 0，说明 policy 过早收敛）

## 如果三步都没找到问题

回到基础：
1. 用最简单的环境（CartPole）验证代码是否正确
2. 对比官方 example 的超参数
3. 检查 observation normalization 是否开启

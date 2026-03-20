---
name: 实验分支管理策略
confidence: very_high
category: git
trigger:
  when: "when starting a new ML experiment"
  globs: ["**/train*.py", "**/config*.yaml", "**/sweep*.yaml"]
  context:
    - project is a ML/RL training codebase
    - user mentions "experiment" or "try"
source: auto
evidence: 45
---

# 实验分支管理

每个实验用独立分支，训练完成后 squash merge 回 main。

## 分支命名

```
exp/<实验名>-<日期>
```

示例：`exp/reward-shaping-0315`、`exp/ppo-lr-sweep-0320`

## 工作流

1. 开始实验：
```bash
git checkout -b exp/reward-shaping-0315
```

2. 实验过程中正常 commit（不用太讲究 message）

3. 实验成功，合并回 main：
```bash
git checkout main
git merge --squash exp/reward-shaping-0315
git commit -m "feat: reward shaping 实验结果合入"
git tag exp-reward-shaping-v1
```

4. 实验失败，保留分支但不合并：
```bash
git tag exp-reward-shaping-failed
git checkout main
```

## 为什么用 squash merge

- main 的 history 保持干净（一个实验 = 一个 commit）
- 实验过程的细碎 commit 不污染主线
- tag 保留实验的完整历史，需要时可以回溯

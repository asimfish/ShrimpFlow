---
name: RL 实验全流程
steps:
  - pattern: exp-branch
  - inline: "检查 GPU 显存和 CUDA 版本是否匹配训练需求"
    when: before training starts
  - pattern: debug-reward
    when: training started and reward looks abnormal
  - pattern: post-ai-commit
    when: code modified with AI assistance
---

# RL 实验全流程

从创建实验分支、训练调试到代码提交的标准工作流。

```
exp-branch ──> [训练] ──> debug-reward ──> post-ai-commit
   │                         │                  │
   │ 创建 exp/ 分支          │ 三板斧调试        │ review + commit
   │ 隔离实验代码            │ 定位 reward 问题   │ 固化 AI 修改
```

## 使用方式

1. 开始新实验时，按 `exp-branch` 模式创建分支
2. 训练过程中如果 reward 异常，按 `debug-reward` 的三步排查
3. 如果用 Claude Code 辅助修改了代码，按 `post-ai-commit` 及时提交

## 自动化级别

当前：suggest（建议模式）
- AI 检测到相关场景时主动提醒，但不自动执行
- 用户确认后按模式执行

目标：semi_auto（半自动模式）
- 置信度全部达到 very_high 后可升级
- 分支创建和 commit 自动执行，调试步骤仍需人工确认

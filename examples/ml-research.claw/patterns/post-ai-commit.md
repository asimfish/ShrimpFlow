---
name: Claude Code 后必 commit
confidence: very_high
category: collaboration
trigger: "when AI-assisted code editing session ends"
source: auto
evidence: 100
---

使用 Claude Code 编辑代码后，立即 review 并 commit 变更。

## 为什么

AI 生成的代码需要及时固化为 git 快照，原因：
- 防止后续编辑覆盖 AI 的有效修改
- 保持 git history 的原子性（AI 编辑 = 一个 commit）
- 方便 revert（如果 AI 改错了，一个 commit 就能回滚）

## 怎么做

```bash
git diff --stat          # 先看改了什么
git add -p               # 交互式选择要 commit 的部分
git commit -m "feat: ..."  # 写清楚这次 AI 帮你做了什么
```

不要用 `git add .`，要逐个确认 AI 的每个修改。

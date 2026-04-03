---
name: lint-and-test
confidence: high
severity: high
category: [ci-cd, testing]
scope: task
trigger:
  event: pr_opened
  globs: ["**/*.ts", "**/*.tsx", "**/*.js"]
  when: "when a PR is opened or code is pushed to a feature branch"
params:
  lint_command:
    type: string
    default: "pnpm lint"
    description: lint 执行命令
  test_command:
    type: string
    default: "pnpm test --run"
    description: 测试执行命令
  coverage_threshold:
    type: number
    default: 80
    min: 0
    max: 100
    description: 最低覆盖率要求（百分比）
outputs:
  lint_passed:
    type: boolean
    description: lint 是否全部通过
    extract:
      method: last_line
  test_passed:
    type: boolean
    description: 测试是否全部通过
    extract:
      method: regex
      pattern: "Tests:\\s+(PASSED|FAILED)"
  coverage_percent:
    type: number
    description: 实际测试覆盖率
    extract:
      method: regex
      pattern: "Coverage:\\s+(\\d+\\.?\\d*)%"
  error_summary:
    type: string
    description: 失败时的错误摘要
    extract:
      method: regex
      pattern: "FAIL\\s+(.+)"
source: manual
---

# Lint & Test 质量门禁

PR 合并前必须通过 lint 和测试。不要跳过任何一步，即使"只改了一行"。

## 第一步：执行 Lint

```bash
<%params.lint_command%>
```

检查要点：
- 所有 lint 错误必须修复，warning 可以暂时忽略
- 如果 lint 规则不合理，提 issue 讨论，不要加 disable 注释绕过

## 第二步：执行测试

```bash
<%params.test_command%>
```

测试要求：
- 覆盖率不低于 <%params.coverage_threshold%>%
- 新增代码必须有对应的单元测试
- 修改的代码如果没有测试，补上再提 PR

## 第三步：结果判定

- lint 通过 + 测试通过 + 覆盖率达标 → 可以请求 review
- 任一失败 → 修复后重新运行，不要手动标记通过

## 常见问题

- snapshot 测试失败 → 确认 UI 变更是预期的，然后 `pnpm test --run -u` 更新
- 覆盖率刚好卡在阈值 → 不要降低阈值，补测试
- lint 和本地不一致 → 检查 Node 版本和 pnpm 版本是否匹配 CI 环境

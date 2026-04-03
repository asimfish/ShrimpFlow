---
name: code-quality-pipeline
steps:
  - id: lint
    pattern: lint-check
    with:
      language: typescript
      strict: true
  - id: test
    pattern: test-runner
    when: "lint passed"
    with:
      test_command: "pnpm test --run"
      coverage_min: 85
      focus_dirs: ["src", "lib"]
    inputs:
      lint_result: "<% steps.lint.outputs.lint_passed %>"
      issue_count: "<% steps.lint.outputs.issue_count %>"
    outputs_map:
      test_passed: tests_ok
      coverage_percent: coverage
  - id: report
    inline: "汇总质量报告：lint=<% steps.lint.outputs.lint_passed %>, issues=<% steps.lint.outputs.issue_count %>, tests=<% steps.test.outputs.tests_ok %>, coverage=<% steps.test.outputs.coverage %>%。全部通过则标记 ready-for-review。"
    when: "test step completed"
    outputs:
      summary:
        type: string
        description: 质量报告摘要
        extract:
          method: last_line
---

# 代码质量 Pipeline

先 lint 再测试，全部通过才能进入 review。

```
lint-check ──→ test-runner ──→ report
    │               │              │
    │ 语法+风格      │ 单测+覆盖率   │ 汇总结果
    │ strict 模式    │ 接收 lint 结果│ 标记 PR
```

## 数据流

1. `lint` 步骤输出 lint_passed / issue_count / issues_json
2. `test` 步骤通过 inputs 接收 lint 结果，通过 outputs_map 将 test_passed 重命名为 tests_ok
3. `report` 步骤汇总所有输出，生成最终报告

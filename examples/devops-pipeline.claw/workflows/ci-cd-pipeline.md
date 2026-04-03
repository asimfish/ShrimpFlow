---
name: ci-cd-pipeline
steps:
  - id: lint-test
    pattern: lint-and-test
    with:
      lint_command: "pnpm lint"
      test_command: "pnpm test --run --coverage"
      coverage_threshold: 80
    outputs:
      - name: lint_passed
        description: lint 是否通过
      - name: test_passed
        description: 测试是否通过
      - name: coverage_percent
        description: 测试覆盖率百分比
      - name: error_summary
        description: 失败时的错误摘要
  - id: deploy
    pattern: deploy-staging
    when: "lint and tests all passed"
    with:
      staging_url: "https://staging.example.com"
    inputs:
      lint_passed: "<% steps.lint-test.outputs.lint_passed %>"
      test_passed: "<% steps.lint-test.outputs.test_passed %>"
      coverage_percent: "<% steps.lint-test.outputs.coverage_percent %>"
    outputs:
      - name: deploy_success
        description: 部署是否成功
      - name: deployed_version
        description: 部署的版本号
      - name: smoke_test_passed
        description: 冒烟测试是否通过
  - id: notify
    inline: "汇总 CI/CD 结果：lint=<% steps.lint-test.outputs.lint_passed %>, test=<% steps.lint-test.outputs.test_passed %>, coverage=<% steps.lint-test.outputs.coverage_percent %>%, deploy=<% steps.deploy.outputs.deploy_success %>, version=<% steps.deploy.outputs.deployed_version %>。如果全部通过，在 PR 中添加 staging-verified 标签。"
    when: "deploy step completed"
---

# CI/CD Pipeline

PR 提交后的标准质量门禁 + staging 部署流程。

```
lint-and-test ──→ deploy-staging ──→ notify
    │                   │                │
    │ lint + test       │ 部署 + 冒烟     │ 汇总结果
    │ + 覆盖率检查       │ + 失败回滚      │ + 标记 PR
```

## 数据流

1. `lint-test` 步骤输出 lint_passed / test_passed / coverage_percent
2. `deploy` 步骤通过 inputs 接收上游结果，作为前置检查条件
3. `notify` 步骤汇总所有输出，生成最终报告

## 失败策略

- lint-test 失败 → 整个 pipeline 停止，不进入 deploy
- deploy 失败 → 自动回滚，通知开发者
- 任何步骤失败都不会静默跳过

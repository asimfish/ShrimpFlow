---
name: deploy-staging
confidence: high
severity: critical
category: [ci-cd, deployment]
scope: task
trigger:
  event: deploy_started
  when: "when deploying to staging environment after tests pass"
requires: ["lint-and-test"]
params:
  staging_url:
    type: string
    required: true
    description: staging 环境的 URL
  deploy_command:
    type: string
    default: "pnpm deploy:staging"
    description: 部署执行命令
  smoke_test_command:
    type: string
    default: "pnpm test:e2e --env=staging"
    description: 冒烟测试命令
  rollback_command:
    type: string
    default: "pnpm deploy:rollback"
    description: 回滚命令
outputs:
  deploy_success:
    type: boolean
    description: 部署是否成功
    extract:
      method: last_line
  deployed_version:
    type: string
    description: 部署的版本号
    extract:
      method: regex
      pattern: "Deployed version:\\s+(v[\\d.]+)"
  smoke_test_passed:
    type: boolean
    description: 冒烟测试是否通过
    extract:
      method: regex
      pattern: "Smoke tests:\\s+(PASSED|FAILED)"
prerequisites:
  - "staging 环境可访问"
  - "部署权限已配置（CI token 或 SSH key）"
source: manual
---

# 部署到 Staging 环境

只有 lint 和测试全部通过后才能部署 staging。这不是建议，是硬性要求。

## 前置检查

确认上游质量门禁结果：
- lint 通过：<% steps.lint-test.outputs.lint_passed %>
- 测试通过：<% steps.lint-test.outputs.test_passed %>
- 覆盖率：<% steps.lint-test.outputs.coverage_percent %>%

如果上述任一项为 false 或未达标，停止部署。

## 第一步：执行部署

```bash
<%params.deploy_command%>
```

部署过程中注意：
- 观察日志输出，确认没有 warning 或 error
- 部署超过 5 分钟未完成，检查网络和目标环境状态

## 第二步：冒烟测试

部署完成后立即执行冒烟测试：

```bash
<%params.smoke_test_command%>
```

冒烟测试覆盖：
- 首页可访问（HTTP 200）
- 核心 API 端点响应正常
- 登录流程可走通

## 第三步：失败处理

冒烟测试失败时立即回滚：

```bash
<%params.rollback_command%>
```

回滚后：
1. 收集部署日志和冒烟测试日志
2. 在 PR 中标注失败原因
3. 修复后从 lint-and-test 重新开始，不要只重新部署

## 成功确认

部署成功 + 冒烟测试通过 → 在 PR 中标注 staging 验证通过，可以请求 production 部署审批。

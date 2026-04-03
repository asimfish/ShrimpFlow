---
name: multi-env-config
confidence: high
severity: high
category: [devops, deployment]
scope: task
trigger:
  event: deploy_started
  globs: ["**/.env*", "**/config/*.yaml", "**/config/*.toml"]
  when: "when setting up or verifying multi-environment configurations"
params:
  environments:
    type: array
    default: ["development", "staging", "production"]
    description: 需要配置的环境列表
  required_vars:
    type: array
    default: ["DATABASE_URL", "API_KEY", "LOG_LEVEL"]
    description: 每个环境必须配置的环境变量列表
  check_command:
    type: string
    default: "env-check"
    description: 环境变量检查工具命令
  strict:
    type: boolean
    default: true
    description: 是否启用严格模式（缺失变量直接报错而非警告）
outputs:
  all_valid:
    type: boolean
    description: 所有环境配置是否全部合法
    extract:
      method: last_line
  missing_vars:
    type: string
    description: 缺失的变量汇总
    extract:
      method: regex
      pattern: "MISSING:\\s+(.+)"
source: manual
---

# 多环境配置检查

部署前逐个环境验证配置完整性。缺一个变量都不要放过，线上炸了比现在多花 5 分钟检查贵得多。

## 环境清单

<% for env in params.environments %>
### <%env%> 环境

检查 `.env.<%env%>` 文件是否存在且包含所有必需变量：

```bash
<%params.check_command%> --env=<%env%> --file=.env.<%env%>
```

必需变量检查：

<% for var in params.required_vars %>
- [ ] `<%var%>` — 已配置且非空
<% endfor %>

<% if params.strict %>
严格模式：任何缺失变量直接中断部署流程。
<% endif %>

<% endfor %>

## 跨环境一致性检查

确认以下规则：
- production 的 `LOG_LEVEL` 不应为 `debug`
- development 和 production 的 `DATABASE_URL` 不应指向同一个数据库
- `API_KEY` 在不同环境应使用不同的值（防止 staging 误调 production API）

## 失败处理

<% if params.strict %>
严格模式下，任何检查失败都会阻断后续部署步骤。修复配置后重新运行此检查。
<% endif %>

<% if not params.strict %>
宽松模式下，缺失变量仅产生警告。但 production 环境始终强制检查，不受此开关影响。
<% endif %>

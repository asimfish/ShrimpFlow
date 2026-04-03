---
name: lint-check
confidence: high
severity: high
category: [code-style, ci-cd]
scope: task
params:
  language:
    type: string
    required: true
    enum: [typescript, javascript, python, go]
    description: 目标语言
  strict:
    type: boolean
    default: false
    description: 是否启用严格模式
outputs:
  lint_passed:
    type: boolean
    description: lint 是否通过
    extract:
      method: last_line
  issue_count:
    type: number
    description: 发现的问题数量
    extract:
      method: regex
      pattern: "Found\\s+(\\d+)\\s+issues?"
  issues_json:
    type: object
    description: 问题详情（JSON 格式）
    extract:
      method: json_path
      path: "$.lint.issues"
source: manual
---

# <%params.language%> Lint 检查

执行 <%params.language%> 项目的 lint 检查。

<% if params.strict %>
## 严格模式

- 所有 warning 视为 error
- 不允许 any 类型
- 不允许 eslint-disable 注释
- 圈复杂度上限 10
<% else %>
## 标准模式

- error 必须修复
- warning 可以暂时保留但需要记录
<% endif %>

## 执行步骤

1. 运行 lint 命令
2. 收集所有问题
3. 输出问题数量和详情
4. 最后一行输出 true/false 表示是否通过

---
name: test-runner
confidence: high
severity: high
category: [testing, ci-cd]
scope: task
params:
  test_command:
    type: string
    default: "pnpm test --run"
    description: 测试执行命令
  coverage_min:
    type: number
    default: 80
    min: 0
    max: 100
    description: 最低覆盖率要求
  focus_dirs:
    type: array
    default: ["src"]
    description: 需要测试的目录列表
outputs:
  test_passed:
    type: boolean
    description: 测试是否全部通过
    extract:
      method: last_line
  coverage_percent:
    type: number
    description: 实际覆盖率
    extract:
      method: regex
      pattern: "Coverage:\\s+(\\d+\\.?\\d*)%"
  failed_tests:
    type: object
    description: 失败的测试用例详情
    extract:
      method: json_path
      path: "$.testResults.failed"
source: manual
---

# 测试执行

运行测试并检查覆盖率。

## 测试范围

<% for dir in params.focus_dirs %>
- <%dir%>/
<% endfor %>

## 执行

```bash
<%params.test_command%> --coverage
```

## 覆盖率要求

最低覆盖率：<%params.coverage_min%>%

- 覆盖率达标 -> 通过
- 覆盖率不达标 -> 列出未覆盖的文件，要求补测试

## 失败处理

- 测试失败时输出失败用例的文件路径和错误信息
- 最后一行输出 true/false

---
name: vue-style
confidence: very_high
severity: high
category: [code-style, frontend]
scope: file
trigger:
  globs: ["**/*.vue", "**/*.ts"]
requires: ["@team/coding-standards::naming-convention"]
conflicts: ["@security-expert/owasp-patterns::strict-csp"]
---

# Vue 代码风格

- 用 Composition API + script setup
- CSS 用 Tailwind CSS4
- 定义方法用 const 不要用 function
- 导入项超过 3 个时用命名空间导入
- 文字最小 14px

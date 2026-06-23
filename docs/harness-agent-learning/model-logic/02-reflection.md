# Reflection

## 这是什么

Reflection 是一种“生成后再检查”的 Agent 模式。它让 Agent 不把第一次输出当成最终答案，而是用一套评价标准重新审视结果，再决定接受、修正或重试。

最小形式是：

```text
生成结果 -> 批判检查 -> 发现缺口 -> 补充或重试 -> 接受结果
```

## 想解决什么问题

它主要解决第一次输出不可靠的问题。

Agent 的第一次结果经常有这些问题：

- 看起来完整，但缺少关键证据。
- 方向大体对，但漏掉约束。
- 语言很顺，但没有满足任务要求。

Reflection 的作用不是让 Agent 无限自我怀疑，而是增加一个质量闸门：结果必须通过检查，才能进入下一步。

## 原理是什么

Reflection 把一次生成拆成两个角色：

- **Producer**：先给出答案、报告、计划或代码。
- **Critic**：根据目标和验收标准检查缺口。

Critic 的输出必须能驱动行动，不能只是泛泛评价。比如“还不够好”没用，“缺少测试目录观察”才有用。

最小控制规则是：

```text
如果 critique 为空 -> 接受
如果 critique 指出缺口且未超过重试次数 -> 修正或重试
如果超过重试次数仍失败 -> 转人工或标记 needs_review
```

## 如何实践

练习场景：让 Agent 写一段仓库分析摘要。

先定义检查项：

1. 是否说明项目入口。
2. 是否说明测试或验证方式。
3. 是否说明当前结论来自哪些观察。

然后让 Agent 生成摘要，再用检查项 critique。若缺少测试信息，就补充读取测试目录，再修订摘要。

验收信号：

- critique 指向具体缺口。
- 重试次数有限。
- 修订结果比第一次更接近验收标准。

## 对应原型

原型中的 `run_reflection` 是最小实现：

- 文件：`prototypes/minimal_harness_agent/src/minimal_harness_agent/patterns.py`
- 测试：`test_reflection_retries_when_critique_finds_missing_requirement`

它保留了 Reflection 的核心控制逻辑：`produce()` 生成结果，`critique(output)` 检查结果，发现问题就在 `max_retries` 内重试。

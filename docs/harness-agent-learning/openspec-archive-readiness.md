# OpenSpec Archive Readiness

## 当前判断

`learn-harness-agent-systematically` 已经达到本轮学习变更的本地归档条件，但还不应自动归档。

原因：

- OpenSpec tasks 没有未完成复选框。
- MiniClaw 已成为主学习骨架。
- 离线验证脚本已经通过。
- 学习证据、架构图、checkpoint、最终文章都已落地。
- Deferred backlog 已明确不是当前闭环阻塞项。
- 之前约定：OpenSpec archive 等用户确认后再做。

因此当前状态是：**archive-ready, waiting for explicit user confirmation**。

## 已满足的归档证据

### 学习路线

- `openspec/changes/learn-harness-agent-systematically/proposal.md`
- `openspec/changes/learn-harness-agent-systematically/design.md`
- `openspec/changes/learn-harness-agent-systematically/tasks.md`
- `openspec/changes/learn-harness-agent-systematically/specs/harness-agent-learning/spec.md`

### 原型

- `prototypes/miniclaw_harness/`
- `prototypes/minimal_harness_agent/`

### 学习材料

- `开始这里.md`
- `docs/harness-agent-learning/checkpoint-当前学习闭环.md`
- `docs/harness-agent-learning/miniclaw-architecture.md`
- `docs/harness-agent-learning/miniclaw-walkthrough.md`
- `docs/harness-agent-learning/cards/`
- `docs/harness-agent-learning/model-logic/`
- `articles/harness-agent/从上下文工程到Harness-Agent：一个工程师视角的系统理解.md`

### 验证入口

```bash
scripts/verify_offline.sh
scripts/run_miniclaw_walkthrough.sh
scripts/check_external_readiness.sh
OPENAI_API_KEY=your_key scripts/verify_real_model.sh
```

当前离线验证已通过：

- MiniClaw：63 passed，3 skipped real-model tests。
- minimal harness：10 passed，1 skipped real-model test。

## Deferred backlog 处理建议

当前 deferred backlog：

- Full chapter 2 reading pass and card refinements.
- Full chapters 4/5 reading pass and card refinements.
- Minimal prototype SubAgent demo, if the smaller prototype remains useful after MiniClaw.
- OpenSpec archive command/process after user confirmation.

建议归档时不要把这些当作未完成任务处理。它们应被视为后续学习方向，而不是本轮变更缺口。

如果后续继续推进，可以开新的 OpenSpec change，例如：

- `deepen-harness-agent-sandboxing`
- `extend-miniclaw-with-search-workflow`
- `build-miniclaw-observability-ui`
- `refine-harness-agent-knowledge-cards`

## 归档前检查

归档前建议运行：

```bash
scripts/check_external_readiness.sh
scripts/verify_offline.sh
```

如果有真实模型 key，再运行：

```bash
OPENAI_API_KEY=your_key scripts/verify_real_model.sh
```

## 归档决策

可以归档，当且仅当用户明确确认：

> 本轮 `learn-harness-agent-systematically` 可以归档。

在确认前，不要移动或删除 `openspec/changes/learn-harness-agent-systematically/`。

## 归档后的期望状态

归档后，这一轮学习应作为 source of truth 保留：

- MiniClaw 证明 Harness Agent 的工程结构。
- knowledge cards 证明必要知识骨架。
- walkthrough/report 证明可观察证据。
- final article 证明可以系统化表达。
- checkpoint 证明本地完成状态。

归档不代表学习停止，只代表这一次“从书本到系统原型”的变更闭环完成。

# Harness Agent 当前路线复盘

## 当前判断

这条学习路线已经从“先读完、先写好文章”切换为“直接实现一个足够完整的 Harness Agent 产品壳”，这个选择是有效的。

MiniClaw 现在承担主线学习任务：它不是一个单点 Demo，而是把模型外部的工程系统串起来，让学习对象从概念变成可观察、可运行、可恢复的系统。

## 已经掌握的系统骨架

MiniClaw 覆盖了 Harness Agent 的三层结构。

第一层是 Agent 内核：

- Agent Loop：任务从计划、决策、工具调用、观察到最终结果。
- Tools：File、Bash、CodeAct 都通过受限工具边界执行。
- Context：执行 trace、task state、compact summary 分开保存。
- Skills：先看标签，再按需加载完整 Skill。
- Memory：完成后的分析结果可以进入长期记忆，并在后续任务中召回。

第二层是任务运行系统：

- Task System：后台任务有状态、结果、trace、approval、report。
- Resume：失败或中断后可以复用已有状态继续执行。
- Compact：trace 过长时可以压缩到结构化状态里。
- SubAgent：隔离一次具体任务的上下文，只把摘要返回主上下文。

第三层是产品壳：

- CLI Channel：本地命令作为入口。
- SQLite Store：消息、任务、trace、memory 持久化。
- Orchestrator：把输入转成可执行工作。
- Queue/Scheduler：支持排队和一次性计划任务。
- Output Router：把结果写回可检查的输出记录。

## 为什么这比继续打磨文章更有效

读书和写文章容易停在“我知道这些词”的层面。实现 MiniClaw 后，每个概念都有了工程位置：

- Context Engineering 不再只是“整理上下文”，而是 trace、state、memory、compact、Skill loading 的组合。
- Agent Loop 不再只是“模型多轮思考”，而是可审计的状态转移。
- Tool 不再只是“函数调用”，而是安全边界、输入约束、观察记录和失败恢复。
- Skills 不再只是提示词模板，而是渐进加载的专家上下文包。
- SubAgent 不再只是另开一个 Agent，而是隔离噪声上下文的执行容器。

这说明当前学习已经进入 Harness 工程本体，而不是停留在文章表达。

## 完成证据

主要代码：

- `prototypes/miniclaw_harness/`
- `prototypes/minimal_harness_agent/`

主要学习材料：

- `docs/harness-agent-learning/cards/`
- `docs/harness-agent-learning/model-logic/`
- `docs/harness-agent-learning/context-memory-skills-strategy.md`
- `articles/harness-agent/from-context-engineering-to-harness-agent.md`

关键验收方式：

```bash
python3 -m unittest discover -s prototypes/miniclaw_harness/tests -v
python3 -m unittest discover -s prototypes/minimal_harness_agent/tests -v
git diff --check
```

真实模型测试需要显式打开：

```bash
RUN_REAL_MODEL_TESTS=1 OPENAI_API_KEY=... python3 -m unittest discover -s prototypes/miniclaw_harness/tests -v
```

## 现在不需要继续纠结的事

短期内不需要继续逐篇 polish 第一章文章。文章已经降级为学习成果和素材库，不是当前主线。

短期内也不需要追求“读完整本书的所有知识点”。必要系统知识已经够支撑原型理解，后续读书应围绕原型缺口补。

## 下一步选择

如果继续学习，建议只选一个方向推进。

方向一：做一次真实模型演示。

目标是用真实模型跑通 planner 或 CodeAct，让 MiniClaw 从 deterministic harness 进入 model-backed harness。验收重点不是模型答得多漂亮，而是 Harness 能验证、约束、记录和 fallback。

方向二：强化执行隔离。

目标是把当前受限 Bash/CodeAct 升级为更明确的 sandbox/process 边界。这样可以深入理解 Harness Agent 为什么必须把工具能力和安全控制放在模型外部。

方向三：归档 OpenSpec。

目标是把 `learn-harness-agent-systematically` 从进行中变成已完成的学习变更。归档前需要确认：当前文章、知识卡、MiniClaw 原型是否已经作为这一轮学习的闭环。

## 当前结论

这轮学习的主线已经闭合：已经不是“知道 Harness Agent 有哪些概念”，而是实现了一个能解释这些概念如何协作的 MiniClaw 系统。

后续最值得做的不是继续补定义，而是选择一个真实压力点，把 MiniClaw 推向更接近真实使用的环境。

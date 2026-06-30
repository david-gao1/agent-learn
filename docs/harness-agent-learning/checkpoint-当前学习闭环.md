# Checkpoint：当前学习闭环

## 当前结论

这一轮 Harness Agent 学习已经形成闭环：

- 有系统知识骨架：知识卡、模式笔记、路线复盘。
- 有可运行原型：MiniClaw 和 minimal harness。
- 有证据生成方式：walkthrough 脚本和 task report。
- 有验证入口：boundary report、learn check、离线验证、真实模型验证、外部就绪检查。
- 有最终表达材料：系统文章和中文开始入口。

现在的主线不再是“继续补概念”或“继续扩功能”，而是收束当前学习闭环。真实模型验证、远端推送、OpenSpec 归档和长文章 polish 都可以作为后续动作，不再阻塞本地学习成果。

## 一条命令验收

```bash
scripts/verify_offline.sh
```

当前这条命令覆盖：

- MiniClaw 单元与集成测试。
- minimal harness 模式测试。
- walkthrough 证据包生成。
- whitespace 检查。

当前已验证通过：

- MiniClaw：66 tests passed locally，3 skipped real-model tests。
- minimal harness：10 passed，1 skipped real-model test。

快速学习验收：

```bash
make boundary-report
make learn-check
```

`boundary-report` 先汇总 FileTool、BashTool、CodeTool 的边界；`learn-check` 再验证这些边界进入真实任务证据链。

## 原型成果

MiniClaw 已经覆盖 Harness Agent 的核心工程机制：

- Channel、Store、Orchestrator、Queue、Scheduler、Output Router。
- Agent Loop：plan、decision、tool_call、observation、final_result。
- Tool：FileTool、BashTool、CodeTool。
- Tool Boundary：FileTool 记录 path escape/read limit，BashTool 记录 shell/cwd/allowlist，CodeTool 记录 imports/builtins/allowed calls。
- SubAgent：隔离任务上下文，主上下文只保留摘要。
- Task System：后台任务、状态持久化、resume、blocked recovery。
- Context Management：trace、state、compact summary。
- Skills：标签优先、按需加载 `SKILL.md`。
- Memory：完成任务后写入长期记忆，后续任务可召回。
- Human Approval：审批请求、批准事件、恢复执行。
- Model-backed path：runtime、planner、CodeAct 均有 gated smoke。

## 学习材料成果

优先阅读：

1. `开始这里.md`
2. `docs/harness-agent-learning/miniclaw-walkthrough.md`
3. `docs/harness-agent-learning/miniclaw-architecture.md`
4. `docs/harness-agent-learning/current-route-review.md`
5. `docs/harness-agent-learning/cards/README.md`
6. `docs/harness-agent-learning/openspec-archive-readiness.md`
7. `docs/harness-agent-learning/github-sync-recovery.md`
8. `articles/harness-agent/从上下文工程到Harness-Agent：一个工程师视角的系统理解.md`

这些材料的关系是：

- `开始这里.md` 负责上手。
- walkthrough 负责动手观察。
- architecture 负责建立代码阅读地图。
- route review 负责解释为什么走 MiniClaw 路线。
- cards 负责最小必要知识。
- archive readiness 负责说明 OpenSpec 归档条件和等待确认的原因。
- github sync recovery 负责说明如何恢复远端推送。
- final article 负责系统化表达。

## 脚本入口

```bash
scripts/check_external_readiness.sh
scripts/verify_offline.sh
scripts/run_miniclaw_walkthrough.sh
make boundary-report
make learn-check
OPENAI_API_KEY=your_key scripts/verify_real_model.sh
```

这些入口分别解决：

- 外部状态是否就绪。
- 本地离线验证是否通过。
- 学习证据是否能一键生成。
- 工具边界是否能先被看见。
- 最小 Harness 学习闭环是否能快速验收。
- 真实模型 smoke 是否能跑通。

## 外部状态

当前外部就绪状态：

- GitHub remote：`https://github.com/david-gao1/agent-learn.git`
- branch：`main`
- behind origin：`0`
- ahead origin：以 `scripts/check_external_readiness.sh` 输出为准
- working tree：`clean`
- `OPENAI_API_KEY`：missing
- credential helper：`osxkeychain`
- credential helper available：missing
- SSH GitHub auth：denied

因此当前还没完成的不是本地学习闭环，而是两个外部动作：

1. 配好 GitHub 凭据后执行：

   ```bash
   git push origin main
   ```

2. 配好真实模型 key 后执行：

   ```bash
   OPENAI_API_KEY=your_key scripts/verify_real_model.sh
   ```

## 还可以继续深化的方向

如果继续实现，建议只选一个方向。它们都是后续增强，不是当前闭环的阻塞项：

- 强化 sandbox/process 隔离，让 BashTool 和 CodeTool 更接近真实生产边界。
- 加一个更真实的 Web/Search 工具，把 MiniClaw 扩展到 DeepResearch 类任务。
- 做一个小型 Web UI，用来查看 task、trace、state、memory 和 report。
- 正式归档 OpenSpec，把本轮学习变更从 active 变为 archived。

## 当前收束建议

当前建议停止继续加功能，保留这个状态作为本轮学习成果：

1. 本地验收以 `make verify` 为准。
2. 日常复习以 `make boundary-report` 和 `make learn-check` 为入口。
3. OpenSpec 归档需要用户明确确认。
4. push 需要 GitHub 凭据恢复后再做。
5. 真实模型验证需要 `OPENAI_API_KEY` 后再跑。

## 判断是否完成本轮学习

如果你能解释下面这句话，本轮学习就已经达到目标：

> Harness Agent 不是一个更会聊天的模型，而是一个围绕模型构建的行动系统；模型负责判断和生成，Harness 负责上下文供给、工具边界、状态持久化、任务恢复、安全审批和证据输出。

这也是后续写文章、做分享或继续实现更复杂 Agent 系统的基础。

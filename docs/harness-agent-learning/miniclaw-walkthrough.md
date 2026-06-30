# MiniClaw 学习实验手册

这份手册的目标不是展示所有命令，而是让你按顺序观察一个 Harness Agent 如何工作。

跑完后，你应该能把这些机制放到同一张图里：入口、队列、SubAgent、Tool、Skill、Trace、State、Memory、Human Approval、Compact、Task Report。

## 快速生成证据

如果你想先看到完整结果，可以直接跑脚本：

```bash
scripts/run_miniclaw_walkthrough.sh
```

脚本会创建临时 workspace 和 SQLite 数据库，并把关键输出写入 `walkthrough-output/miniclaw-<timestamp>/`。

如果你想指定输出目录：

```bash
scripts/run_miniclaw_walkthrough.sh --output /tmp/miniclaw-walkthrough
```

输出目录里会包含：

- `普通消息.txt`
- `仓库分析-trace.txt`
- `仓库分析-state.txt`
- `memory.txt`
- `codeact-trace.txt`
- `codeact-state.txt`
- `approval-trace.txt`
- `compact-trace.txt`
- `task-report.md`
- `summary.md`

下面的手动步骤适合逐步理解每个机制。

## 准备实验环境

下面的命令会创建一个临时仓库和临时数据库，不污染当前项目。

```bash
TMPDIR=$(mktemp -d)
WORKSPACE="$TMPDIR/workspace"
DB="$TMPDIR/miniclaw.db"

mkdir -p "$WORKSPACE/tests"
cat > "$WORKSPACE/README.md" <<'EOF'
# Demo
EOF
cat > "$WORKSPACE/tests/test_smoke.py" <<'EOF'
import unittest

class SmokeTest(unittest.TestCase):
    def test_ok(self):
        self.assertTrue(True)
EOF

echo "$DB"
echo "$WORKSPACE"
```

记住输出的 `DB` 和 `WORKSPACE`。后面所有命令都基于它们。

## 1. 先跑普通消息

普通消息展示的是产品壳：CLI Channel -> SQLite Store -> Orchestrator -> Agent Runtime -> Output Router。

```bash
python3 prototypes/miniclaw_harness/main.py --db "$DB" send "hello miniclaw"
python3 prototypes/miniclaw_harness/main.py --db "$DB" run-once
python3 prototypes/miniclaw_harness/main.py --db "$DB" outbox
```

观察点：

- `send` 只负责把输入放进 store。
- `run-once` 才触发 orchestrator 处理一条消息。
- `outbox` 证明输出也被持久化，而不是只打印到终端。

## 2. 跑一次 SubAgent 仓库分析

这一步是主实验。它把 Harness Agent 的几个核心部件串起来：SubAgent、Skill、FileTool、BashTool、Trace、Task State、Memory。

```bash
python3 prototypes/miniclaw_harness/main.py \
  --db "$DB" \
  --runtime subagent \
  --workspace "$WORKSPACE" \
  --skills-root prototypes/minimal_harness_agent/skills \
  send "subagent-background: analyze repo with repo-reading skill"

python3 prototypes/miniclaw_harness/main.py \
  --db "$DB" \
  --runtime subagent \
  --workspace "$WORKSPACE" \
  --skills-root prototypes/minimal_harness_agent/skills \
  run-once

python3 prototypes/miniclaw_harness/main.py --db "$DB" background-list
```

从 `background-list` 里取出任务 id：

```bash
TASK_ID=<上一步看到的 task id，不要带 #>
```

观察点：

- 主 Agent 没有直接吞下仓库细节，而是把任务派给 SubAgent。
- SubAgent 的执行细节进入后台任务和 trace。
- 主上下文只需要知道任务已派发或已完成。

## 3. 看 Trace：Agent Loop 是否真的发生

```bash
python3 prototypes/miniclaw_harness/main.py --db "$DB" trace-show "$TASK_ID"
```

你应该能看到类似顺序：

```text
plan
decision
tool_call: FileTool.list_files
skill_load
observation
tool_call: FileTool.read_file
observation
tool_call: BashTool.run
observation
final_result
```

观察点：

- `plan` 说明任务先被转成执行意图。
- `decision` 说明 Harness 选择了允许的动作，而不是让模型任意行动。
- `tool_call` 和 `observation` 说明 Agent 通过环境反馈继续推进。
- `final_result` 是可审计链路的末端，不是凭空生成的答案。

这就是最小 Agent Loop：计划 -> 决策 -> 行动 -> 观察 -> 总结。

## 4. 看 State：上下文如何变成可恢复状态

```bash
python3 prototypes/miniclaw_harness/main.py --db "$DB" state-show "$TASK_ID"
```

重点看这些字段：

- `kind: repo_analysis`
- `files`
- `preview_file`
- `test_status`
- `summary`
- `skill`
- `plan_source`

观察点：

- Trace 适合审计过程，State 适合恢复任务。
- 文件列表、预览、测试结果进入结构化状态后，任务可以中断再继续。
- 这就是上下文工程的一个关键动作：把易丢失的上下文沉淀成状态。

## 5. 看 Memory：完成结果是否能被后续复用

```bash
python3 prototypes/miniclaw_harness/main.py --db "$DB" memory-list repo
```

观察点：

- Memory 不是聊天历史。
- Memory 保存的是后续任务可能复用的结构化经验或结果摘要。
- MiniClaw 这里保存的是一次仓库分析结果，后续分析可以 recall。

## 6. 跑一次 CodeAct

CodeAct 的核心不是“模型会写代码”，而是 Harness 把代码执行变成一个受限工具。

```bash
python3 prototypes/miniclaw_harness/main.py \
  --db "$DB" \
  --runtime subagent \
  --workspace "$WORKSPACE" \
  send "subagent-background: codeact count files"

python3 prototypes/miniclaw_harness/main.py \
  --db "$DB" \
  --runtime subagent \
  --workspace "$WORKSPACE" \
  run-once

python3 prototypes/miniclaw_harness/main.py --db "$DB" background-list
```

把新的任务 id 记为：

```bash
CODE_TASK_ID=<新的 task id>
```

检查它的执行证据：

```bash
python3 prototypes/miniclaw_harness/main.py --db "$DB" trace-show "$CODE_TASK_ID"
python3 prototypes/miniclaw_harness/main.py --db "$DB" state-show "$CODE_TASK_ID"
```

观察点：

- `codeact: CodeTool.run` 说明这次行动媒介是代码。
- `CodeTool` 会做 AST 安全检查。
- 代码执行结果进入 trace 和 state，而不是只作为一次不可追踪的脚本运行。

## 7. 跑一次 Human Approval

这一步观察人类审批如何进入 Harness，而不是靠口头约定。

```bash
python3 prototypes/miniclaw_harness/main.py \
  --db "$DB" \
  --runtime subagent \
  --workspace "$WORKSPACE" \
  send "subagent-background: run tests with approval"

python3 prototypes/miniclaw_harness/main.py \
  --db "$DB" \
  --runtime subagent \
  --workspace "$WORKSPACE" \
  run-once

python3 prototypes/miniclaw_harness/main.py --db "$DB" background-list
```

把等待审批的任务 id 记为：

```bash
APPROVAL_TASK_ID=<等待审批的 task id>
```

批准并恢复：

```bash
python3 prototypes/miniclaw_harness/main.py \
  --db "$DB" \
  --runtime subagent \
  --workspace "$WORKSPACE" \
  approve-task "$APPROVAL_TASK_ID"

python3 prototypes/miniclaw_harness/main.py --db "$DB" trace-show "$APPROVAL_TASK_ID"
```

观察点：

- 审批请求会持久化。
- 批准动作会进入 trace。
- 这说明 Human-in-the-loop 是系统状态，不是“人在旁边看着”。

## 8. 手动 Compact 长 Trace

Compact 不是简单删除历史，而是把长过程压缩成可继续使用的摘要。

```bash
python3 prototypes/miniclaw_harness/main.py --db "$DB" compact-task "$TASK_ID" --keep-recent 5
python3 prototypes/miniclaw_harness/main.py --db "$DB" trace-show "$TASK_ID"
python3 prototypes/miniclaw_harness/main.py --db "$DB" state-show "$TASK_ID"
```

观察点：

- trace 里会保留最近事件。
- state 里会出现 `compact_summary`。
- 这对应长任务里的上下文管理：旧过程被压缩，新近状态保留细节。

## 9. 导出 Task Report

Task Report 是把一次任务的证据打包成文章或复盘材料。

```bash
python3 prototypes/miniclaw_harness/main.py --db "$DB" task-report "$TASK_ID"
```

如果只想快速复盘学习要点：

```bash
python3 prototypes/miniclaw_harness/main.py --db "$DB" task-report "$TASK_ID" --summary
```

观察点：

- report 包含 task metadata、tool decision、trace、state、approval。
- summary 只保留机制、行动边界、状态证据和复盘重点。
- 它把“Agent 做了什么”从黑盒回答变成可检查证据。
- 最终文章应该引用这类证据，而不是只复述概念。

## 复盘问题

跑完实验后，用下面的问题检查理解是否到位：

1. 哪些信息留在 trace，哪些信息进入 state？
2. Skill 是什么时候加载的？为什么不是一开始全部塞进上下文？
3. SubAgent 隔离了什么？主上下文损失了什么，又换来了什么？
4. CodeAct 的风险在哪里？MiniClaw 把风险放在哪个边界控制？
5. Human Approval 在系统中是状态、事件，还是一句提示词？
6. Compact 之后，系统还保留了哪些恢复任务所需的信息？

能回答这些问题，就说明你已经在理解 Harness Agent 的工程结构，而不是只记住术语。

# MiniClaw Harness Prototype

MiniClaw is a local-first Claw-style Harness product inspired by the book's Claude Code and NanoClaw chapters.

It turns a basic Agent runtime into a product shell:

```text
Local CLI Channel
  -> SQLite Store
  -> Orchestrator
  -> Group Queue
  -> Agent Runtime
  -> Output Router
```

## What v0.1 Demonstrates

- Local channel input.
- SQLite persistence for inbound messages, outbound messages, and scheduled tasks.
- One-shot scheduler that turns due tasks into normal inbound messages.
- Per-group queue state.
- Deterministic local agent runtime.
- Output routing back to the store.

## What v0.2 Adds

- `ModelBackedRuntime`, an adapter that lets the orchestrator call any model object with a `complete(instructions, prompt)` method.
- Runtime injection through `MiniClawApp.open(..., runtime=...)`.
- Test coverage proving the orchestrator can use a model-backed runtime without requiring network access.

## What v0.3 Adds

- A gated real-model smoke test that wires `ModelBackedRuntime` to the existing OpenAI Responses API adapter.
- The default test suite remains offline; real-model verification only runs when explicitly enabled.

## What v0.4 Adds

- File-system IPC namespaces with `input/`, `messages/`, and `tasks/` directories per group.
- IPC input files can become normal inbound messages.
- IPC task files can become scheduled tasks.
- Outbound messages can be flushed back to `messages/` files.

## What v0.5 Adds

- `SubAgentRuntime`, a minimal runtime that demonstrates context isolation.
- Messages containing `subagent:` are delegated to a child context.
- The main context receives only the child summary, not the child detail log.

## What v0.6 Adds

- `BackgroundTaskManager`, a minimal in-process background task runner.
- Slow operations can run in a background thread without blocking the main flow.
- Completion notifications can be converted into normal inbound messages and processed by the orchestrator.
- Execution is still in-process; persistent background workers come later.

## What v0.7 Adds

- Background task state is persisted in SQLite.
- Completed background task results can be read after reopening `MiniClawApp`.
- The SQLite store can be updated safely from the background worker thread.
- CLI commands can start, list, and inspect background tasks.

## What v0.8 Adds

- `SubAgentRuntime` can dispatch isolated work into the background task system.
- The main context receives only a dispatch summary.
- Child-only details stay in the SubAgent context while the background result is persisted.

## What v0.9 Adds

- SubAgent background work can observe a bounded local workspace.
- The persisted background result includes a small relative file list.
- Hidden directories and common cache folders are skipped during observation.

## What v0.10 Adds

- `FileTool` becomes the first formal tool boundary.
- `SubAgentRuntime` observes workspace files through the tool interface instead of scanning files directly.
- Tests can inject a fake file tool to verify runtime-tool separation.

## What v0.11 Adds

- `FileTool.read_file()` reads bounded text from files inside the workspace.
- Path traversal outside the workspace is blocked.
- SubAgent background results include a short preview of the first observed file.

## What v0.12 Adds

- `BashTool` provides a minimal allowlisted command tool.
- Commands run in the configured workspace without `shell=True`.
- SubAgent background results include a small `pwd` observation when Bash is available.

## What v0.13 Adds

- SubAgent background work includes minimal rule-based tool routing.
- File listing tasks use `FileTool.list_files()`.
- File reading tasks use `FileTool.read_file()`.
- Test-running tasks use `BashTool.run("python3 -m unittest discover -s tests -v")`.

## What v0.14 Adds

- Tool routing now produces a structured `ToolDecision`.
- Each decision records `action`, `target`, and `reason`.
- SubAgent runtime keeps an in-memory decision log for inspection and tests.

## What v0.15 Adds

- Tool decisions are persisted in SQLite by background task id.
- Reopening `MiniClawApp` can recover the decision for a completed background task.
- The persisted record forms a minimal audit trail for tool routing.

## What v0.16 Adds

- Execution trace events are persisted in SQLite by background task id.
- `trace-show <task-id>` displays the tool decision and resulting observation.
- The trace starts to connect Harness reasoning with tool output instead of only storing final task results.

## What v0.17 Adds

- SubAgent background traces now record a minimal Agent Loop sequence:
  `plan -> decision -> tool_call -> observation -> final_result`.
- `trace-show <task-id>` can be used to inspect how a task moved from intent to tool execution to final result.
- This makes MiniClaw useful for learning Harness behavior, not just checking that a background task completed.

## Run Tests

```bash
python3 -m unittest discover -s prototypes/miniclaw_harness/tests -v
```

Run MiniClaw with a real model:

```bash
RUN_REAL_MODEL_TESTS=1 OPENAI_API_KEY=your_key python3 -m unittest discover -s prototypes/miniclaw_harness/tests -v
```

Optional:

```bash
OPENAI_MODEL=gpt-5.4-mini
```

## Run Locally

```bash
python3 prototypes/miniclaw_harness/main.py send "分析这个仓库"
python3 prototypes/miniclaw_harness/main.py run-once
python3 prototypes/miniclaw_harness/main.py outbox
```

Schedule a one-shot task:

```bash
python3 prototypes/miniclaw_harness/main.py schedule "提醒我检查后台任务" --delay 0
python3 prototypes/miniclaw_harness/main.py tick
python3 prototypes/miniclaw_harness/main.py run-once
python3 prototypes/miniclaw_harness/main.py outbox
```

Use file-system IPC:

```bash
python3 prototypes/miniclaw_harness/main.py ipc-send "通过 IPC 分析 Harness"
python3 prototypes/miniclaw_harness/main.py ipc-drain
python3 prototypes/miniclaw_harness/main.py run-once
python3 prototypes/miniclaw_harness/main.py ipc-flush
```

Run a background task from the CLI:

```bash
python3 prototypes/miniclaw_harness/main.py background-run "collect metrics" --group ops
python3 prototypes/miniclaw_harness/main.py background-list
python3 prototypes/miniclaw_harness/main.py background-show <task-id>
python3 prototypes/miniclaw_harness/main.py trace-show <task-id>
```

Dispatch isolated SubAgent work through the orchestrator:

```bash
python3 prototypes/miniclaw_harness/main.py --runtime subagent --workspace . send "subagent-background: 汇总代码仓库结构"
python3 prototypes/miniclaw_harness/main.py --runtime subagent --workspace . run-once
python3 prototypes/miniclaw_harness/main.py background-list
```

## Next Steps

- Connect SubAgent background work to file tools or IPC.
- Add stronger sandbox or container boundary.

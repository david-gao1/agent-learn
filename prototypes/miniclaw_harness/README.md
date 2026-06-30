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

## What v0.18 Adds

- `analyze repo` tasks run a minimal multi-step chain:
  `list_files -> read_file -> run_tests -> summarize`.
- Each tool call and observation is persisted in the execution trace.
- Background tasks can now demonstrate a real Harness loop instead of a single routed tool action.

## What v0.19 Adds

- Repository analysis results are persisted as structured task state.
- `state-show <task-id>` displays state such as files, preview file, test status, test output, and summary.
- Task state gives MiniClaw a recovery-friendly record beyond human-readable traces.

## What v0.20 Adds

- Repository analysis can reuse existing task state.
- If `files`, `preview_file`, and `preview` already exist, MiniClaw skips file listing and file reading.
- Resume traces record when existing task state was reused before continuing with tests and summary.

## What v0.21 Adds

- `resume-task <task-id>` provides a CLI entry point for continuing a persisted SubAgent task.
- Resumed repository analysis reuses existing task state and continues remaining tool steps.
- This turns state reuse from an internal mechanism into a product-visible recovery flow.

## What v0.22 Adds

- Repository analysis marks failed test runs as blocked task state instead of pretending the task completed.
- Blocked state keeps files, preview, test output, and a blocked reason for later recovery.
- Resuming after the failure reuses preserved context, reruns tests, clears the blocked reason, and marks the state completed.

## What v0.23 Adds

- `compact-task <task-id>` compresses long execution traces into `compact_summary` in structured task state.
- Compaction keeps a compact event plus the most recent trace events.
- This gives MiniClaw a minimal context-management loop: trace, state, resume, and compact.

## What v0.24 Adds

- Trace writes can trigger automatic compaction when a task exceeds a threshold.
- SubAgent runtime traces use a default threshold of 20 events and keep the 8 most recent events.
- Automatic compaction waits until structured task state exists, so early trace-only tasks are not compressed before they have a durable summary target.

## What v0.25 Adds

- Repository analysis can use an optional model-backed planner.
- The planner returns a structured JSON `steps` array, while MiniClaw validates allowed steps and executes them through the Harness.
- Model planning is recorded as a `model_plan` trace event and stored as `plan_source: model` in task state.

## What v0.26 Adds

- A gated real-model planner smoke test verifies Model -> Plan -> Harness execution.
- Planner parsing can extract JSON from model responses that include extra prose.
- The default suite still stays offline unless `RUN_REAL_MODEL_TESTS=1` and `OPENAI_API_KEY` are set.

## What v0.27 Adds

- Planner failures now fall back to the deterministic repository analysis plan.
- Invalid JSON and plans with no allowed steps are recorded as `planner_error` trace events.
- Structured task state stores `plan_source: rule_fallback` and the `planner_error`, so learners can see why Harness did not trust the model plan.

## What v0.28 Adds

- MiniClaw now has a local `LocalSkillLoader` for progressive Skill loading.
- The loader exposes Skill labels first and loads full `SKILL.md` only after a task matches the Skill.
- SubAgent repository analysis records `skill_load` in the trace and stores `skill` plus `skill_summary` in structured task state.
- The CLI accepts `--skills-root` for running SubAgent tasks with local Skills.

## What v0.29 Adds

- MiniClaw now has a structured long-term memory table in SQLite.
- Completed repository analysis tasks write a reusable `repo_analysis` memory entry.
- Later repository analysis tasks recall matching memories and record `memory_recall` in the trace.
- Structured task state stores `memory_count` and `memory_summary` when memories are recalled.
- The CLI adds `memory-list <query>` for inspecting persisted memories.

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

Run SubAgent repository analysis with local Skills:

```bash
python3 prototypes/miniclaw_harness/main.py \
  --runtime subagent \
  --workspace . \
  --skills-root prototypes/minimal_harness_agent/skills \
  send "subagent-background: analyze repo with repo-reading skill"
python3 prototypes/miniclaw_harness/main.py \
  --runtime subagent \
  --workspace . \
  --skills-root prototypes/minimal_harness_agent/skills \
  run-once
```

Inspect persisted memories:

```bash
python3 prototypes/miniclaw_harness/main.py memory-list repo
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
python3 prototypes/miniclaw_harness/main.py state-show <task-id>
python3 prototypes/miniclaw_harness/main.py --runtime subagent --workspace . resume-task <task-id>
python3 prototypes/miniclaw_harness/main.py compact-task <task-id> --keep-recent 5
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

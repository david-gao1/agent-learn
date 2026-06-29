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

## Run Tests

```bash
python3 -m unittest discover -s prototypes/miniclaw_harness/tests -v
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

## Next Steps

- Wire `ModelBackedRuntime` to the existing OpenAI Responses API adapter from `minimal_harness_agent`.
- Add file-system IPC.
- Add SubAgent isolation.
- Add background task execution.
- Add stronger sandbox or container boundary.

# AGENTS.md

## Current Mission

This repository is a Harness Agent learning project. The current backbone is MiniClaw, a local-first Claw-style Harness prototype under `prototypes/miniclaw_harness/`.

Do not treat article polishing as the main path. The main path is:

1. Keep MiniClaw runnable.
2. Keep the learning evidence scripts working.
3. Keep OpenSpec as the source of truth.
4. Preserve the final article and learning notes as synthesis material.

## Start Here

For human-facing orientation, read:

- `开始这里.md`
- `docs/harness-agent-learning/checkpoint-当前学习闭环.md`
- `docs/harness-agent-learning/miniclaw-architecture.md`
- `docs/harness-agent-learning/miniclaw-walkthrough.md`
- `docs/harness-agent-learning/openspec-archive-readiness.md`

For OpenSpec state, read:

- `openspec/changes/learn-harness-agent-systematically/tasks.md`
- `openspec/changes/learn-harness-agent-systematically/design.md`
- `openspec/changes/learn-harness-agent-systematically/specs/harness-agent-learning/spec.md`

## Verification

Default verification:

```bash
scripts/verify_offline.sh
```

This runs:

- MiniClaw tests.
- minimal harness tests.
- walkthrough evidence generation.
- `git diff --check`.

Real model verification is gated and must not be run unless `OPENAI_API_KEY` is available:

```bash
OPENAI_API_KEY=your_key scripts/verify_real_model.sh
```

External readiness check:

```bash
scripts/check_external_readiness.sh
```

## Important Scripts

- `scripts/verify_offline.sh`: full local offline verification.
- `scripts/run_miniclaw_walkthrough.sh`: generates walkthrough evidence files.
- `scripts/verify_real_model.sh`: runs gated real-model smoke tests.
- `scripts/check_external_readiness.sh`: reports git/remote/key readiness.

## Git State

The local branch has been ahead of `origin/main` because GitHub credentials are not configured in this environment. Do not assume push has succeeded. Check with:

```bash
scripts/check_external_readiness.sh
```

Avoid destructive git commands. Do not reset, clean, or discard user changes unless explicitly instructed.

## Deferred Backlog Is Not A Blocker

The OpenSpec deferred backlog includes:

- Full chapter 2 reading pass and card refinements.
- Full chapters 4/5 reading pass and card refinements.
- Minimal prototype SubAgent demo, if still useful after MiniClaw.
- OpenSpec archive after user confirmation.

These are not blockers for the current MiniClaw learning closure.

## OpenSpec Archive

The current change is archive-ready but waiting for explicit user confirmation. Read `docs/harness-agent-learning/openspec-archive-readiness.md` before archiving. Do not move or delete `openspec/changes/learn-harness-agent-systematically/` unless the user explicitly confirms archive.

## Editing Guidance

- Prefer small, verified commits.
- Keep generated walkthrough output out of git; `walkthrough-output/` is ignored.
- Do not enable real-model tests in default CI.
- Keep tests offline by default.
- If adding behavior, add or update tests first.
- If changing docs that mention commands, run the referenced command or explain why it could not be run.

## Current Completion Signal

The current local learning loop is healthy when:

```bash
scripts/verify_offline.sh
```

passes, and `scripts/check_external_readiness.sh` reports `working_tree: clean`.

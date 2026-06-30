# Agent Learn

This repository tracks a structured learning path for Harness Agent engineering.

Start here if you are learning the system:

- `开始这里.md`

## Current Focus

- OpenSpec-managed learning change: `learn-harness-agent-systematically`
- Learning notes for Harness Agent concepts
- MiniClaw, a local-first Harness Agent product prototype
- A minimal offline Harness Agent prototype for smaller pattern demos
- Article draft: `articles/harness-agent/从上下文工程到Harness-Agent：一个工程师视角的系统理解.md`

## Useful Paths

- `openspec/changes/learn-harness-agent-systematically/`: proposal, design, tasks, and spec
- `docs/harness-agent-learning/`: concept map and strategy notes
- `articles/harness-agent/`: long-form synthesis article
- `prototypes/miniclaw_harness/`: primary local-first Harness Agent product prototype
- `prototypes/minimal_harness_agent/`: runnable prototype and sample Skill

## Verify Prototype

```bash
make verify
```

Equivalent script:

```bash
scripts/verify_offline.sh
```

The verification script runs the MiniClaw tests, minimal harness tests, walkthrough evidence generation, and whitespace check.

Individual test commands:

```bash
python3 -m unittest discover -s prototypes/miniclaw_harness/tests -v
python3 -m unittest discover -s prototypes/minimal_harness_agent/tests -v
```

GitHub Actions runs the same offline test suite on push and pull request.

Optional real-model smoke test:

```bash
OPENAI_API_KEY=your_key scripts/verify_real_model.sh
```

## Run Learning Walkthrough

Follow the MiniClaw walkthrough to observe Agent Loop, Tools, Skills, Memory, Task State, Compact, SubAgent, CodeAct, and approval as one system:

- `docs/harness-agent-learning/miniclaw-walkthrough.md`

Generate walkthrough evidence in one command:

```bash
scripts/run_miniclaw_walkthrough.sh
```

## Run Minimal Demo

```bash
python3 prototypes/minimal_harness_agent/demo.py
```

## Source Material

The local workspace may contain PDF source books used for study, but PDFs are ignored by git because one scanned file exceeds GitHub's normal file-size limit.

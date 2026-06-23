# Agent Learn

This repository tracks a structured learning path for Harness Agent engineering.

## Current Focus

- OpenSpec-managed learning change: `learn-harness-agent-systematically`
- Learning notes for Harness Agent concepts
- A minimal offline Harness Agent prototype
- Article draft: `articles/harness-agent/from-context-engineering-to-harness-agent.md`

## Useful Paths

- `openspec/changes/learn-harness-agent-systematically/`: proposal, design, tasks, and spec
- `docs/harness-agent-learning/`: concept map and strategy notes
- `articles/harness-agent/`: long-form synthesis article
- `prototypes/minimal_harness_agent/`: runnable prototype and sample Skill

## Verify Prototype

```bash
python3 -m unittest discover -s prototypes/minimal_harness_agent/tests -v
```

Optional real-model smoke test:

```bash
RUN_REAL_MODEL_TESTS=1 OPENAI_API_KEY=your_key python3 -m unittest discover -s prototypes/minimal_harness_agent/tests -v
```

## Run Demo

```bash
python3 prototypes/minimal_harness_agent/demo.py
```

## Source Material

The local workspace may contain PDF source books used for study, but PDFs are ignored by git because one scanned file exceeds GitHub's normal file-size limit.

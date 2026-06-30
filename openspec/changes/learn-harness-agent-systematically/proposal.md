# Learn Harness Agent Systematically

## Why

Harness Agent is becoming the practical layer that turns a language model from a responder into a worker. The learning goal is to move beyond prompt usage and build a systematic engineering view of context, tools, loops, skills, memory, subagents, and task systems.

This change captures the learning path as an OpenSpec-managed source of truth so progress can be tracked by capability, artifact, and scenario instead of by calendar time.

## What Changes

- Shift the learning strategy from concept-by-concept study to building the most complete implementable Harness system from the book.
- Use a MiniClaw project to combine Claude Code-style Harness internals with NanoClaw-style product shell capabilities.
- Keep existing notes and cards as references, but make implementation the primary learning path.
- Specify capabilities through runnable scenarios rather than article progress.
- Preserve the minimal offline Harness Agent prototype as a smaller reference implementation.

## Outcomes

- A necessary knowledge card set: `docs/harness-agent-learning/cards/`.
- A MiniClaw project: `prototypes/miniclaw_harness/`.
- A system article: `articles/harness-agent/从上下文工程到Harness-Agent：一个工程师视角的系统理解.md`.
- A minimal prototype: `prototypes/minimal_harness_agent/`.
- A reusable sample Skill: `prototypes/minimal_harness_agent/skills/repo-reading/`.
- A learning spec: `openspec/changes/learn-harness-agent-systematically/specs/harness-agent-learning/spec.md`.

## Out Of Scope

- Building a production LLM agent service.
- Integrating live model APIs.
- Implementing full DeepResearch, Mem0, OpenClaw, or Claude Code equivalents.
- Replacing the book with external courses or weekly schedules.

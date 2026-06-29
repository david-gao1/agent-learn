# Design: Harness Agent Learning System

## Learning Architecture

The learning path now centers on implementing MiniClaw, a small but complete Harness product inspired by the book's Claude Code and NanoClaw chapters. Notes and cards remain useful, but implementation is the fastest route to understanding.

1. **System target**: build MiniClaw as the most complete implementable system in the book.
2. **Harness core**: reuse and extend Agent Loop, tools, Skills, Compact, Task System, SubAgent, and real-model hooks.
3. **Product shell**: add channel input, message persistence, queueing, scheduling, orchestration, and output routing.
4. **Runtime boundary**: keep v0.1 local and offline-capable, then add real-model and process/container isolation as optional layers.
5. **Synthesis**: write articles only after the running system has exposed the engineering tradeoffs.

## Knowledge Model

The learner should first build short cards under `docs/harness-agent-learning/cards/`. Each card answers five questions: what problem it solves, the core mechanism, a minimal example, how it differs from nearby concepts, and where it appears in the prototype.

The necessary first-pass card set is:

- **Context Engineering** selects, shapes, compresses, and injects information into model calls.
- **Agent Loop** keeps the model-tool-environment cycle running across multiple steps.
- **Tool** lets the model observe and act outside the chat transcript.
- **ReAct** interleaves reasoning, action, and observation.
- **Plan-Act** separates task decomposition from execution.
- **Reflection** critiques an attempt and decides whether to retry.
- **CodeAct** uses code execution as an action medium.
- **Memory** stores durable facts or state beyond the immediate context window.
- **Skills** package reusable expert context and load it progressively.
- **Task System** persists work so the agent can resume, audit, and report progress.
- **SubAgent** isolates noisy execution context from the main agent.
- **Compact** compresses older context so the loop can continue.

## Prototype Design

The prototype is intentionally offline and deterministic. It demonstrates Harness mechanics without depending on a live LLM.

- `HarnessAgent` creates a task, selects a local Skill, observes workspace files through a shell tool, compacts context, and marks the task done.
- `LocalSkillLoader` implements the L1/L2 idea: list labels first, load full `SKILL.md` only when selected.
- `TaskStore` persists tasks to JSON.
- `compact_messages` summarizes older context and keeps recent working memory.
- `run_bash` exposes a constrained command tool with a small safety denylist.

Prototype evolution should happen only after the related model-logic note exists:

1. Add a Plan-Act demo that creates a short plan and executes each step.
2. Add a Reflection demo that critiques an insufficient result and retries once.
3. Add a CodeAct demo that runs constrained code for a small analysis task.
4. Add a SubAgent demo that isolates a repository-reading or note-summarizing task from the main loop context.

Each core pattern needs a pre-practice explanation under `docs/harness-agent-learning/model-logic/` before implementation. The explanation answers:

1. **What it is**: the pattern's plain-language definition.
2. **Why it exists**: the failure mode or uncertainty it reduces.
3. **Principle**: the minimal loop, state transition, or control rule.
4. **How to practice**: a small scenario and acceptance signal.
5. **Prototype mapping**: which function, test, or demo expresses the idea.

## MiniClaw Design

MiniClaw is the new primary project under `prototypes/miniclaw_harness/`. It is a local-first version of a Claw-style Harness product.

The v0.1 system shall include:

- **CLI Channel**: accepts user messages and scheduled jobs without depending on external IM platforms.
- **SQLite Store**: persists inbound messages, outbound messages, groups, sessions, and tasks.
- **Orchestrator**: polls pending messages, applies trigger rules, and hands work to the queue.
- **Group Queue**: serializes work per group and tracks running/idle state.
- **Agent Runtime**: produces a response through a local deterministic agent first, with a real-model adapter kept optional.
- **Scheduler**: supports one-shot jobs for v0.1 and leaves cron/interval for later.
- **Output Router**: writes agent replies back to the store for inspection.

Later versions should add file-system IPC, SubAgent isolation, background tasks, and a stronger execution sandbox.

## Final Article Design

The article should teach the system from an engineer's point of view:

1. Why prompt engineering is insufficient for real work.
2. How context engineering changes the unit of design.
3. The five foundational Agent patterns.
4. How Loop, Tools, Skills, Memory, SubAgent, and Task System compose a Harness Agent.
5. What the prototype demonstrates and what it deliberately omits.
6. How DeepResearch, OpenClaw/NanoClaw, and Agent Teams extend the same ideas.

Article drafts should follow `skills/article-depth-writing/SKILL.md`. Knowledge articles explain concepts from problem to mechanism. Exploratory articles pursue one judgment question with a running example, a judgment framework, and explicit boundaries and costs.

Existing chapter articles are treated as a material library. They should not block the learning path while the knowledge cards and prototype practice are incomplete.

## Validation

Learning is accepted through scenario tests:

- Explain a concept such as Skills, Compact, or SubAgent in terms of problem, mechanism, and risk.
- Explain a core pattern such as Plan-Act, Reflection, or CodeAct before running its demo.
- Design a Harness architecture for a repository-analysis Agent.
- Run MiniClaw end to end: enqueue a message, persist it, process it through the orchestrator, and route an output.
- Schedule a one-shot MiniClaw task and observe it become a normal message for the agent.
- Run the prototype and show a multi-step task with persisted task state.
- Publish a coherent article only after the card set and prototype walkthrough can support it.

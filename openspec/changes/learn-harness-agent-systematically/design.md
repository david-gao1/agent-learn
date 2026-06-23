# Design: Harness Agent Learning System

## Learning Architecture

The learning path now follows a tighter sequence: necessary knowledge cards, prototype practice, then synthesis writing. Articles remain important, but they are downstream outputs rather than the main learning driver.

1. **Necessary knowledge skeleton**: build a compact concept map for understanding Harness Agent without trying to cover every term in the book.
2. **Core pattern cards and demos**: connect ReAct, Plan-Act, Reflection, CodeAct, and human-in-the-loop to specific failure modes and minimal runnable examples.
3. **Harness component practice**: use the prototype to understand Context, Tools, Skills, Memory, Task System, Compact, and SubAgent.
4. **Prototype evolution**: extend the offline Harness Agent in small stages so every concept has an implementation anchor.
5. **Synthesis article**: write the system article after the knowledge cards and prototype have produced enough concrete experience.

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

Prototype evolution should happen after the first card set exists:

1. Add a Plan-Act demo that creates a short plan and executes each step.
2. Add a Reflection demo that critiques an insufficient result and retries once.
3. Add a CodeAct demo that runs constrained code for a small analysis task.
4. Add a SubAgent demo that isolates a repository-reading or note-summarizing task from the main loop context.

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
- Design a Harness architecture for a repository-analysis Agent.
- Run the prototype and show a multi-step task with persisted task state.
- Publish a coherent article only after the card set and prototype walkthrough can support it.

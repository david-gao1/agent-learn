# Design: Harness Agent Learning System

## Learning Architecture

The learning path has five phases. Each phase produces durable artifacts and has scenario-based acceptance criteria.

1. **Harness Agent overview**: build the mental model that `Agent = Model + Harness`.
2. **Core Agent patterns**: understand intent recognition, plan-execute, reflection, CodeAct, and human-in-the-loop.
3. **Context, memory, and Skills**: understand how useful information is loaded, compressed, persisted, and reused.
4. **Minimal Harness Agent**: build a small offline prototype with loop, tools, Skills, compacting, and task state.
5. **Synthesis**: write a system article and use the prototype to explain the architecture.

## Knowledge Model

The learner should connect these concepts:

- **Context Engineering** selects, shapes, compresses, and injects information into model calls.
- **Agent Loop** keeps the model-tool-environment cycle running across multiple steps.
- **Tools** let the model observe and act outside the chat transcript.
- **Skills** package reusable expert context and load it progressively.
- **Memory** stores facts and task state beyond the immediate context window.
- **SubAgent** isolates noisy execution context from the main agent.
- **Task System** persists work so the agent can resume, audit, and report progress.

## Prototype Design

The prototype is intentionally offline and deterministic. It demonstrates Harness mechanics without depending on a live LLM.

- `HarnessAgent` creates a task, selects a local Skill, observes workspace files through a shell tool, compacts context, and marks the task done.
- `LocalSkillLoader` implements the L1/L2 idea: list labels first, load full `SKILL.md` only when selected.
- `TaskStore` persists tasks to JSON.
- `compact_messages` summarizes older context and keeps recent working memory.
- `run_bash` exposes a constrained command tool with a small safety denylist.

## Final Article Design

The article should teach the system from an engineer's point of view:

1. Why prompt engineering is insufficient for real work.
2. How context engineering changes the unit of design.
3. The five foundational Agent patterns.
4. How Loop, Tools, Skills, Memory, SubAgent, and Task System compose a Harness Agent.
5. What the prototype demonstrates and what it deliberately omits.
6. How DeepResearch, OpenClaw/NanoClaw, and Agent Teams extend the same ideas.

Article drafts should follow `skills/article-depth-writing/SKILL.md`: use purpose-driven titles, start by correcting a common misconception, pursue one central question, use one running example, provide a judgment framework, and include boundaries and costs.

## Validation

Learning is accepted through scenario tests:

- Explain a concept such as Skills, Compact, or SubAgent in terms of problem, mechanism, and risk.
- Design a Harness architecture for a repository-analysis Agent.
- Run the prototype and show a multi-step task with persisted task state.
- Publish a coherent article that a peer engineer can use as a map.

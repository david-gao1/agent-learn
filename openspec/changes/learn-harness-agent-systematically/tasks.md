# Tasks: Learn Harness Agent Systematically

## Phase 1: Harness Agent Overview

- [x] Read chapter 1 and summarize Prompt Engineering vs Context Engineering.
- [x] Write `docs/harness-agent-learning/harness-agent-concept-map.md`.
- [x] Write `docs/harness-agent-learning/chapter-1-deep-dive-questions.md`.
- [x] Draft the short article section: "Why Agent is more than a model".
- [x] Write chapter 1 knowledge articles under `articles/harness-agent/knowledge/chapter-1/`.
- [ ] Acceptance: explain Chatbot, Tool Agent, Code Agent, and Harness Agent differences.

## Phase 2: Core Agent Patterns

- [ ] Read chapter 2 sections on intent recognition, planning, reflection, CodeAct, and human-in-the-loop.
- [ ] Write notes for when each pattern should be used.
- [ ] Map each pattern to one failure mode it reduces.
- [ ] Acceptance: choose a suitable pattern for a given Agent task and justify the tradeoff.

## Phase 3: Context, Memory, And Skills

- [ ] Read chapters 4 and 5.
- [ ] Write `docs/harness-agent-learning/context-memory-skills-strategy.md`.
- [ ] Create a sample Skill under `prototypes/minimal_harness_agent/skills/repo-reading/`.
- [ ] Acceptance: explain Skills vs MCP, RAG, and prompt templates.

## Phase 4: Minimal Harness Agent Prototype

- [x] Add tests for Skill loading, context compacting, task persistence, tools, and offline Agent Loop.
- [x] Implement the minimal prototype in `prototypes/minimal_harness_agent/`.
- [x] Add a README and demo command.
- [x] Acceptance: the prototype completes a multi-step workspace analysis and persists task state.

## Phase 5: Synthesis

- [ ] Complete `articles/harness-agent/from-context-engineering-to-harness-agent.md`.
- [ ] Use the prototype to add a concrete walkthrough to the article.
- [ ] Review the OpenSpec change and archive it after the article and prototype are accepted.
- [ ] Acceptance: a peer engineer can read the article and understand the Harness Agent architecture.

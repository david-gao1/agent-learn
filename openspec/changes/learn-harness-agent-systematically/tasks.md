# Tasks: Learn Harness Agent Systematically

## Phase 1: Necessary Knowledge Skeleton

- [x] Read chapter 1 and summarize Prompt Engineering vs Context Engineering.
- [x] Write `docs/harness-agent-learning/harness-agent-concept-map.md`.
- [x] Write `docs/harness-agent-learning/chapter-1-deep-dive-questions.md`.
- [x] Create `docs/harness-agent-learning/cards/README.md`.
- [x] Write first-pass knowledge cards for Context Engineering, Agent Loop, Tool, ReAct, Plan-Act, Reflection, CodeAct, Memory, Skills, Task System, SubAgent, and Compact.
- [ ] Acceptance: randomly choose a card and explain the problem, mechanism, risk, and prototype position without expanding into a full article.

## Phase 2: Core Agent Patterns

- [ ] Read chapter 2 sections on intent recognition, planning, reflection, CodeAct, and human-in-the-loop.
- [ ] Refine the ReAct, Plan-Act, Reflection, and CodeAct cards with notes from chapter 2.
- [ ] Map each pattern to one failure mode it reduces.
- [x] Add or document minimal demos for Plan-Act, Reflection, and CodeAct.
- [ ] Acceptance: choose a suitable pattern for a given Agent task and justify the tradeoff.

## Phase 3: Context, Memory, Skills, And Tasks

- [ ] Read chapters 4 and 5.
- [x] Write `docs/harness-agent-learning/context-memory-skills-strategy.md`.
- [x] Create a sample Skill under `prototypes/minimal_harness_agent/skills/repo-reading/`.
- [ ] Refine the Context Engineering, Memory, Skills, Task System, and Compact cards after reading chapters 4 and 5.
- [ ] Acceptance: explain Skills vs MCP, RAG, and prompt templates.

## Phase 4: Minimal Harness Agent Prototype

- [x] Add tests for Skill loading, context compacting, task persistence, tools, and offline Agent Loop.
- [x] Implement the minimal prototype in `prototypes/minimal_harness_agent/`.
- [x] Add a README and demo command.
- [x] Add a Plan-Act demo or test.
- [x] Add a Reflection demo or test.
- [x] Add a CodeAct demo or test.
- [ ] Add a SubAgent isolation demo or test.
- [x] Acceptance: the current prototype completes a multi-step workspace analysis and persists task state.
- [x] Acceptance: the evolved prototype demonstrates at least three core patterns beyond the base loop.

## Phase 5: Synthesis

- [x] Preserve existing chapter articles as a material library rather than the current learning bottleneck.
- [ ] Complete `articles/harness-agent/from-context-engineering-to-harness-agent.md`.
- [ ] Use the prototype to add a concrete walkthrough to the article.
- [ ] Review the OpenSpec change and archive it after the cards, article, and prototype are accepted.
- [ ] Acceptance: a peer engineer can read the article and understand the Harness Agent architecture.

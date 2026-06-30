# Tasks: Learn Harness Agent Systematically

## Phase 0: MiniClaw Direction

- [x] Decide that the most complete implementable system from the book is a NanoClaw/OpenClaw-style Harness product.
- [x] Record the decision that MiniClaw composes more Harness mechanisms than implementing DeepResearch, Mem0, or Skills alone.
- [x] Make `prototypes/miniclaw_harness/` the primary implementation path.
- [x] Acceptance: MiniClaw can run an end-to-end local message through channel, store, orchestrator, agent runtime, and output router.
- [x] Acceptance: MiniClaw can schedule a one-shot local task and process it as an agent message.

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
- [x] Write model-logic notes for Plan-Act, Reflection, and CodeAct under `docs/harness-agent-learning/model-logic/`.
- [x] For each model-logic note, explain: what it is, why it exists, principle, problem solved, and how to practice.
- [x] Map each pattern to one failure mode it reduces.
- [x] Add or document minimal demos for Plan-Act, Reflection, and CodeAct.
- [ ] Acceptance: explain a pattern's model logic before looking at its prototype code.
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
- [x] Link each pattern demo to its model-logic note.
- [x] Add a Plan-Act demo or test.
- [x] Add a Reflection demo or test.
- [x] Add a CodeAct demo or test.
- [x] Add an optional real-model smoke test gated by environment variables.
- [ ] Add a SubAgent isolation demo or test.
- [x] Acceptance: the current prototype completes a multi-step workspace analysis and persists task state.
- [x] Acceptance: the evolved prototype demonstrates at least three core patterns beyond the base loop.

## Phase 4B: MiniClaw Harness Product

- [x] Create `prototypes/miniclaw_harness/` with CLI, SQLite store, orchestrator, queue, scheduler, agent runtime, and router.
- [x] Add end-to-end tests for local message processing.
- [x] Add end-to-end tests for one-shot scheduled task processing.
- [x] Add model-backed runtime injection for MiniClaw orchestrator.
- [x] Add optional real-model smoke test for MiniClaw using the OpenAI Responses API adapter.
- [x] Add file-system IPC namespaces with `input/`, `messages/`, and `tasks` directories.
- [x] Add minimal SubAgent context isolation runtime.
- [x] Add in-process background task execution with completion notifications.
- [x] Persist background task state and completed results in SQLite.
- [x] Add CLI commands to launch, list, and inspect background tasks.
- [x] Connect SubAgent isolation to the background task system.
- [x] Add bounded workspace file observation for SubAgent background work.
- [x] Extract workspace file observation into a formal `FileTool`.
- [x] Add bounded `FileTool.read_file()` with workspace escape protection.
- [x] Add allowlisted `BashTool` and wire it into SubAgent background work.
- [x] Add minimal rule-based routing from SubAgent task text to FileTool or BashTool.
- [x] Add structured `ToolDecision` records for SubAgent tool routing.
- [x] Persist `ToolDecision` records in SQLite by background task id.
- [x] Persist execution trace observations for SubAgent background tasks.
- [x] Add a CLI command to inspect a background task's decision and observation trace.
- [x] Expand execution trace into a minimal Agent Loop sequence: plan, decision, tool call, observation, and final result.
- [x] Add a multi-step repository analysis task chain: list files, read file, run tests, and summarize.
- [x] Persist structured repository analysis task state.
- [x] Add a CLI command to inspect structured task state.
- [x] Reuse existing repository analysis task state to skip completed file listing and reading steps.
- [x] Add a CLI command to resume a persisted repository analysis task from state.
- [x] Mark failed repository analysis test runs as blocked state with a recoverable reason.
- [x] Allow repository analysis to resume after blocked test failures and complete with preserved context.
- [x] Add task trace compaction into structured task state.
- [x] Add a CLI command to compact long task traces while keeping recent events.
- [x] Add automatic trace compaction when trace length exceeds a configured threshold.
- [x] Ensure automatic compaction waits until structured task state exists.
- [x] Add an optional model-backed planner for repository analysis.
- [x] Validate model-planned steps before executing them through Harness tools.
- [x] Add a gated real-model smoke test for the repository analysis planner.
- [x] Allow planner parsing to extract JSON plans from model responses with extra prose.
- [x] Add planner failure fallback when model output is invalid JSON or contains no allowed steps.
- [x] Add progressive local Skill loading to MiniClaw repository analysis.
- [x] Add a CLI option for running MiniClaw SubAgent tasks with a local Skills root.
- [x] Document MiniClaw architecture and run commands.
- [x] Acceptance: MiniClaw demonstrates the book's Claw product shell without external IM credentials.
- [x] Acceptance: completed background task state can be read after reopening `MiniClawApp`.
- [x] Acceptance: background tasks can be managed from the CLI without writing Python code.
- [x] Acceptance: SubAgent work can be dispatched as an isolated background task while preserving main-context summary only.
- [x] Acceptance: SubAgent background work can observe workspace file names without loading file contents into the main context.
- [x] Acceptance: SubAgent runtime depends on a file tool interface rather than embedding file traversal logic.
- [x] Acceptance: File reads are bounded and cannot escape the configured workspace.
- [x] Acceptance: Bash execution is allowlisted, workspace-scoped, and does not use unrestricted shell execution.
- [x] Acceptance: list, read, and test-running tasks select different tool paths.
- [x] Acceptance: Tool routing decisions expose action, target, and reason for audit.
- [x] Acceptance: Tool routing decisions can be recovered after reopening `MiniClawApp`.
- [x] Acceptance: A learner can inspect a background task's decision and observation trace from the CLI.
- [x] Acceptance: A learner can inspect how a background task moves from plan to tool call to observation to result.
- [x] Acceptance: A repository analysis task can perform multiple tool actions in one background task.
- [x] Acceptance: Repository analysis state can be recovered after reopening `MiniClawApp`.
- [x] Acceptance: A learner can inspect structured task state from the CLI.
- [x] Acceptance: Repository analysis can continue from existing task state without repeating completed steps.
- [x] Acceptance: A learner can resume a persisted repository analysis task from the CLI.
- [x] Acceptance: Failed repository analysis test runs preserve context and become recoverable blocked tasks.
- [x] Acceptance: Resuming after a blocked test failure can clear the blocked state and complete the task.
- [x] Acceptance: Long task traces can be compacted into task state without losing recent events.
- [x] Acceptance: A learner can compact task traces from the CLI.
- [x] Acceptance: Trace writes can automatically compact long traces while preserving recent events.
- [x] Acceptance: Tasks without structured state are not auto-compacted prematurely.
- [x] Acceptance: A model-backed planner can produce a repository analysis plan while Harness executes only allowed steps.
- [x] Acceptance: Model-generated plans are recorded in trace and task state.
- [x] Acceptance: A real model can be used as planner when real-model test environment variables are configured.
- [x] Acceptance: Planner parsing tolerates extra prose around the JSON plan.
- [x] Acceptance: Invalid or unsafe model plans are recorded as planner errors and fall back to the deterministic Harness plan.
- [x] Acceptance: MiniClaw can inspect Skill labels first, load a matching Skill on demand, and persist the loaded Skill summary in task state.
- [x] Acceptance: A learner can run MiniClaw with `--skills-root` to exercise Skill loading from the CLI.

## Phase 5: Synthesis

- [x] Preserve existing chapter articles as a material library rather than the current learning bottleneck.
- [ ] Complete `articles/harness-agent/from-context-engineering-to-harness-agent.md`.
- [ ] Use the prototype to add a concrete walkthrough to the article.
- [ ] Review the OpenSpec change and archive it after the cards, article, and prototype are accepted.
- [ ] Acceptance: a peer engineer can read the article and understand the Harness Agent architecture.

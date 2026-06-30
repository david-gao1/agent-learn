# Harness Agent Learning Specification

## ADDED Requirements

### Requirement: Stage-Based Learning

The learning system SHALL organize progress by conceptual stages rather than calendar weeks.

#### Scenario: Phase Completion

- **GIVEN** a learner has completed a phase
- **WHEN** they review its acceptance criteria
- **THEN** they can point to a written artifact, prototype artifact, or explanation that demonstrates the phase outcome

### Requirement: System Understanding

The learner SHALL be able to explain how Context Engineering, Agent Loop, Tools, Skills, Memory, SubAgent, and Task System compose a Harness Agent.

#### Scenario: Concept Explanation

- **GIVEN** a concept such as Skills or SubAgent
- **WHEN** the learner explains it
- **THEN** the explanation includes the problem it solves, the mechanism it uses, and at least one engineering risk

### Requirement: Necessary Knowledge Cards

The learning system SHALL maintain a compact set of knowledge cards before prioritizing long-form article polish.

#### Scenario: Card Review

- **GIVEN** a knowledge card for a Harness Agent concept
- **WHEN** it is reviewed
- **THEN** it states the problem solved, core mechanism, minimal example, nearby concept distinction, and prototype position

#### Scenario: Learning Priority Review

- **GIVEN** both knowledge cards and article drafts exist
- **WHEN** the learner chooses the next learning task
- **THEN** unfinished cards and prototype demos take priority over article polishing

### Requirement: Model Logic Before Practice

The learning system SHALL explain a core Agent pattern's model logic before asking the learner to study or implement its prototype.

#### Scenario: Pattern Explanation Before Demo

- **GIVEN** a core pattern such as Plan-Act, Reflection, or CodeAct
- **WHEN** the learner starts practicing it
- **THEN** they first have a note that explains what it is, why it exists, what problem it solves, the operating principle, and how to practice it

#### Scenario: Prototype Mapping

- **GIVEN** a pattern demo exists in the prototype
- **WHEN** the learner reads the demo
- **THEN** the related model-logic note identifies the function, test, or demo that maps the concept to code

### Requirement: Article Output

The learning system SHALL produce a system article about Harness Agent engineering.

#### Scenario: Peer Reader

- **GIVEN** an engineer who understands basic LLM usage
- **WHEN** they read the article
- **THEN** they can distinguish prompt engineering from context engineering and describe the main Harness components

#### Scenario: Article Timing

- **GIVEN** the final system article is being drafted
- **WHEN** the article introduces Harness Agent components
- **THEN** it uses completed knowledge cards and prototype walkthroughs as source material

### Requirement: Article Depth Standard

The learning system SHALL use the article depth writing standard for conceptual articles.

#### Scenario: Focused Article Review

- **GIVEN** a conceptual article draft
- **WHEN** it is reviewed before publication
- **THEN** it has a purpose-driven title, one central question, a common misconception, a redefined core problem, one running example, a reusable judgment framework, clear boundaries and costs, limited visible hierarchy, and a one-sentence takeaway

### Requirement: Article Type Separation

The learning system SHALL separate knowledge articles from exploratory articles.

#### Scenario: Knowledge Article Review

- **GIVEN** a knowledge article draft
- **WHEN** it is reviewed before publication
- **THEN** it explains a concept from problem to mechanism, includes a clear definition, explains the core workflow or causal chain, breaks down only necessary components, and states what the concept solves and does not solve

#### Scenario: Exploratory Article Review

- **GIVEN** an exploratory article draft
- **WHEN** it is reviewed before publication
- **THEN** it pursues one judgment question, corrects a common misconception, uses one running example, provides a judgment framework, and states boundaries and costs without expanding into a full knowledge article

### Requirement: Prototype Output

The learning system SHALL include a minimal runnable Harness Agent prototype.

#### Scenario: Offline Prototype

- **GIVEN** no live LLM API is configured
- **WHEN** the prototype test suite runs
- **THEN** it demonstrates Skill loading, constrained tool execution, context compacting, task persistence, and a multi-step loop

#### Scenario: Pattern Practice

- **GIVEN** the base prototype is already runnable
- **WHEN** the learner evolves it
- **THEN** Plan-Act, Reflection, CodeAct, and SubAgent are explained through model-logic notes before being treated as completed practice demos

### Requirement: MiniClaw Product Prototype

The learning system SHALL include a local MiniClaw prototype that combines Harness Agent internals with a Claw-style product shell.

#### Scenario: Local Message Processing

- **GIVEN** a user message is submitted through the local CLI channel
- **WHEN** the MiniClaw orchestrator runs
- **THEN** the message is persisted, processed by the agent runtime, and routed to an outbound message record

#### Scenario: One-Shot Scheduled Task

- **GIVEN** a one-shot task is scheduled for the current time or earlier
- **WHEN** the MiniClaw scheduler ticks
- **THEN** the task creates a normal inbound message that can be processed by the orchestrator

#### Scenario: Product Shell Learning

- **GIVEN** MiniClaw v0.1 is running locally
- **WHEN** the learner inspects its architecture
- **THEN** they can identify the channel, store, orchestrator, queue, scheduler, agent runtime, and output router responsibilities

#### Scenario: Model-Backed Runtime

- **GIVEN** a model object exposes `complete(instructions, prompt)`
- **WHEN** MiniClaw is opened with a model-backed runtime
- **THEN** the orchestrator uses that model to produce the outbound response while preserving the same channel, store, queue, and router flow

#### Scenario: Optional Real-Model Smoke Test

- **GIVEN** `RUN_REAL_MODEL_TESTS=1` and `OPENAI_API_KEY` are configured
- **WHEN** the MiniClaw test suite runs
- **THEN** MiniClaw processes a local message through the OpenAI-backed runtime and stores a non-empty outbound response

#### Scenario: File-System IPC

- **GIVEN** a group has an IPC namespace with `input`, `messages`, and `tasks` directories
- **WHEN** an input file is drained
- **THEN** it becomes a normal inbound message that can be processed by the orchestrator

#### Scenario: IPC Scheduled Task

- **GIVEN** a task file is written under a group's IPC `tasks` directory
- **WHEN** IPC tasks are drained and the scheduler ticks
- **THEN** the task becomes a normal scheduled message and can be routed back through the same output path

#### Scenario: SubAgent Context Isolation

- **GIVEN** a MiniClaw runtime delegates a message to a SubAgent
- **WHEN** the SubAgent completes its isolated work
- **THEN** the main context stores only the SubAgent summary while child-only details remain outside the main context

#### Scenario: Background Task Completion

- **GIVEN** MiniClaw starts a slow operation as a background task
- **WHEN** the background task completes
- **THEN** MiniClaw can drain a completion notification and convert it into a normal inbound message for orchestration

#### Scenario: Persistent Background Task State

- **GIVEN** MiniClaw starts and completes a background task
- **WHEN** `MiniClawApp` is reopened against the same SQLite database
- **THEN** the completed background task status, command, and result can still be inspected

#### Scenario: Background Task CLI

- **GIVEN** a learner wants to exercise background tasks without writing Python code
- **WHEN** they run `background-run`, `background-list`, and `background-show`
- **THEN** they can start a background task, see it in the persisted task list, and inspect its result

#### Scenario: SubAgent Background Dispatch

- **GIVEN** MiniClaw receives a message that requests isolated SubAgent background work
- **WHEN** the orchestrator processes the message
- **THEN** the main context receives only a dispatch summary while the background task persists the isolated result

#### Scenario: SubAgent Workspace Observation

- **GIVEN** SubAgent background work is configured with a local workspace
- **WHEN** it runs an isolated task
- **THEN** the persisted background result includes a bounded list of observed relative file paths without adding those details to the main context

#### Scenario: File Tool Boundary

- **GIVEN** SubAgent background work needs to observe workspace files
- **WHEN** the runtime performs that observation
- **THEN** it uses a file tool interface instead of embedding file traversal logic in the runtime

#### Scenario: Bounded File Read

- **GIVEN** a file path inside the configured workspace
- **WHEN** `FileTool.read_file()` reads it
- **THEN** the returned text is bounded by the requested character limit

#### Scenario: File Read Escape Protection

- **GIVEN** a path that resolves outside the configured workspace
- **WHEN** `FileTool.read_file()` is called
- **THEN** the read is rejected

#### Scenario: Allowlisted Bash Tool

- **GIVEN** MiniClaw is configured with a local workspace
- **WHEN** `BashTool` executes a command
- **THEN** only allowlisted commands run, execution happens in the workspace, and unrestricted shell execution is not used

#### Scenario: SubAgent Read And Bash Tool Use

- **GIVEN** SubAgent background work has file and bash tools available
- **WHEN** the isolated task runs
- **THEN** the persisted result can include bounded file preview and a small bash observation

#### Scenario: Minimal Tool Routing

- **GIVEN** a SubAgent background task asks to list files, read a file, or run tests
- **WHEN** the runtime executes the isolated task
- **THEN** it routes to file listing, file reading, or allowlisted bash execution respectively

#### Scenario: Auditable Tool Decision

- **GIVEN** SubAgent background work selects a tool path
- **WHEN** the decision is recorded
- **THEN** the decision exposes an action, target, and reason that can be inspected

#### Scenario: Persistent Tool Decision

- **GIVEN** a SubAgent background task has selected a tool path
- **WHEN** `MiniClawApp` is reopened against the same SQLite database
- **THEN** the task's tool decision can still be inspected by background task id

#### Scenario: Execution Trace CLI

- **GIVEN** a SubAgent background task has selected a tool and produced an observation
- **WHEN** the learner runs `trace-show <task-id>`
- **THEN** MiniClaw displays the recorded decision action, target, reason, and observation trace

#### Scenario: Agent Loop Trace

- **GIVEN** a SubAgent background task runs through MiniClaw
- **WHEN** its execution trace is inspected
- **THEN** the trace records the sequence from plan to decision, tool call, observation, and final result

#### Scenario: Multi-Step Repository Analysis

- **GIVEN** a SubAgent background task asks MiniClaw to analyze a repository
- **WHEN** the task runs with file and bash tools available
- **THEN** MiniClaw lists workspace files, reads a bounded file preview, runs the allowlisted test command, and stores a final summary in one background task trace

#### Scenario: Structured Task State

- **GIVEN** a repository analysis task has completed
- **WHEN** MiniClaw is reopened against the same SQLite database or `state-show <task-id>` is run
- **THEN** the files, preview file, bounded preview, test status, test output, and summary are available as structured task state

#### Scenario: State-Based Resume

- **GIVEN** a repository analysis task already has files, preview file, and bounded preview in structured state
- **WHEN** the task continues
- **THEN** MiniClaw skips file listing and file reading, reuses the existing state, and continues with the remaining tool steps

#### Scenario: Resume Task CLI

- **GIVEN** a persisted repository analysis task has partial structured state
- **WHEN** the learner runs `resume-task <task-id>` with the SubAgent runtime and workspace configured
- **THEN** MiniClaw resumes the same background task id, reuses existing state, continues remaining tool steps, and updates trace and structured state

#### Scenario: Blocked Task Recovery

- **GIVEN** a repository analysis task reaches the test step and tests fail
- **WHEN** the task state is inspected
- **THEN** MiniClaw marks the state as blocked, preserves files, preview, test output, and blocked reason, and leaves the task recoverable

#### Scenario: Resume After Blocked Failure

- **GIVEN** a blocked repository analysis task has preserved files and preview
- **WHEN** the task is resumed and tests pass
- **THEN** MiniClaw reuses the preserved context, clears the blocked reason, and marks the structured state completed

#### Scenario: Task Trace Compact

- **GIVEN** a task has a long execution trace and structured task state
- **WHEN** the learner runs `compact-task <task-id>`
- **THEN** MiniClaw writes a compact summary into task state, keeps a compact event and the most recent trace events, and removes older trace noise

#### Scenario: Automatic Trace Compact

- **GIVEN** a task has structured state and trace writes exceed the configured compact threshold
- **WHEN** MiniClaw appends another trace event
- **THEN** MiniClaw automatically writes a compact summary, keeps recent trace events, and avoids premature compaction for tasks that do not yet have structured state

#### Scenario: Model-Backed Planning

- **GIVEN** a repository analysis task is configured with a model-backed planner
- **WHEN** the planner returns a structured plan
- **THEN** MiniClaw validates the allowed steps, records the model plan in trace and task state, and executes the steps through Harness tools

#### Scenario: Real Model Planner Smoke

- **GIVEN** real-model test environment variables are configured
- **WHEN** MiniClaw uses a real model as the repository analysis planner
- **THEN** the model-produced JSON plan is parsed, validated, recorded, and executed by Harness tools

#### Scenario: Planner JSON Extraction

- **GIVEN** a planner response includes prose around a JSON plan
- **WHEN** MiniClaw parses the planner response
- **THEN** it extracts the JSON object, validates allowed steps, and executes the resulting plan

#### Scenario: Planner Failure Fallback

- **GIVEN** a planner response is invalid JSON or contains no allowed repository analysis steps
- **WHEN** MiniClaw plans the repository analysis task
- **THEN** it records a planner error, falls back to the deterministic Harness plan, executes the task through allowed tools, and stores `plan_source: rule_fallback` in task state

### Requirement: OpenSpec Traceability

The learning system SHALL keep proposal, design, tasks, and capability spec files together under one OpenSpec change.

#### Scenario: Progress Review

- **GIVEN** the learner wants to resume later
- **WHEN** they inspect the OpenSpec change
- **THEN** they can identify the goal, current tasks, acceptance criteria, and expected final artifacts

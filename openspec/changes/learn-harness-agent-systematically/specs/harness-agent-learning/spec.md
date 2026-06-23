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

### Requirement: Article Output

The learning system SHALL produce a system article about Harness Agent engineering.

#### Scenario: Peer Reader

- **GIVEN** an engineer who understands basic LLM usage
- **WHEN** they read the article
- **THEN** they can distinguish prompt engineering from context engineering and describe the main Harness components

### Requirement: Prototype Output

The learning system SHALL include a minimal runnable Harness Agent prototype.

#### Scenario: Offline Prototype

- **GIVEN** no live LLM API is configured
- **WHEN** the prototype test suite runs
- **THEN** it demonstrates Skill loading, constrained tool execution, context compacting, task persistence, and a multi-step loop

### Requirement: OpenSpec Traceability

The learning system SHALL keep proposal, design, tasks, and capability spec files together under one OpenSpec change.

#### Scenario: Progress Review

- **GIVEN** the learner wants to resume later
- **WHEN** they inspect the OpenSpec change
- **THEN** they can identify the goal, current tasks, acceptance criteria, and expected final artifacts

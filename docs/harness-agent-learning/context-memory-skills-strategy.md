# Context, Memory, And Skills Strategy

## Context Rules

- Put only task-relevant information into the current model call.
- Keep recent observations verbatim when they affect the next decision.
- Compact older context into summaries once it becomes historical background.
- Treat tool output as raw material, not automatically trusted truth.

## Memory Rules

- Use short-term memory for active task state and recent observations.
- Use compacted summaries for long sessions where exact wording is less important than decisions.
- Use long-term memory for reusable facts, preferences, project conventions, and completed task learnings.
- Avoid storing transient noise such as failed commands unless the failure changes future behavior.

## Skills Rules

- L1: keep only the Skill name and description in the always-available index.
- L2: load `SKILL.md` only after the current task matches the Skill.
- L3: load scripts, references, and assets only when the Skill instructions require them.
- Prefer executable scripts for repeatable actions; send only results back into context.

## Practical Heuristic

Use this decision rule:

- If the information is needed in the next few turns, keep it in context.
- If it summarizes a completed chunk of work, compact it.
- If it should help future sessions, store it as memory.
- If it is reusable expertise, package it as a Skill.

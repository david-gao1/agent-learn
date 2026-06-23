---
name: repo-reading
description: Read a small repository and summarize its structure, entrypoints, and learning value.
---

# Repo Reading Skill

Use this Skill when the user wants to understand a small codebase or learning prototype.

## Workflow

1. List files with `find . -maxdepth 2 -type f | sort` or `rg --files`.
2. Identify likely entrypoints such as `README.md`, `demo.py`, `src/`, and `tests/`.
3. Read the README before source files.
4. Summarize the system in terms of purpose, major components, data flow, and verification command.

## Output Shape

Return:

- Purpose
- Key files
- Runtime flow
- How to verify
- What is intentionally omitted

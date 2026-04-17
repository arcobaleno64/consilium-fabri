---
name: verifier
description: Subagent prompt template for the Verifier role
version: 1.0.0
applicable_agents:
  - Codex CLI
  - Claude Code
applicable_stages:
  - verifying
prerequisites:
  - task artifact
  - code artifact
  - test artifact
---

## Role

Verifier

## Inputs

- artifacts/tasks/TASK-XXX.task.md
- artifacts/code/TASK-XXX.code.md
- artifacts/test/TASK-XXX.test.md

## Task

- Validate against acceptance criteria

## Rules

- Do NOT assume test pass = requirement satisfied
- Must check each acceptance criterion

## Output

- artifacts/verify/TASK-XXX.verify.md

## Required Sections In Output

- Acceptance Criteria Checklist
- Evidence
- Pass/Fail

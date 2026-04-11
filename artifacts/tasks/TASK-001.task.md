# Task: TASK-001 Review Overall Architecture and Workflow

## Metadata
- Task ID: TASK-001
- Artifact Type: task
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-11T07:42:00+08:00

## Objective

Review the overall architecture and workflow of the consilium-fabri repository. Identify gaps, inconsistencies, or missing features between the documentation and the implementation, then fix them.

## Background

The consilium-fabri repository defines an artifact-first, gate-guarded workflow system for multi-agent AI development. The architecture involves:

1. A state machine with 8 states (drafted, researched, planned, coding, testing, verifying, done, blocked)
2. Artifact schemas for task, research, plan, code, test, verify, decision, status, improvement
3. A Python guard validator (`guard_status_validator.py`) that enforces transitions
4. Documentation files in `docs/`
5. Agent entry points (CLAUDE.md, GEMINI.md, CODEX.md)
6. A template sync protocol to `template/`

## Inputs

- All documentation in `docs/`
- `artifacts/scripts/guard_status_validator.py`
- `CLAUDE.md`, `GEMINI.md`, `CODEX.md`, `AGENTS.md`
- `docs/lightweight_mode_rules.md`
- `docs/workflow_state_machine.md`

## Constraints

- Changes must maintain backward compatibility with existing TASK-900 smoke test
- Changes must not break `python guard_status_validator.py --task-id TASK-900`
- All documentation changes must be reflected in both `docs/` and `template/`
- No new external dependencies

## Acceptance Criteria

- [ ] `drafted -> planned` state transition is supported for research-free tasks
- [ ] `docs/workflow_state_machine.md` explicitly documents the `drafted -> planned` path
- [ ] `docs/lightweight_mode_rules.md` includes explicit state transition flow
- [ ] `guard_status_validator.py` allows `drafted -> planned` transition
- [ ] All template/ files are synced with updated docs/
- [ ] TASK-900 smoke test still passes: `python artifacts/scripts/guard_status_validator.py --task-id TASK-900` returns `[OK]`
- [ ] No regressions in validator behavior for standard workflow

## Dependencies

None

## Out of Scope

- Changes to the overall workflow design philosophy
- Adding new agent types beyond the existing 3
- Changing the artifact schema structure
- Modifications to external tooling (Gemini API, Codex CLI integration)

## Current Status Summary

Actively being reviewed. Key finding: `drafted -> planned` transition is not in the legal transitions table, creating a gap for lightweight/research-free tasks.

# Task: TASK-900 Template Smoke Test

## Metadata
- Task ID: TASK-900
- Artifact Type: task
- Owner: Claude
- Status: drafted
- Last Updated: 2026-01-01

## Objective
Verify that the artifact-first workflow template is correctly set up by running the guard_status_validator against this demo task.

## Background
This is a built-in smoke test task included with the template. It exists solely to verify that:
1. The directory structure is correct
2. The guard_status_validator.py can find and parse artifacts
3. State transitions work as expected

## Inputs
- This task file
- The corresponding status file at `artifacts/status/TASK-900.status.json`

## Constraints
- Do not modify this file for production use
- This task should remain as a reference/demo

## Acceptance Criteria
- [ ] `python artifacts/scripts/guard_status_validator.py --task-id TASK-900` returns `[OK]`
- [ ] All artifact directories exist with `.gitkeep`

## Dependencies
None

## Out of Scope
- Any production work
- Modifications to the validator

## Current Status Summary
Demo task for template validation.

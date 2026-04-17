# Plan: TASK-001 Review Overall Architecture and Workflow

## Metadata
- Task ID: TASK-001
- Artifact Type: plan
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-11T07:42:00+08:00

## Scope

Review the consilium-fabri repository architecture and fix the identified gap: the `drafted -> planned` state transition is not listed in `LEGAL_TRANSITIONS`, which makes lightweight mode unusable without going through a `researched` state even when no research is needed.

## Files Likely Affected

- `artifacts/scripts/guard_status_validator.py` — add `planned` to `LEGAL_TRANSITIONS["drafted"]`
- `docs/workflow_state_machine.md` — document the `drafted -> planned` path and update entry conditions for `planned`
- `docs/lightweight_mode_rules.md` — add explicit state transition flow showing `drafted -> planned`
- `template/docs/workflow_state_machine.md` — template sync
- `template/docs/lightweight_mode_rules.md` — template sync
- `template/artifacts/scripts/guard_status_validator.py` — template sync
- `artifacts/tasks/TASK-001.task.md` — create task artifact for this review
- `artifacts/plans/TASK-001.plan.md` — create and refine the execution plan artifact

## Proposed Changes

1. In `guard_status_validator.py`:
   - Change `LEGAL_TRANSITIONS["drafted"]` from `{"researched", "blocked"}` to `{"researched", "planned", "blocked"}`

2. In `docs/workflow_state_machine.md`:
   - Add `-> planned (若任務不需要 research)` to the `drafted` state in the transition diagram
   - Add note to `planned` state entry conditions: lightweight tasks can transition directly from `drafted`

3. In `docs/lightweight_mode_rules.md`:
   - Replace the generic 5-step flow with explicit state machine labels
   - Add a state path example: `drafted -> planned -> coding -> verifying -> done`

4. Sync all changed files to `template/docs/` and `template/artifacts/scripts/`

## Risks

R1
- Risk: Adding `drafted -> planned` breaks isolation between research-required and research-free tasks — tasks that should require research might skip it
- Trigger: Task requires external knowledge but no research artifact exists; developer transitions directly to `planned`
- Detection: Plan artifact would lack a supporting research artifact; `state_required_artifacts` for `planned` would not enforce research unless research already exists
- Mitigation: The guard already handles this correctly — `state_required_artifacts` only adds research to requirements if research artifact already exists; the orchestration docs still mandate research for external-knowledge tasks
- Severity: non-blocking

R2
- Risk: Template files get out of sync if only `docs/` is updated
- Trigger: Files synced at the wrong point in the workflow — e.g. docs updated but template copy forgotten
- Detection: Diff between `docs/` and `template/docs/` shows divergence
- Mitigation: Sync is performed atomically in the same commit as the docs changes
- Severity: non-blocking

R3
- Risk: Allowing `drafted -> planned` globally in validator can be misused to skip required research for tasks that do need external knowledge
- Trigger: Contributor transitions directly from `drafted` to `planned` without research artifact while task actually depends on external references
- Detection: PR review shows no research artifact for a task with externally sourced claims; task narrative conflicts with `docs/orchestration.md §2.4`
- Mitigation: Explicitly document validator limitation and keep research requirement enforced by process/review gate; reject misuse in PR review and require research artifact before approval
- Severity: blocking

## Validation Strategy

1. Run `python artifacts/scripts/guard_status_validator.py --task-id TASK-900` — must return `[OK]`
2. Test `drafted -> planned` transition is now accepted: `python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --from-state drafted --to-state planned` — must return `[OK]`
3. Test `drafted -> coding` is still rejected — must return `[FAIL]`
4. Test `planned -> done` is still rejected — must return `[FAIL]`
5. Verify `template/docs/workflow_state_machine.md` matches `docs/workflow_state_machine.md`
6. Verify `template/docs/lightweight_mode_rules.md` matches `docs/lightweight_mode_rules.md`

## Out of Scope

- Changing the overall state machine design
- Adding new states or new artifact types
- Modifying any schema validation rules beyond the transition table
- Updating README.md or README.zh-TW.md (no feature-level changes visible to end users)

## Ready For Coding

yes

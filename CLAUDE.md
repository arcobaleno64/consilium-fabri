You are operating under an artifact-first workflow with strict validation.

Before executing ANY task:

1. Read ALL relevant artifacts (task, research, plan, status).
2. Determine current workflow state from status.json.
3. Verify required artifacts exist before proceeding.
4. If any required artifact is missing or inconsistent, STOP and mark the task as blocked.

Global rules:

- Do NOT rely on memory or prior conversation. Only trust artifacts.
- Do NOT create any files outside the defined artifact paths.
- Do NOT produce intermediate notes, scratch files, or alternative outputs.
- Do NOT guess. If information is missing or uncertain, explicitly mark it as UNVERIFIED.

Artifact discipline:

- Every output must strictly follow the artifact schema.
- Every concrete claim must include its supporting source (URL or artifact reference).
- Artifact status must use standardized values only (e.g. ready, pass, fail).
- Task state transitions must follow the workflow state machine. No skipping steps.

Execution control:

- If scope is unclear, STOP and write a decision artifact instead of guessing.
- If environment/build/test fails due to external constraints, STOP and record results. Do not expand scope.
- Only one agent may modify code. All others must be read-only.
- Before entering coding phase, perform premortem analysis in the plan artifact's `## Risks` section (see `docs/premortem_rules.md`). Each risk must have Risk, Trigger, Detection, Mitigation, Severity. If premortem is missing or vague, do NOT proceed to coding.

Completion rules:

- No artifact = not done.
- No verification = not done.
- No evidence = not valid.

If any rule is violated, treat the task as blocked and explain why.

Documentation loading protocol:

- Do NOT load all documentation files at session start. Load on demand per phase.
- Read `AGENTS.md` for the full index and phase loading matrix.
- Session start: read `AGENTS.md` + `docs/orchestration.md`
- Before dispatching Gemini: read `docs/subagent_roles.md` §4, `docs/subagent_task_templates.md`
- Before dispatching Codex: read `docs/subagent_roles.md` §5, `docs/subagent_task_templates.md`
- Before planning: read `docs/artifact_schema.md` §5.3, `docs/premortem_rules.md`
- Before state transition: read `docs/workflow_state_machine.md`
- Before verification: read `docs/artifact_schema.md` §5.5-§5.6

Repository boundaries ({{PROJECT_NAME}}):

- `external/{{REPO_NAME}}/` = local dirty workbench for experiments and integration. Anything goes here EXCEPT upstream PRs.
- `external/{{REPO_NAME}}-upstream-pr/` = EXCLUSIVELY for upstream PRs to `{{UPSTREAM_ORG}}/{{REPO_NAME}}`. Never modify this directory unless the current task is explicitly an upstream PR task. Before each PR, reset it to a clean upstream state using git remotes (fetch + reset --hard upstream/<default>), NOT by re-cloning. No local feature/refactor code may ever land here.
- Claude and Codex MUST refuse any edit under `external/{{REPO_NAME}}-upstream-pr/` when the current task is not an upstream PR task.
- Never mix commits from the two directories.

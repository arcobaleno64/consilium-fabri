# Code Result: TASK-956

## Metadata

- Task ID: TASK-956
- Artifact Type: code
- Owner: Codex
- Status: ready
- Last Updated: 2026-04-13T14:23:04+08:00

## Files Changed

- `artifacts/tasks/TASK-956.task.md`
- `artifacts/decisions/TASK-956.decision.md`
- `artifacts/plans/TASK-956.plan.md`
- `artifacts/code/TASK-956.code.md`
- `artifacts/verify/TASK-956.verify.md`
- `artifacts/status/TASK-956.status.json`
- `artifacts/scripts/guard_status_validator.py`
- `template/artifacts/scripts/guard_status_validator.py`
- `artifacts/scripts/run_red_team_suite.py`
- `template/artifacts/scripts/run_red_team_suite.py`
- `artifacts/scripts/drills/prompt_regression_cases.json`
- `template/artifacts/scripts/drills/prompt_regression_cases.json`
- `docs/artifact_schema.md`
- `template/docs/artifact_schema.md`
- `docs/red_team_runbook.md`
- `template/docs/red_team_runbook.md`
- `docs/red_team_backlog.md`
- `template/docs/red_team_backlog.md`
- `README.md`
- `README.zh-TW.md`
- `OBSIDIAN.md`
- `template/README.md`
- `template/README.zh-TW.md`
- `template/OBSIDIAN.md`

## Summary Of Changes

- 將 `guard_status_validator.py` 的 clean-task `commit-range` evidence 升級為 immutable evidence contract：現在必須提供 `Base Commit`、`Head Commit`、`Changed Files Snapshot` 與 `Snapshot SHA256`，並先驗證 snapshot/checksum 後才進行 historical replay。
- 將 scope waiver 邊界再收斂一層：`--allow-scope-drift` 只會降級真正的 drift files；若是 diff evidence 損毀、checksum 不一致、commit SHA 無效或 replay 失敗，guard 仍直接 fail。
- 在 `run_red_team_suite.py` 新增 `RT-014` checksum corruption drill，並重寫 `RT-011` 的 fixture 流程，先建立 historical source commit、再寫入 evidence commit，避免 pinned `Head Commit` 與 code artifact 自我參照。
- 在固定 prompt regression cases 新增 `PR-018`，鎖住 pinned commit 與 snapshot checksum 的 immutable evidence contract。
- 同步更新 schema、runbook、backlog、README 與 Obsidian 入口，說明 pinned commit replay、ref drift warning 與 evidence integrity 邊界。

## Mapping To Plan

- 對應 plan 的 validator 升級：在 root 與 `template/` 的 `guard_status_validator.py` 新增 pinned commit replay、snapshot checksum 與 ref drift warning。
- 對應 plan 的 red-team / regression 擴充：在 root 與 `template/` 的 `run_red_team_suite.py` 與 `prompt_regression_cases.json` 新增 `RT-014` 與 `PR-018`。
- 對應 plan 的 schema / 文件同步：更新 `docs/artifact_schema.md`、`docs/red_team_runbook.md`、`docs/red_team_backlog.md`、README 與 Obsidian 入口文件。

## Tests Added Or Updated

- `python artifacts/scripts/prompt_regression_validator.py --root .`
- `python artifacts/scripts/guard_contract_validator.py --root .`
- `python artifacts/scripts/run_red_team_suite.py --phase static`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --artifacts-root artifacts`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-955 --artifacts-root artifacts`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-956 --artifacts-root artifacts`

## Known Risks

- 若 task 沒有記錄 `## Diff Evidence`，或 pinned commits 對應的 git objects 已被清理，historical scope 審計仍會回退為 artifact-only。
- ref drift 目前只會產生 warning，不會自動阻斷 closure；若後續要更嚴格，仍需 policy 決策。

## Diff Evidence

None (this task was completed in a dirty worktree and did not record a commit-range snapshot for itself)

## Blockers

None
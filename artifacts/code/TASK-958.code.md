# Code Result: TASK-958

## Metadata

- Task ID: TASK-958
- Artifact Type: code
- Owner: Codex
- Status: ready
- Last Updated: 2026-04-13T14:57:33+08:00
- PDCA Stage: D

## Files Changed

- `artifacts/tasks/TASK-958.task.md`
- `artifacts/decisions/TASK-958.decision.md`
- `artifacts/plans/TASK-958.plan.md`
- `artifacts/code/TASK-958.code.md`
- `artifacts/verify/TASK-958.verify.md`
- `artifacts/status/TASK-958.status.json`
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
- `template/README.md`
- `README.zh-TW.md`
- `template/README.zh-TW.md`
- `OBSIDIAN.md`
- `template/OBSIDIAN.md`

## Summary Of Changes

- 在 root 與 `template/` 的 `guard_status_validator.py` 補上 `Archive Path` / `Archive SHA256` metadata 驗證，並在 `commit-range` local git replay 失敗時改走 archive-backed changed-files fallback。
- archive file 現在必須是 repo-relative、UTF-8、每行一個 normalized relative path、排序後、LF 換行的 text file；hash 或內容格式錯誤時會直接 fail，不能被 `--allow-scope-drift` 降級。
- 在 root 與 `template/` 的 `run_red_team_suite.py` 新增 `RT-016` 與 `RT-017`，分別驗證 archive fallback 真的會接手，以及 archive corruption 會被直接攔下。
- 在固定 prompt regression cases 新增 `PR-020`，鎖住 retention / archive fallback contract；同步更新 schema、runbook、backlog、README 與 Obsidian 入口文件。

## Mapping To Plan

- 對應 plan 的 validator 升級：`guard_status_validator.py` 新增 archive metadata 驗證與 `commit-range` fallback 控制流。
- 對應 plan 的 red-team / regression 擴充：`run_red_team_suite.py` 新增 `RT-016`、`RT-017`，`prompt_regression_cases.json` 新增 `PR-020`。
- 對應 plan 的 schema / 文件同步：更新 `docs/artifact_schema.md`、`docs/red_team_runbook.md`、`docs/red_team_backlog.md`、README 與 Obsidian 入口文件，說明 archive format 與 retention policy。

## Tests Added Or Updated

- `python artifacts/scripts/prompt_regression_validator.py --root .`
- `python artifacts/scripts/guard_contract_validator.py --root .`
- `python artifacts/scripts/run_red_team_suite.py --phase static`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --artifacts-root artifacts`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-956 --artifacts-root artifacts`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-957 --artifacts-root artifacts`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-958 --artifacts-root artifacts`

## Known Risks

- archive fallback 只保存 changed-files list，不是完整 patch 或 git object bundle；若後續需要完整 restore，仍需新政策。
- 若 task 沒有記錄 `Archive Path` / `Archive SHA256`，且 local git objects 已消失，commit-range historical replay 仍會直接失敗。

## Diff Evidence

None (this task was completed in a dirty worktree and did not record a historical replay snapshot for itself)


## TAO Trace

Reconstructed from artifact history. This task predates the TAO schema (introduced in TASK-1000 Phase 2).

### Step 1
- Thought Log: (Reconstructed) Reviewed plan Proposed Changes and executed accordingly.
- Action Step: Implemented changes per plan scope.
- Observation: Completed (inferred from verify artifact AC checklist).
- Next-Step Decision: continue

## Blockers

None
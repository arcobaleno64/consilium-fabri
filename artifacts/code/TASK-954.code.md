# Code Result: TASK-954

## Metadata

- Task ID: TASK-954
- Artifact Type: code
- Owner: Codex
- Status: ready
- Last Updated: 2026-04-13T13:46:02+08:00
- PDCA Stage: D

## Files Changed

- `artifacts/tasks/TASK-954.task.md`
- `artifacts/plans/TASK-954.plan.md`
- `artifacts/code/TASK-954.code.md`
- `artifacts/verify/TASK-954.verify.md`
- `artifacts/status/TASK-954.status.json`
- `artifacts/scripts/guard_status_validator.py`
- `template/artifacts/scripts/guard_status_validator.py`
- `artifacts/scripts/run_red_team_suite.py`
- `template/artifacts/scripts/run_red_team_suite.py`
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

- 將 `guard_status_validator.py` 升級為 git-backed scope drift guard：當 task 專屬 artifact 位於 dirty worktree 時，會拿實際 git changed files 比對 plan / code artifact。
- 保留既有 artifact-based scope drift 檢查，並在沒有 task-owned dirty worktree 時回退為相容模式。
- 在 `run_red_team_suite.py` 新增 `RT-010`，用 temp git repo 驗證未宣告的 dirty worktree 檔案會被 guard 直接攔下。
- 同步更新 schema、runbook、backlog 與入口文件，說明新 guard 行為與歷史 diff 的殘餘限制。

## Mapping To Plan

- 對應 plan 的 guard 升級：在 root 與 `template/` 的 `guard_status_validator.py` 新增 git root 偵測與 actual changed files 比對。
- 對應 plan 的 red-team 驗證：在 root 與 `template/` 的 `run_red_team_suite.py` 新增 `RT-010`。
- 對應 plan 的文件同步：更新 `docs/artifact_schema.md`、`docs/red_team_runbook.md`、`docs/red_team_backlog.md` 以及 README / Obsidian 入口。

## Tests Added Or Updated

- `python artifacts/scripts/run_red_team_suite.py --phase static`
- `python artifacts/scripts/guard_contract_validator.py --root .`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --artifacts-root artifacts`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-954 --artifacts-root artifacts`

## Known Risks

- 歷史 clean worktree task 仍無法從 guard 直接重建過去 commit-range diff；目前只在 active task 的 dirty worktree 啟用 git-backed heuristic。


## TAO Trace

Reconstructed from artifact history. This task predates the TAO schema (introduced in TASK-1000 Phase 2).

### Step 1
- Thought Log: (Reconstructed) Reviewed plan Proposed Changes and executed accordingly.
- Action Step: Implemented changes per plan scope.
- Observation: Completed (inferred from verify artifact AC checklist).
- Next-Step Decision: continue

## Blockers

None

# Code Result: TASK-955

## Metadata

- Task ID: TASK-955
- Artifact Type: code
- Owner: Codex
- Status: ready
- Last Updated: 2026-04-13T14:08:38+08:00
- PDCA Stage: D

## Files Changed

- `artifacts/tasks/TASK-955.task.md`
- `artifacts/decisions/TASK-955.decision.md`
- `artifacts/plans/TASK-955.plan.md`
- `artifacts/code/TASK-955.code.md`
- `artifacts/verify/TASK-955.verify.md`
- `artifacts/status/TASK-955.status.json`
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

- 將 `guard_status_validator.py` 升級為兩段式 scope evidence guard：dirty worktree 仍使用實際 git changed files，clean task 則可從 code artifact 的 `commit-range` `## Diff Evidence` 重放 historical diff。
- 收斂 `--allow-scope-drift`：若 scope drift 只想降級為 warning，現在必須存在 decision artifact 的 `## Guard Exception`，且明確列出被豁免的 drift files。
- 在 `run_red_team_suite.py` 新增 `RT-011` 到 `RT-013`，驗證 historical diff replay、缺少 waiver 的例外失敗，以及有顯式 waiver 的受控通過。
- 在固定 prompt regression cases 新增 `PR-016` / `PR-017`，鎖住 decision-gated waiver 與 historical diff evidence contract。
- 同步更新 schema、runbook、backlog、README 與 Obsidian 入口，說明新的 replay 邊界與剩餘缺口。

## Mapping To Plan

- 對應 plan 的 guard 升級：在 root 與 `template/` 的 `guard_status_validator.py` 新增 `commit-range` diff evidence replay 與 waiver 驗證路徑。
- 對應 plan 的 red-team / regression 擴充：在 root 與 `template/` 的 `run_red_team_suite.py` 與 `prompt_regression_cases.json` 新增對應案例。
- 對應 plan 的 schema / 文件同步：更新 `docs/artifact_schema.md`、`docs/red_team_runbook.md`、`docs/red_team_backlog.md` 以及 README / Obsidian 入口文件。

## Tests Added Or Updated

- `python artifacts/scripts/prompt_regression_validator.py --root .`
- `python artifacts/scripts/run_red_team_suite.py --phase static`
- `python artifacts/scripts/guard_contract_validator.py --root .`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --artifacts-root artifacts`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-955 --artifacts-root artifacts`

## Known Risks

- 若歷史 task 沒有記錄 `## Diff Evidence`，或 `Base Ref` / `Head Ref` 在當前 repo 已不可重放，historical scope 審計仍會回退成 artifact-only。
- PR diff evidence 尚未接入；跨 provider 或已合併 PR 的追溯仍屬後續補強範圍。

## Diff Evidence

None (this task was completed in a dirty worktree and did not record a commit-range snapshot for itself)


## TAO Trace

Reconstructed from artifact history. This task predates the TAO schema (introduced in TASK-1000 Phase 2).

### Step 1
- Thought Log: (Reconstructed) Reviewed plan Proposed Changes and executed accordingly.
- Action Step: Implemented changes per plan scope.
- Observation: Completed (inferred from verify artifact AC checklist).
- Next-Step Decision: continue

## Blockers

None

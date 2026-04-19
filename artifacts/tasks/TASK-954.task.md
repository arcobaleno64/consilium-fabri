# Task: TASK-954 Git-Backed Scope Drift Guard

## Metadata
- Task ID: TASK-954
- Artifact Type: task
- Owner: Claude
- Status: done
- Last Updated: 2026-04-13T13:46:02+08:00

## Objective
將 plan/code scope drift 從主要依賴 verify / decision 的人工收斂，提升為 `guard_status_validator.py` 的自動 guard：當 task 專屬 artifacts 正在 dirty worktree 中變動時，直接用實際 git changed files 比對 plan 與 code artifact。

## Background
目前 `guard_status_validator.py` 已會比對 plan 的 `## Files Likely Affected` 與 code 的 `## Files Changed`，但這仍依賴 artifact 自我宣告。M2 要補上 git-backed heuristic，讓 active task 在工作樹中若實際改了未宣告檔案，就被 status guard 直接攔下。

## Inputs
- `artifacts/scripts/guard_status_validator.py`
- `artifacts/scripts/run_red_team_suite.py`
- `docs/artifact_schema.md`
- `docs/red_team_runbook.md`
- `docs/red_team_backlog.md`
- `README.md`
- `README.zh-TW.md`
- `OBSIDIAN.md`

## Constraints
- 不修改產品程式碼或外部 repo
- root 與 `template/` 的 guard script、runner 與文件必須同步
- 新 guard 必須對歷史 clean worktree task 保持相容，不可讓既有 sample task 無故失敗

## Acceptance Criteria
- [x] `guard_status_validator.py` 在 task-owned dirty worktree 存在時，會用實際 git changed files 自動比對 `## Files Changed` 與 `## Files Likely Affected`
- [x] 預設行為仍為 hard fail，`--allow-scope-drift` 可降級為 warning
- [x] 內建 red-team suite 新增一個可重跑的 scope drift auto-guard static case
- [x] root / `template/` 文件同步說明新 guard 行為
- [x] `python artifacts/scripts/guard_status_validator.py --task-id TASK-954 --artifacts-root artifacts` 通過
- [x] `python artifacts/scripts/run_red_team_suite.py --phase static` 通過
- [x] `python artifacts/scripts/guard_contract_validator.py --root .` 通過

## Dependencies
- Python 3
- Git CLI

## Out of Scope
- 建立 commit-range / historical diff reconstruction
- 修改 prompt regression cases

## Assurance Level
POC

## Project Adapter
generic

## Current Status Summary
Completed: status guard now performs git-backed scope checks for active task worktrees, and RT-010 protects the behavior with a repeatable static drill.

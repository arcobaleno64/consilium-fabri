# Task: TASK-955 Historical Diff Evidence And Scope Waiver Hardening

## Metadata

- Task ID: TASK-955
- Artifact Type: task
- Owner: Claude
- Status: done
- Last Updated: 2026-04-13T14:08:38+08:00

## Objective

把 scope drift hardening 再往下推兩層：一是為已提交或已清空工作樹的任務補上可重建的 historical diff evidence；二是把 `--allow-scope-drift` 收斂成必須附 decision artifact 的顯式 guard waiver。

## Background

`TASK-954` 已讓 `guard_status_validator.py` 在 task 專屬 artifacts 位於 dirty worktree 時，自動用實際 git changed files 比對 plan/code 宣告；但對歷史 clean worktree task，guard 仍無法原生重建過去 diff。另一方面，`--allow-scope-drift` 目前只是把 drift 從 error 降為 warning，還沒有要求顯式 decision waiver，治理邊界仍偏鬆。

## Inputs

- `artifacts/scripts/guard_status_validator.py`
- `artifacts/scripts/run_red_team_suite.py`
- `artifacts/scripts/drills/prompt_regression_cases.json`
- `docs/artifact_schema.md`
- `docs/red_team_runbook.md`
- `docs/red_team_backlog.md`
- `README.md`
- `README.zh-TW.md`
- `OBSIDIAN.md`

## Constraints

- 不修改產品程式碼或 `external/` 內容
- root 與 `template/` 的 guard、runner、schema、runbook、入口文件與 regression cases 必須同步
- historical diff reconstruction 需優先使用 repo-local、可重跑、無外部憑證依賴的證據形式
- `--allow-scope-drift` 不可再是口頭例外，必須由 decision artifact 顯式記錄豁免範圍

## Acceptance Criteria

- [x] `guard_status_validator.py` 支援從 code artifact 的 historical diff evidence 重建已提交 task 的 changed files，至少支援 `commit-range` snapshot
- [x] 當 worktree 已 clean 且存在合法 diff evidence 時，scope drift 檢查可用該 evidence 比對 `## Files Changed` 與 `## Files Likely Affected`
- [x] `--allow-scope-drift` 只有在存在顯式 decision waiver 時才可降級為 warning，否則仍應 fail
- [x] red-team static suite 新增可重跑案例，分別覆蓋 historical diff reconstruction 與 decision-gated scope waiver
- [x] root / `template/` 文件與固定 prompt regression 測例同步反映新的 diff evidence / waiver contract
- [x] `python artifacts/scripts/prompt_regression_validator.py --root .` 通過
- [x] `python artifacts/scripts/run_red_team_suite.py --phase static` 通過
- [x] `python artifacts/scripts/guard_contract_validator.py --root .` 通過
- [x] `python artifacts/scripts/guard_status_validator.py --task-id TASK-955 --artifacts-root artifacts` 通過

## Dependencies

- Python 3
- Git CLI

## Out of Scope

- 直接整合 GitHub PR API 或 `gh` 取得 PR diff
- 回填舊任務的 historical diff evidence
- 修改 `CLAUDE.md`、`GEMINI.md`、`CODEX.md` 的 agent 契約文字

## Current Status Summary

Completed: status guard now supports clean-task commit-range replay and only accepts `--allow-scope-drift` when a structured decision waiver explicitly covers the drifted files.

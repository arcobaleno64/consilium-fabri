# Task: TASK-953 Decision-Focused Prompt Regression Expansion

## Metadata
- Task ID: TASK-953
- Artifact Type: task
- Owner: Claude
- Status: done
- Last Updated: 2026-04-13T13:36:04+08:00

## Objective
在既有 prompt regression 基礎上，再補一輪更細的 coverage，優先納入 decision chain integrity，並補強外部失敗時的 STOP 契約。

## Background
`TASK-952` 已將固定 prompt regression 擴充到 11 個案例，但 verify 仍指出 decision chain integrity 尚未被固定 case 保護。目前 workflow 對衝突處理與 decision artifact 的要求主要存在於 `docs/orchestration.md` 與 `docs/artifact_schema.md`，需要納入固定回歸測例，以免後續規則漂移。

## Inputs
- `artifacts/scripts/drills/prompt_regression_cases.json`
- `artifacts/scripts/prompt_regression_validator.py`
- `artifacts/scripts/run_red_team_suite.py`
- `CLAUDE.md`
- `docs/orchestration.md`
- `docs/artifact_schema.md`
- `docs/red_team_runbook.md`

## Constraints
- 不修改產品程式碼或外部 repo
- 新增測例必須對應既有 prompt / workflow contract，不能先新增規則再補測例
- root 與 `template/` 的 regression cases、runner、validator 說明與入口文件必須同步

## Acceptance Criteria
- [x] 固定 prompt regression 測例擴充到至少 15 個案例
- [x] 新增 coverage 至少包含 conflict-to-decision routing、decision artifact schema / trigger integrity、external failure STOP contract
- [x] `python artifacts/scripts/prompt_regression_validator.py --root .` 通過
- [x] `python artifacts/scripts/run_red_team_suite.py --phase prompt` 通過
- [x] `python artifacts/scripts/guard_contract_validator.py --root .` 通過
- [x] `python artifacts/scripts/guard_status_validator.py --task-id TASK-953 --artifacts-root artifacts` 通過

## Dependencies
- Python 3

## Out of Scope
- 實作 M2 的 diff-to-plan 自動 guard
- 變更 `CLAUDE.md`、`GEMINI.md`、`CODEX.md`、`docs/orchestration.md` 或 `docs/artifact_schema.md` 的契約內容

## Assurance Level
POC

## Project Adapter
generic

## Current Status Summary
Completed: prompt regression now covers 15 fixed cases, including decision-focused workflow contracts and external failure STOP behavior.

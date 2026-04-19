# Task: TASK-952 Prompt Regression Coverage Expansion

## Metadata
- Task ID: TASK-952
- Artifact Type: task
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-13T13:04:25+08:00

## Objective
擴充固定 prompt regression 測例，將 coverage 從 7 個案例提升到至少 10 個案例，補上 artifact-only truth、workflow sync completeness、Gemini blocked preconditions 與 Codex summary discipline。

## Background
目前 prompt regression 已涵蓋違規輸入、角色越界、citation、防止 fabrication、truth-source 隔離、research recommendation boundary、blocked wording 與 premortem gate，但對 Claude 的 artifact-only truth / completion contract、workflow sync 完整性，以及 Gemini/Codex 的部分 hard rules 尚未有固定測例保護。

## Inputs
- `artifacts/scripts/drills/prompt_regression_cases.json`
- `artifacts/scripts/prompt_regression_validator.py`
- `artifacts/scripts/run_red_team_suite.py`
- `CLAUDE.md`
- `GEMINI.md`
- `CODEX.md`
- `docs/red_team_runbook.md`

## Constraints
- 只擴充 workflow / red-team coverage，不修改產品程式碼或外部 repo
- root 與 `template/` 的 prompt regression cases、runner 與對應文件必須保持同步
- 不新增未被 prompt 現有契約支撐的測例

## Acceptance Criteria
- [x] 固定 prompt regression 測例擴充到至少 10 個案例
- [x] `run_red_team_suite.py --phase prompt` 納入新增案例，且 root / `template/` 保持一致
- [x] `docs/red_team_runbook.md` 與對應入口文件反映新增 coverage
- [x] `python artifacts/scripts/prompt_regression_validator.py --root .`
- [x] `python artifacts/scripts/run_red_team_suite.py --phase prompt`
- [x] `python artifacts/scripts/guard_contract_validator.py --root .`

## Dependencies
- Python 3

## Out of Scope
- 修改 `CLAUDE.md`、`GEMINI.md`、`CODEX.md` 的 prompt 契約內容
- 新增 diff-to-plan guard 或其他 M2 之後的機制

## Assurance Level
POC

## Project Adapter
generic

## Current Status Summary
Ready to expand fixed prompt regression coverage as the first hardening task from the audit backlog.

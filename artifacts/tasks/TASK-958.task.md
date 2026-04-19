# Task: TASK-958 Git Object Retention And Archive Policy

## Metadata
- Task ID: TASK-958
- Artifact Type: task
- Owner: Claude
- Status: done
- Last Updated: 2026-04-13T14:57:33+08:00

## Objective
補上 `commit-range` evidence 的 git object retention / archive policy，讓 pinned commits 若因 gc、shallow clone 或歷史清理而不可重放時，guard 仍能透過可驗證的 archive file 保留 scope drift 審計能力。

## Background
`TASK-956` 已把 repo-local historical evidence 升級為 pinned commits + snapshot checksum，但 verify 仍明確指出：若 repo 後續執行 aggressive gc 或 objects retention 不足，pinned commits 仍可能消失。這一輪要把風險收斂到 policy + fallback：當 local git objects 缺失時，guard 可以改用 archive file 的 changed-files list 做 reconstruction。

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
- `artifacts/verify/TASK-956.verify.md`

## Constraints
- 不修改產品程式碼或 `external/` 內容
- 不新增外部 Python 套件依賴
- archive policy 應以最小可驗證資訊為主，只保護 scope drift 所需的 changed-files reconstruction；不在本輪嘗試完整 patch / bundle restore
- root 與 `template/` 的 guard、runner、schema、runbook、入口文件與 regression cases 必須同步

## Acceptance Criteria
- [x] `commit-range` diff evidence 支援可選 archive metadata，至少包含 `Archive Path` 與 `Archive SHA256`
- [x] 若 local git replay 失敗但 archive metadata 完整且 archive file 合法，guard 能以 archive file 的 changed-files list 做 fallback 驗證
- [x] archive file 的 hash 與內容格式會被 validator 驗證，損毀或不一致時直接 fail
- [x] red-team static suite 新增可重跑案例，覆蓋 archive fallback 與 archive corruption
- [x] prompt regression 與文件同步反映新的 retention / archive policy
- [x] `python artifacts/scripts/prompt_regression_validator.py --root .` 通過
- [x] `python artifacts/scripts/run_red_team_suite.py --phase static` 通過
- [x] `python artifacts/scripts/guard_contract_validator.py --root .` 通過
- [x] `python artifacts/scripts/guard_status_validator.py --task-id TASK-958 --artifacts-root artifacts` 通過

## Dependencies
- Python 3
- Git CLI

## Out of Scope
- 完整 patch archive 或 git bundle restore
- 修改 agent prompt contracts 本身
- 回補既有舊 task 的 archive file

## Assurance Level
POC

## Project Adapter
generic

## Current Status Summary
Completed: commit-range evidence now supports `Archive Path` / `Archive SHA256`, and the guard can fall back to a validated archive file when local git objects are no longer available.

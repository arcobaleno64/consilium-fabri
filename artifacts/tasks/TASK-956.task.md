# Task: TASK-956 Immutable Diff Evidence Pinning

## Metadata

- Task ID: TASK-956
- Artifact Type: task
- Owner: Claude
- Status: done
- Last Updated: 2026-04-13T14:23:04+08:00

## Objective

縮小 historical diff reconstruction 的殘餘風險，將 clean-task 的 `commit-range` diff evidence 從可重放但仍依賴 refs 的形式，提升為 immutable commit pinning 加 changed-files snapshot checksum。

## Background

`TASK-955` 已讓 status guard 能從 code artifact 的 `commit-range` diff evidence 重放 clean task 的 historical diff，但目前 evidence 仍只依賴 `Base Ref` / `Head Ref` 與 `Diff Command`。這代表 refs 漂移、objects 清理、或後續人工編輯 artifact 時，證據強度仍不夠。這一輪要把 replay evidence pin 到 immutable commit ids，並加入 snapshot checksum，縮小 refs retention 與 artifact 漂移的殘餘風險。

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
- 優先採用 repo-local、無外部憑證依賴的風險收斂手段，不直接整合 remote provider API
- 若新增 diff evidence 欄位，必須可由 red-team fixture 自動產生並驗證

## Acceptance Criteria

- [x] `guard_status_validator.py` 的 `commit-range` diff evidence 支援 immutable `Base Commit` / `Head Commit` pinning
- [x] `## Diff Evidence` 支援 `Changed Files Snapshot` 與 `Snapshot SHA256`，validator 會驗證 checksum 與 replayed diff 的一致性
- [x] 若 `Base Ref` / `Head Ref` 存在但已不再對應 pinned commit，guard 至少會產生明確 warning 或 failure，而不是默默接受
- [x] red-team static suite 新增可重跑案例，覆蓋 corrupted snapshot / checksum 或 ref drift 造成的證據不一致
- [x] prompt regression 與文件同步反映新的 immutable evidence contract
- [x] `python artifacts/scripts/prompt_regression_validator.py --root .` 通過
- [x] `python artifacts/scripts/run_red_team_suite.py --phase static` 通過
- [x] `python artifacts/scripts/guard_contract_validator.py --root .` 通過
- [x] `python artifacts/scripts/guard_status_validator.py --task-id TASK-956 --artifacts-root artifacts` 通過

## Dependencies

- Python 3
- Git CLI

## Out of Scope

- 直接整合 GitHub / GitLab PR diff API
- 回補舊 task 的 diff evidence
- 修改 agent prompt contracts 本身

## Current Status Summary

Completed: clean-task diff evidence now uses immutable pinned commits plus a checksummed changed-files snapshot, and corrupted evidence can no longer hide behind `--allow-scope-drift`.
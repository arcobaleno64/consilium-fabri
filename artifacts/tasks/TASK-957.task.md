# Task: TASK-957 GitHub Provider-Backed PR Diff Evidence

## Metadata

- Task ID: TASK-957
- Artifact Type: task
- Owner: Claude
- Status: done
- Last Updated: 2026-04-13T14:57:33+08:00

## Objective

補上 provider-backed historical diff evidence 的第一個 provider 實作，讓 clean-task 除了 repo-local `commit-range` 之外，也能以 GitHub pull request files API 重建 changed files 並做 scope drift 驗證。

## Background

`TASK-956` 已把 repo-local `commit-range` evidence 做到 pinned commit 與 checksum 驗證，但 `artifacts/verify/TASK-956.verify.md` 與 `docs/red_team_backlog.md` 仍指出：若需要追溯已合併 PR、跨 clone 歷史、或本地 git objects 不完整，guard 仍缺少 provider-backed path。這一輪先做 GitHub provider，將 historical diff evidence 從純 repo-local 擴充為 provider-backed 可選路徑。

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
- provider-backed path 先以 GitHub 為第一個 provider；不在本輪擴充到 GitLab / Azure / Bitbucket
- 不新增外部 Python 套件依賴；若需要 provider 存取，優先使用標準函式庫與環境變數 token
- red-team 必須可在無外網環境下重跑，不能把 static suite 綁到真實 GitHub 網路呼叫
- root 與 `template/` 的 guard、runner、schema、runbook、入口文件與 regression cases 必須同步

## Acceptance Criteria

- [x] `guard_status_validator.py` 支援新的 provider-backed diff evidence type，用 GitHub PR files API 取得 changed files
- [x] provider-backed evidence 至少支援 `Repository`、`PR Number`、可選 `API Base URL`、`Changed Files Snapshot` 與 `Snapshot SHA256`
- [x] public repo 可在無 token 下存取；private repo 或受限環境則能從 `GITHUB_TOKEN` 或 `GH_TOKEN` 讀取認證，失敗時回報明確錯誤
- [x] provider 回傳的 files list 會被拿來比對 `## Files Changed` 與 `## Files Likely Affected`，並沿用 checksum / drift 規則
- [x] red-team static suite 新增可重跑案例，覆蓋 provider-backed PR diff reconstruction
- [x] prompt regression 與文件同步反映新的 GitHub provider-backed evidence contract
- [x] `python artifacts/scripts/prompt_regression_validator.py --root .` 通過
- [x] `python artifacts/scripts/run_red_team_suite.py --phase static` 通過
- [x] `python artifacts/scripts/guard_contract_validator.py --root .` 通過
- [x] `python artifacts/scripts/guard_status_validator.py --task-id TASK-957 --artifacts-root artifacts` 通過

## Dependencies

- Python 3
- Git CLI

## Out of Scope

- GitLab / Azure DevOps / Bitbucket provider support
- 修改 agent prompt contracts 本身
- 回補既有舊 task 的 provider-backed evidence

## Current Status Summary

Completed: GitHub PR files are now available as the first provider-backed historical diff evidence path, with pagination, token-aware fetches, red-team drills, and synced workflow contracts.
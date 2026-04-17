# Verification: TASK-957

## Metadata

- Task ID: TASK-957
- Artifact Type: verify
- Owner: Claude
- Status: pass
- Last Updated: 2026-04-13T14:57:33+08:00

## Acceptance Criteria Checklist

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

## Evidence

- `python artifacts/scripts/prompt_regression_validator.py --root .` 回報 `PR-001` 到 `PR-020` 全數 pass，其中 `PR-019` 已鎖住 GitHub provider-backed diff evidence contract。
- `python artifacts/scripts/guard_contract_validator.py --root .` 回報 `[OK] Contract validation passed`。
- `python artifacts/scripts/run_red_team_suite.py --phase static` 的報表中，`RT-015` 以預期失敗方式證明 `github-pr` evidence 會抓到第二頁 PR files 並攔截未宣告 drift；`RT-013` 仍以預期成功方式通過。
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --artifacts-root artifacts` 回報 `[OK] Validation passed`，表示既有 smoke sample 未被 provider-backed evidence 新增路徑打壞。
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-956 --artifacts-root artifacts` 回報 `[OK] Validation passed`，表示 immutable commit-range contract 與新的 provider-backed path 可共存。
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-957 --artifacts-root artifacts` 回報 `[OK] Validation passed`。

## Build Guarantee

None (no product code or build targets modified) — 本任務只修改 workflow guards、red-team drills、schema 與入口文件。

## Pass Fail Result

pass

## Remaining Gaps

- provider-backed historical diff evidence 目前只支援 GitHub，其他 provider 仍未納入。
- GitHub provider 路徑仍受 auth、rate-limit 與 endpoint file-count 上限影響。
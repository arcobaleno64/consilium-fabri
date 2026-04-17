# Verification: TASK-958

## Metadata

- Task ID: TASK-958
- Artifact Type: verify
- Owner: Claude
- Status: pass
- Last Updated: 2026-04-13T14:57:33+08:00

## Acceptance Criteria Checklist

- [x] `commit-range` diff evidence 支援可選 archive metadata，至少包含 `Archive Path` 與 `Archive SHA256`
- [x] 若 local git replay 失敗但 archive metadata 完整且 archive file 合法，guard 能以 archive file 的 changed-files list 做 fallback 驗證
- [x] archive file 的 hash 與內容格式會被 validator 驗證，損毀或不一致時直接 fail
- [x] red-team static suite 新增可重跑案例，覆蓋 archive fallback 與 archive corruption
- [x] prompt regression 與文件同步反映新的 retention / archive policy
- [x] `python artifacts/scripts/prompt_regression_validator.py --root .` 通過
- [x] `python artifacts/scripts/run_red_team_suite.py --phase static` 通過
- [x] `python artifacts/scripts/guard_contract_validator.py --root .` 通過
- [x] `python artifacts/scripts/guard_status_validator.py --task-id TASK-958 --artifacts-root artifacts` 通過

## Evidence

- `python artifacts/scripts/prompt_regression_validator.py --root .` 回報 `PR-001` 到 `PR-020` 全數 pass，其中 `PR-020` 已鎖住 archive retention fallback contract。
- `python artifacts/scripts/guard_contract_validator.py --root .` 回報 `[OK] Contract validation passed`。
- `python artifacts/scripts/run_red_team_suite.py --phase static` 的報表中，`RT-016` 以預期失敗方式證明 git objects 缺失時 archive fallback 會接手並攔截未宣告 drift，`RT-017` 以預期失敗方式證明 archive hash 損毀不會被接受。
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --artifacts-root artifacts` 回報 `[OK] Validation passed`，表示既有 smoke sample 未被 archive fallback 邏輯打壞。
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-956 --artifacts-root artifacts` 回報 `[OK] Validation passed`，表示先前 immutable evidence contract 與新的 archive policy 相容。
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-958 --artifacts-root artifacts` 回報 `[OK] Validation passed`。

## Build Guarantee

None (no product code or build targets modified) — 本任務只修改 workflow guards、red-team drills、schema 與入口文件。

## Pass Fail Result

pass

## Remaining Gaps

- archive fallback 目前只保存 changed-files list，不提供完整 patch 或 git object bundle restore。
- 若 task 完全沒有記錄 archive metadata，long-term git object retention 仍需流程紀律保證。
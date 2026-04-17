# Verification: TASK-956

## Metadata

- Task ID: TASK-956
- Artifact Type: verify
- Owner: Claude
- Status: pass
- Last Updated: 2026-04-13T14:23:04+08:00

## Acceptance Criteria Checklist

- [x] `guard_status_validator.py` 的 `commit-range` diff evidence 支援 immutable `Base Commit` / `Head Commit` pinning
- [x] `## Diff Evidence` 支援 `Changed Files Snapshot` 與 `Snapshot SHA256`，validator 會驗證 checksum 與 replayed diff 的一致性
- [x] 若 `Base Ref` / `Head Ref` 存在但已不再對應 pinned commit，guard 至少會產生明確 warning 或 failure，而不是默默接受
- [x] red-team static suite 新增可重跑案例，覆蓋 corrupted snapshot / checksum 造成的證據不一致
- [x] prompt regression 與文件同步反映新的 immutable evidence contract
- [x] `python artifacts/scripts/prompt_regression_validator.py --root .` 通過
- [x] `python artifacts/scripts/run_red_team_suite.py --phase static` 通過
- [x] `python artifacts/scripts/guard_contract_validator.py --root .` 通過
- [x] `python artifacts/scripts/guard_status_validator.py --task-id TASK-956 --artifacts-root artifacts` 通過

## Evidence

- `python artifacts/scripts/prompt_regression_validator.py --root .` 回報 `PR-001` 到 `PR-018` 全數 pass，其中 `PR-018` 已鎖住 pinned commit 與 snapshot checksum contract。
- `python artifacts/scripts/guard_contract_validator.py --root .` 回報 `[OK] Contract validation passed`。
- `python artifacts/scripts/run_red_team_suite.py --phase static` 的報表中，`RT-011` 以預期失敗方式證明 pinned historical replay 仍能抓 scope drift，`RT-014` 以預期失敗方式證明 checksum corruption 不會被接受，`RT-013` 仍以預期成功方式通過。
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --artifacts-root artifacts` 回報 `[OK] Validation passed`，表示既有 smoke sample 未被新 immutable evidence 規則打壞。
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-955 --artifacts-root artifacts` 回報 `[OK] Validation passed`，表示前一輪 historical diff evidence contract 與新欄位要求相容。
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-956 --artifacts-root artifacts` 回報 `[OK] Validation passed`。

## Build Guarantee

None (no product code or build targets modified) — 本任務只修改 workflow guards、red-team drills、schema 與入口文件。

## Pass Fail Result

pass

## Remaining Gaps

- provider-backed PR diff evidence 仍未接入；跨 provider 或遠端已合併 PR 的追溯仍屬後續補強範圍。
- 若 repo 後續執行 aggressive gc 或物件清理，pinned commits 的長期 retention 仍需額外政策支撐。
# Verification: TASK-952

## Metadata
- Task ID: TASK-952
- Artifact Type: verify
- Owner: Claude
- Status: pass
- Last Updated: 2026-04-13T13:07:07+08:00

## Acceptance Criteria Checklist
- [x] 固定 prompt regression 測例已擴充到至少 10 個案例（目前為 11 個）
- [x] `run_red_team_suite.py --phase prompt` 已納入新增案例，且 root / `template/` 保持一致
- [x] `docs/red_team_runbook.md` 與對應入口文件已反映新增 coverage
- [x] `python artifacts/scripts/prompt_regression_validator.py --root .` 通過
- [x] `python artifacts/scripts/run_red_team_suite.py --phase prompt` 通過
- [x] `python artifacts/scripts/guard_contract_validator.py --root .` 通過

## Evidence
- `python artifacts/scripts/prompt_regression_validator.py --root .` 回報 `PR-001` 到 `PR-011` 全數 pass。
- `python artifacts/scripts/run_red_team_suite.py --phase prompt` 的 prompt phase 報表已包含 `PR-008` 到 `PR-011`。
- `python artifacts/scripts/guard_contract_validator.py --root .` 回報 `[OK] Contract validation passed`。
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-952 --artifacts-root artifacts` 回報 `[OK] Validation passed`。

## Build Guarantee
None (no product code or build targets modified) — 本任務僅擴充 workflow prompt regression coverage 與對應文件。

## Pass Fail Result
pass

## Remaining Gaps
- prompt regression 仍未覆蓋 diff-to-plan 自動 guard 與 decision chain integrity；這兩項屬於 M2 或後續 hardening 範圍。

## Recommendation
下一步可直接進入 M2，將 code-plan scope drift 從人工 verify / decision 收斂提升為自動 guard。
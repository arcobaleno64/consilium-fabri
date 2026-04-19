# Verification: TASK-955

## Metadata
- Task ID: TASK-955
- Artifact Type: verify
- Owner: Claude
- Status: pass
- Last Updated: 2026-04-13T14:08:38+08:00

## Verification Summary
Migrated from legacy verify artifact.

## Acceptance Criteria Checklist
- **criterion**: `guard_status_validator.py` 支援從 code artifact 的 historical diff evidence 重建已提交 task 的 changed files，至少支援 `commit-range` snapshot
- **method**: Artifact and command evidence review
- **evidence**: `python artifacts/scripts/prompt_regression_validator.py --root .` 回報 `PR-001` 到 `PR-017` 全數 pass，其中 `PR-016` / `PR-017` 已鎖住 decision-gated waiver 與 historical diff evidence contract。
- **result**: verified

- **criterion**: 當 worktree 已 clean 且存在合法 diff evidence 時，scope drift 檢查可用該 evidence 比對 `## Files Changed` 與 `## Files Likely Affected`
- **method**: Artifact and command evidence review
- **evidence**: `python artifacts/scripts/run_red_team_suite.py --phase static` 的報表中，`RT-011`、`RT-012` 以預期失敗方式通過，`RT-013` 以預期成功方式通過，證明 historical replay 與顯式 waiver 兩條新路徑都可重跑驗證。
- **result**: verified

- **criterion**: `--allow-scope-drift` 只有在存在顯式 decision waiver 時才可降級為 warning，否則仍應 fail
- **method**: Artifact and command evidence review
- **evidence**: `python artifacts/scripts/guard_contract_validator.py --root .` 回報 `[OK] Contract validation passed`。
- **result**: verified

- **criterion**: red-team static suite 已新增可重跑案例，分別覆蓋 historical diff reconstruction 與 decision-gated scope waiver
- **method**: Artifact and command evidence review
- **evidence**: `python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --artifacts-root artifacts` 回報 `[OK] Validation passed`，表示既有 clean sample 未被新邏輯打壞。
- **result**: verified

- **criterion**: root / `template/` 文件與固定 prompt regression 測例已同步反映新的 diff evidence / waiver contract
- **method**: Artifact and command evidence review
- **evidence**: `python artifacts/scripts/guard_status_validator.py --task-id TASK-955 --artifacts-root artifacts` 回報 `[OK] Validation passed`。
- **result**: verified

- **criterion**: `python artifacts/scripts/prompt_regression_validator.py --root .` 通過
- **method**: Artifact and command evidence review
- **evidence**: `python artifacts/scripts/prompt_regression_validator.py --root .` 回報 `PR-001` 到 `PR-017` 全數 pass，其中 `PR-016` / `PR-017` 已鎖住 decision-gated waiver 與 historical diff evidence contract。
- **result**: verified

- **criterion**: `python artifacts/scripts/run_red_team_suite.py --phase static` 通過
- **method**: Artifact and command evidence review
- **evidence**: `python artifacts/scripts/prompt_regression_validator.py --root .` 回報 `PR-001` 到 `PR-017` 全數 pass，其中 `PR-016` / `PR-017` 已鎖住 decision-gated waiver 與 historical diff evidence contract。
- **result**: verified

- **criterion**: `python artifacts/scripts/guard_contract_validator.py --root .` 通過
- **method**: Artifact and command evidence review
- **evidence**: `python artifacts/scripts/prompt_regression_validator.py --root .` 回報 `PR-001` 到 `PR-017` 全數 pass，其中 `PR-016` / `PR-017` 已鎖住 decision-gated waiver 與 historical diff evidence contract。
- **result**: verified

- **criterion**: `python artifacts/scripts/guard_status_validator.py --task-id TASK-955 --artifacts-root artifacts` 通過
- **method**: Artifact and command evidence review
- **evidence**: `python artifacts/scripts/prompt_regression_validator.py --root .` 回報 `PR-001` 到 `PR-017` 全數 pass，其中 `PR-016` / `PR-017` 已鎖住 decision-gated waiver 與 historical diff evidence contract。
- **result**: verified

## Overall Maturity
poc

## Deferred Items
- 歷史 scope reconstruction 目前只支援 repo-local `commit-range` evidence；若 refs 不可重放或需要外部 provider 的 PR diff，仍需後續補強。
- `TASK-955` 自身沒有 commit-range snapshot，因為這次實作是在 dirty worktree 中完成；新 schema 主要保護後續 clean task 的可追溯性。

## Evidence
- `python artifacts/scripts/prompt_regression_validator.py --root .` 回報 `PR-001` 到 `PR-017` 全數 pass，其中 `PR-016` / `PR-017` 已鎖住 decision-gated waiver 與 historical diff evidence contract。
- `python artifacts/scripts/run_red_team_suite.py --phase static` 的報表中，`RT-011`、`RT-012` 以預期失敗方式通過，`RT-013` 以預期成功方式通過，證明 historical replay 與顯式 waiver 兩條新路徑都可重跑驗證。
- `python artifacts/scripts/guard_contract_validator.py --root .` 回報 `[OK] Contract validation passed`。
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --artifacts-root artifacts` 回報 `[OK] Validation passed`，表示既有 clean sample 未被新邏輯打壞。
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-955 --artifacts-root artifacts` 回報 `[OK] Validation passed`。

## Evidence Refs
None

## Decision Refs
- `artifacts/decisions/TASK-955.decision.md`

## Build Guarantee
None (no product code or build targets modified) — 本任務只修改 workflow guards、red-team drills、schema 與入口文件。

## Pass Fail Result
pass

## Recommendation
M2 的第二步已完成；若要再往下走，下一輪可以把 PR diff evidence 或 diff checksum 接進 historical reconstruction，縮小 refs retention 的殘餘風險。

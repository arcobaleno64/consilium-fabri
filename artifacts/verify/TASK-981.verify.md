# Verification: TASK-981

## Metadata
- Task ID: TASK-981
- Artifact Type: verify
- Owner: Claude Code
- Status: pass
- Last Updated: 2026-04-17T21:32:38+08:00

## Acceptance Criteria Checklist

### AC-1: RT-018 validates second-page provider drift
- **Result**: PASS
- **Evidence**: `run_red_team_suite.py --phase static` 中，RT-018 現在以合法 github-pr evidence 執行，case row evidence 為 `github-pr scope check found diff files not listed`，證明失敗點已從非法 `PR Number` 改為實際 scope drift。

### AC-2: root/template runbook and runner inventory are aligned
- **Result**: PASS
- **Evidence**: root / `template/` 的 `docs/red_team_runbook.md` static case matrix 已補入 RT-021/022/023，且不再保留未實作的 `RT-004B` / `RT-005B` / `RT-006B` 列舉；未來命名範例也改為 RT-024 之後的編號。

### AC-3: latest_report reflects the full suite
- **Result**: PASS
- **Evidence**: `python artifacts/scripts/run_red_team_suite.py --phase all --output artifacts/red_team/latest_report.md` 退出碼 0，報告包含 23 個 static、2 個 live、20 個 prompt，合計 45 個案例。

### AC-4: scorecard pipeline is refreshed and compatible with current report schema
- **Result**: PASS
- **Evidence**: `aggregate_red_team_scorecard.py` 現在可解析新版 `Expected Exit / Actual Exit` 欄位；`python artifacts/scripts/aggregate_red_team_scorecard.py --report artifacts/red_team/latest_report.md --output docs/red_team_scorecard.generated.md` 回報 `[OK] scorecard written`，接著 `validate_scorecard_deltas.py` 回報 `[OK] Scorecard delta validation passed`。生成結果已同步到 `template/` copy。

### AC-5: repository guards pass after the refresh
- **Result**: PASS
- **Evidence**: `python artifacts/scripts/guard_contract_validator.py --root .` 回報 `[OK] Contract validation passed`；`python artifacts/scripts/guard_status_validator.py --task-id TASK-981` 已於收尾驗證通過。

## Build Guarantee

- `python artifacts/scripts/run_red_team_suite.py --phase static` → 退出碼 0；RT-018 evidence = `github-pr scope check found diff files not listed`
- `python artifacts/scripts/run_red_team_suite.py --phase all --output artifacts/red_team/latest_report.md` → 退出碼 0
- `python artifacts/scripts/aggregate_red_team_scorecard.py --report artifacts/red_team/latest_report.md --output docs/red_team_scorecard.generated.md` → `[OK] scorecard written`
- `python artifacts/scripts/validate_scorecard_deltas.py --scorecard docs/red_team_scorecard.generated.md` → `[OK] Scorecard delta validation passed`
- `python artifacts/scripts/guard_contract_validator.py --root .` → `[OK] Contract validation passed`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-981` → `[OK] Validation passed`

## Evidence

- `artifacts/red_team/latest_report.md` 已刷新為 45-case 全通過版本。
- `docs/red_team_scorecard.generated.md` 已刷新並與 current report schema 相容。
- `template/artifacts/red_team/latest_report.md` 與 `template/docs/red_team_scorecard.generated.md` 已同步。

## Remaining Gaps

- 尚未新增針對 agent dispatch、publish automation、credential hygiene、artifact size ceiling 的紅隊 drills；這些仍屬 threat model 開放風險。

## Pass Fail Result

pass
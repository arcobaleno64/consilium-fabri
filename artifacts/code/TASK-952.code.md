# Code Result: TASK-952

## Metadata
- Task ID: TASK-952
- Artifact Type: code
- Owner: Codex
- Status: ready
- Last Updated: 2026-04-13T13:07:07+08:00

## Files Changed
- `artifacts/scripts/drills/prompt_regression_cases.json`
- `template/artifacts/scripts/drills/prompt_regression_cases.json`
- `artifacts/scripts/run_red_team_suite.py`
- `template/artifacts/scripts/run_red_team_suite.py`
- `docs/red_team_runbook.md`
- `template/docs/red_team_runbook.md`
- `README.md`
- `README.zh-TW.md`
- `OBSIDIAN.md`
- `template/README.md`
- `template/README.zh-TW.md`
- `template/OBSIDIAN.md`
- `artifacts/status/TASK-952.status.json`

## Summary Of Changes
- 將固定 prompt regression 測例從 7 個擴充到 11 個，新增 artifact-only truth / completion、workflow sync completeness、research blocked preconditions、implementation summary discipline。
- 更新 prompt phase red-team runner，讓 `run_red_team_suite.py --phase prompt` 會執行新增案例。
- 同步更新 red-team runbook 與 root / `template/` 入口文件，明確說明新增 coverage。

## Mapping To Plan
- 對應 plan 的 cases 擴充：在 root 與 `template/` 的 `prompt_regression_cases.json` 新增 `PR-008` 到 `PR-011`。
- 對應 plan 的 runner 擴充：在 root 與 `template/` 的 `run_red_team_suite.py` 註冊新案例。
- 對應 plan 的文件同步：更新 runbook、README 與 Obsidian 入口，反映 prompt regression coverage 擴充。

## Tests Added Or Updated
- `python artifacts/scripts/prompt_regression_validator.py --root .`
- `python artifacts/scripts/run_red_team_suite.py --phase prompt`
- `python artifacts/scripts/guard_contract_validator.py --root .`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-952 --artifacts-root artifacts`

## Known Risks
- 若後續再新增或更名 prompt regression case，`prompt_regression_cases.json`、`run_red_team_suite.py` 與 runbook 仍必須同步維護。

## Blockers
None
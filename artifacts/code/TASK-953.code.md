# Code Result: TASK-953

## Metadata
- Task ID: TASK-953
- Artifact Type: code
- Owner: Codex
- Status: ready
- Last Updated: 2026-04-13T13:36:04+08:00

## Files Changed
- `artifacts/scripts/drills/prompt_regression_cases.json`
- `template/artifacts/scripts/drills/prompt_regression_cases.json`
- `artifacts/scripts/run_red_team_suite.py`
- `template/artifacts/scripts/run_red_team_suite.py`
- `artifacts/scripts/prompt_regression_validator.py`
- `template/artifacts/scripts/prompt_regression_validator.py`
- `docs/red_team_runbook.md`
- `template/docs/red_team_runbook.md`
- `README.md`
- `README.zh-TW.md`
- `OBSIDIAN.md`
- `template/README.md`
- `template/README.zh-TW.md`
- `template/OBSIDIAN.md`
- `artifacts/status/TASK-953.status.json`

## Summary Of Changes
- 將固定 prompt regression 擴充到 15 個案例，新增 `PR-012` 到 `PR-015`，鎖住 conflict-to-decision routing、decision artifact trigger matrix、decision schema completeness 與 external failure STOP contract。
- 更新 prompt phase runner，讓 red-team prompt phase 報表納入新案例。
- 更新 prompt regression validator 說明與 root / `template/` 文件，明確表達 coverage 已包含關鍵 workflow contracts。

## Mapping To Plan
- 對應 plan 的 cases 擴充：在 root 與 `template/` 的 `prompt_regression_cases.json` 新增 `PR-012` 到 `PR-015`。
- 對應 plan 的 runner / validator 說明更新：同步更新 `run_red_team_suite.py` 與 `prompt_regression_validator.py`。
- 對應 plan 的文件同步：更新 runbook、README 與 Obsidian 入口，說明新的 decision-focused coverage。

## Tests Added Or Updated
- `python artifacts/scripts/prompt_regression_validator.py --root .`
- `python artifacts/scripts/run_red_team_suite.py --phase prompt`
- `python artifacts/scripts/guard_contract_validator.py --root .`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-953 --artifacts-root artifacts`

## Known Risks
- 若後續 decision workflow 規則改動，`docs/orchestration.md` / `docs/artifact_schema.md` 與對應 regression case 仍需同步維護。

## Blockers
None
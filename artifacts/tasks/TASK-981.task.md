# Task: TASK-981 Red Team RT-018 Drift Repair And Report Refresh

## Metadata
- Task ID: TASK-981
- Artifact Type: task
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-17T21:26:46+08:00

## Objective

修正 RT-018 的文件與實作漂移，讓 provider-backed github-pr 紅隊案例真正驗證「第二頁未宣告檔案」情境，並同步刷新 red-team runbook / report / scorecard，讓 checked-in 文檔與 runner 現況一致。

## Background

- 目前 [docs/red_team_runbook.md](docs/red_team_runbook.md) 將 RT-018 描述為「GitHub provider-backed PR files 含第二頁未宣告檔案」，但 [artifacts/scripts/run_red_team_suite.py](artifacts/scripts/run_red_team_suite.py) 的 RT-018 實際測的是非法 `PR Number`。
- `run_red_team_suite.py --phase all` 現況已包含 45 個案例，但 checked-in 的 `artifacts/red_team/latest_report.md` 與 `docs/red_team_scorecard.generated.md` 仍停留在較舊的案例集。
- root / template / generated docs 需要重新對齊，避免 red-team 文件再度與 runner 漂移。

## Inputs

- `artifacts/scripts/run_red_team_suite.py`
- `template/artifacts/scripts/run_red_team_suite.py`
- `docs/red_team_runbook.md`
- `template/docs/red_team_runbook.md`
- `artifacts/scripts/aggregate_red_team_scorecard.py`

## Constraints

- 不得改變 RT-018 的目標為其他檢查；必須落回 runbook 宣稱的第二頁 provider drift 情境。
- 若更新 runbook，必須同步 `template/`。
- generated report 與 scorecard 必須由實際 runner 重新產生，不可手寫偽造。
- 本 task 僅處理紅隊 runner / 文件 / generated artifacts，不處理其他 threat-model open findings 的實作修補。

## Acceptance Criteria

- [ ] RT-018 以合法 github-pr diff evidence 驗證 provider 第二頁未宣告檔案，並由 `guard_status_validator.py` 以 github-pr scope check 失敗。
- [ ] root / `template/` 的 runbook 與 runner case inventory 對齊，不再保留 RT-018 的舊敘述漂移。
- [ ] `python artifacts/scripts/run_red_team_suite.py --phase all --output artifacts/red_team/latest_report.md` 退出碼 0，且報告反映完整案例集。
- [ ] `python artifacts/scripts/aggregate_red_team_scorecard.py --report artifacts/red_team/latest_report.md --output docs/red_team_scorecard.generated.md` 產出最新 scorecard，並同步 `template/` copy。
- [ ] `python artifacts/scripts/guard_contract_validator.py --root .` 與 `python artifacts/scripts/guard_status_validator.py --task-id TASK-981` 皆退出碼 0。

## Dependencies

- Python 3
- 既有 `TASK-900` sample artifacts 與 `guard_status_validator.py` 的 github-pr replay 支援

## Out of Scope

- 新增 agent dispatch / publish automation / size ceiling 類型的新紅隊案例
- 修改 `guard_status_validator.py` 的 github-pr 安全策略
- 重新設計 scorecard 機制

## Current Status Summary

Planned。需要先建立 task/plan/status，再修正 RT-018、對齊 runbook，最後重跑 suite 並刷新 generated 報告。
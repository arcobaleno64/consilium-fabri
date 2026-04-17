# Code Result: TASK-981

## Metadata
- Task ID: TASK-981
- Artifact Type: code
- Owner: Claude Code
- Status: ready
- Last Updated: 2026-04-17T21:32:38+08:00

## Files Changed

- `artifacts/tasks/TASK-981.task.md`
- `artifacts/plans/TASK-981.plan.md`
- `artifacts/code/TASK-981.code.md`
- `artifacts/verify/TASK-981.verify.md`
- `artifacts/status/TASK-981.status.json`
- `artifacts/scripts/run_red_team_suite.py`
- `template/artifacts/scripts/run_red_team_suite.py`
- `artifacts/scripts/aggregate_red_team_scorecard.py`
- `template/artifacts/scripts/aggregate_red_team_scorecard.py`
- `docs/red_team_runbook.md`
- `template/docs/red_team_runbook.md`
- `artifacts/red_team/latest_report.md`
- `template/artifacts/red_team/latest_report.md`
- `docs/red_team_scorecard.generated.md`
- `template/docs/red_team_scorecard.generated.md`

## Summary Of Changes

- 修正 RT-018，使其使用合法 github-pr diff evidence，並以 page 1 滿 100 筆、page 2 額外 rogue file 的 provider 回應，實際驗證 second-page scope drift。
- 對齊 root / `template/` 的 `docs/red_team_runbook.md`，移除不存在的邊界案例列舉、補上已實作的 RT-021/022/023，並修正未來案例編號範例。
- 更新 `aggregate_red_team_scorecard.py` root / `template/` copy，讓 scorecard parser 相容新版 report 表格欄位。
- 重新產生 `artifacts/red_team/latest_report.md` 與 `docs/red_team_scorecard.generated.md`，並同步到 `template/` 對應檔案。

## Mapping To Plan

- plan_item: 1.1, status: done, evidence: "RT-018 now uses PR#971 plus a paginated provider response and fails on github-pr scope drift instead of invalid PR number."
- plan_item: 2.1, status: done, evidence: "Runbook case matrix now matches the runner inventory, including RT-021/022/023 and updated future example numbering."
- plan_item: 3.1, status: done, evidence: "Full suite report and generated scorecard were regenerated and copied to template output paths."
- plan_item: 4.1, status: done, evidence: "TASK-981 code/verify/status artifacts were added and validated with contract/status guards."

## Tests Added Or Updated

- 更新內建紅隊案例 RT-018，使其真正覆蓋 github-pr provider 第二頁 drift。
- 更新 scorecard aggregation parser，讓它可解析新版 `Expected Exit / Actual Exit` report 格式。

## Known Risks

- 這次只修正 RT-018 與紅隊輸出鏈漂移；agent dispatch、publish automation、artifact size ceiling 等其他 threat-model 開放風險仍未新增對應 drills。
- `latest_report.md` 與 `red_team_scorecard.generated.md` 仍屬 generated artifacts，之後若 runner 或欄位格式再變動，需要再次重跑刷新。

## Blockers

None
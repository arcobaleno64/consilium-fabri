# Research: TASK-999

## Metadata
- Task ID: TASK-999
- Artifact Type: research
- Owner: Claude
- Status: ready
- Last Updated: 2026-04-16T00:00:00+08:00

## Research Questions

1. S2 KPI 基線數據為何，以便計算 S6 delta？
2. docs/orchestration.md 現有 §12 結尾位置為何，以便正確插入 §13？
3. docs/red_team_runbook.md 現有末節為何，以便正確追加 §7？
4. TASK-999.decision.md 需符合哪個 schema，Status 為何值？

## Confirmed Facts

- S2 基線：`false_positive_rate_pct=0.0`、`avg_validation_ms=338.576`，coverage_tasks: TASK-900/950/951/902（[artifacts/metrics/kpi_sprint2.json](https://github.com/arcobaleno64/consilium-fabri/blob/master/artifacts/metrics/kpi_sprint2.json)）。
- docs/orchestration.md 末節為 §12 Decision Waiver，結尾行為有效 waiver 的 `[WAIVER ACTIVE gate=N]` 說明（[docs/orchestration.md](https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/orchestration.md)）。
- docs/red_team_runbook.md 末節為 §6 清理原則，最末行為「完整建立 task / status / verify / decision / improvement 鏈」（[docs/red_team_runbook.md](https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/red_team_runbook.md)）。
- artifact_schema.md §5.7 規定 decision artifact 的 Status 合法值為 `done`，必填區段包含 `## Issue`、`## Options Considered`、`## Chosen Option`、`## Reasoning`、`## Implications`、`## Follow Up`（[docs/artifact_schema.md](https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/artifact_schema.md)）。

## Relevant References

- `artifacts/metrics/kpi_sprint2.json`
- `docs/orchestration.md` §12
- `docs/red_team_runbook.md` §6
- `docs/artifact_schema.md` §5.7

## Sources

[1] Arcobaleno. "artifacts/metrics/kpi_sprint2.json — S2 KPI baseline." https://github.com/arcobaleno64/consilium-fabri/blob/master/artifacts/metrics/kpi_sprint2.json (2026-04-16 retrieved)
[2] Arcobaleno. "docs/orchestration.md §12 Decision Waiver." https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/orchestration.md (2026-04-16 retrieved)
[3] Arcobaleno. "docs/red_team_runbook.md §6 清理原則." https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/red_team_runbook.md (2026-04-16 retrieved)
[4] Arcobaleno. "docs/artifact_schema.md §5.7 Decision Artifact Schema." https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/artifact_schema.md (2026-04-16 retrieved)

## Uncertain Items

None

## Constraints For Implementation

- §13 插入點：必須接在 §12 最後一行之後，不得修改 §1–§12。
- §7 插入點：必須接在 §6 清理原則最後一行之後。
- kpi_sprint6.json avg_validation_ms 計算方式：四個 canonical tasks 各取 3 次中位數後再取算術平均。
- decision artifact Status 只能填 `done`，不可用其他值。

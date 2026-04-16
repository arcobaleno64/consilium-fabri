# Task: TASK-999

## Metadata
- Task ID: TASK-999
- Artifact Type: task
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-16T00:00:00+08:00

## Objective

封版 S6 sprint，產出下季（Q3 2026）路線圖決策 artifact，包含 90 天 KPI 對比、Cross-Repository 跨倉協作規範（docs/orchestration.md §13）、Red Team 擴展指南（docs/red_team_runbook.md §7），以及對應的 decision artifact（TASK-999.decision.md）。

## Background

S6 sprint 完成後，guard 穩定性已通過 90 天驗證（false_positive_rate_pct=0.0，avg_validation_ms=290.754）。需以實測數據為依據，定義下季投資優先順序，並補齊跨倉協作與 red team 擴展的文件缺口。

## Inputs

- `artifacts/status/kpi_sprint2.json`（S2 基線數據）
- `docs/orchestration.md`（現有 §1–§12）
- `docs/red_team_runbook.md`（現有 §1–§6）
- `docs/artifact_schema.md §5.7`（decision artifact schema）

## Constraints

- 不得修改 docs/orchestration.md §1–§12 現有內容。
- §13 不得包含任何真實 repo URL 或 token。
- kpi_sprint6.json 不得偽造測量數據；若無法執行測量，在 methodology 欄位標記 "not measured, estimated"。
- template sync 為強制義務：docs/orchestration.md → template/docs/orchestration.md，docs/red_team_runbook.md → template/docs/red_team_runbook.md。
- kpi_sprint6.json 與 TASK-999.decision.md 不加入 template/。

## Acceptance Criteria

- guard_contract_validator.py --root . 退出碼 0。
- run_red_team_suite.py --static 退出碼 0，RT-010/011/012 仍 PASS。
- prompt_regression_validator.py 退出碼 0。
- TASK-900/950/951/902 四個 guard_status_validator 均退出碼 0。
- kpi_sprint6.json 存在且 false_positive_rate_pct ≤ kpi_sprint2 基線（0.0）。
- artifacts/decisions/TASK-999.decision.md 存在且 guard_status_validator 退出碼 0。

## Dependencies

- kpi_sprint2.json 已存在（基線來源）。
- guard_status_validator.py、guard_contract_validator.py、run_red_team_suite.py 可執行。

## Out of Scope

- 不修改 README*、OBSIDIAN.md、template/OBSIDIAN.md（本次不涉及 workflow phase / gate / file structure / agent role 變更）。
- 不新增 template 版本的 KPI 或 decision artifact。
- 不對 guard scripts 進行邏輯修改。

## Current Status Summary

Planned。task/research/plan/decision/status artifacts 齊備，待 guard_status_validator 驗收通過後進入 done。

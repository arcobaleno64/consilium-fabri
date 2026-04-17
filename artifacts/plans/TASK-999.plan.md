# Plan: TASK-999

## Metadata
- Task ID: TASK-999
- Artifact Type: plan
- Owner: Claude
- Status: ready
- Last Updated: 2026-04-16T00:00:00+08:00

## Scope

1. 新增 docs/orchestration.md §13 Cross-Repository Collaboration（13.1–13.4）。
2. 新增 docs/red_team_runbook.md §7 Extension Guide（7.1–7.3）。
3. 建立 artifacts/status/kpi_sprint6.json（S6 KPI 實測對比）。
4. 建立 artifacts/decisions/TASK-999.decision.md（下季路線圖決策）。
5. 建立 artifacts/status/TASK-999.status.json。
6. 同步 docs/orchestration.md → template/docs/orchestration.md。
7. 同步 docs/red_team_runbook.md → template/docs/red_team_runbook.md。

## Files Likely Affected

- docs/orchestration.md
- template/docs/orchestration.md
- docs/red_team_runbook.md
- template/docs/red_team_runbook.md
- artifacts/status/kpi_sprint6.json
- artifacts/decisions/TASK-999.decision.md
- artifacts/status/TASK-999.status.json
- artifacts/tasks/TASK-999.task.md
- artifacts/plans/TASK-999.plan.md
- artifacts/research/TASK-999.research.md

## Proposed Changes

- §13 新增四個小節：remote 命名慣例、upstream pinning 流程、衝突處理策略表格、PR 策略規則。
- §7 新增三個小節：Severity × Coverage 矩陣（12 格）、命名規則、三個範例分類（RT-013/014/015）。
- kpi_sprint6.json 記錄 S6 vs S2 對比數據，方法論說明採中位數計算。
- TASK-999.decision.md 採 roadmap 決策類型，記錄下季三項優先事項及 KPI 依據。

## Risks

- R1: Risk: template 同步遺漏。Trigger: 只改 root docs/ 而忘記同步 template/。Detection: guard_contract_validator.py 漂移偵測。Mitigation: 每次改 doc 後立即同步 template，並以 guard_contract_validator.py 驗證。Severity: non-blocking（guard 會擋住）。
- R2: Risk: kpi 數據方法論不清楚。Trigger: avg_validation_ms 計算方式未說明導致無法重跑。Detection: 人工 review methodology 欄位。Mitigation: 在 methodology 欄位明確記錄每個 task 的中位數與計算公式。Severity: non-blocking。

## Validation Strategy

執行以下命令全數 exit code 0：
- `python artifacts/scripts/guard_contract_validator.py --root .`
- `python artifacts/scripts/run_red_team_suite.py --static`
- `python artifacts/scripts/prompt_regression_validator.py --root .`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-900`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-950`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-951`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-902`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-999`

## Out of Scope

- 不修改 README*、OBSIDIAN.md（無 workflow phase/gate/agent role 變更）。
- 不修改 guard scripts 邏輯。
- 不新增 template 版本的 KPI 或 decision artifact。

## Ready For Coding
yes

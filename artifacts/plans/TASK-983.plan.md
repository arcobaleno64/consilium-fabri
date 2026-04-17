# Plan: TASK-983

## Metadata
- Task ID: TASK-983
- Artifact Type: plan
- Owner: Claude
- Status: ready
- Last Updated: 2026-04-17T23:45:00+08:00

## Scope

這是一輪聚焦 FIND-02 的 lightweight 短衝，只做 artifact size ceiling 與 replay byte cap guard，外加對應 coverage。

1. 在 `guard_status_validator.py` 為 text / JSON artifact 讀取加入明確 byte ceiling，讓超限 artifact 在解析前 fail。
2. 為 `commit-range` archive fallback 與 `github-pr` provider response 加上 replay byte cap，避免 oversized diff evidence 進入高成本解析。
3. 更新 `test_guard_units.py` root / `template/` copy，覆蓋 oversized artifact、oversized archive 與 oversized provider response。
4. 在 `run_red_team_suite.py` 新增對應靜態案例，並同步更新 root / `template/` 的 `docs/red_team_runbook.md`、README 與 generated outputs。
5. 完成 TASK-983 的 code / verify / status 收尾 artifacts。

## Files Likely Affected

- `artifacts/tasks/TASK-983.task.md`
- `artifacts/plans/TASK-983.plan.md`
- `artifacts/code/TASK-983.code.md`
- `artifacts/verify/TASK-983.verify.md`
- `artifacts/status/TASK-983.status.json`
- `artifacts/scripts/guard_status_validator.py`
- `template/artifacts/scripts/guard_status_validator.py`
- `artifacts/scripts/test_guard_units.py`
- `template/artifacts/scripts/test_guard_units.py`
- `artifacts/scripts/run_red_team_suite.py`
- `template/artifacts/scripts/run_red_team_suite.py`
- `docs/red_team_runbook.md`
- `template/docs/red_team_runbook.md`
- `README.md`
- `README.zh-TW.md`
- `template/README.md`
- `template/README.zh-TW.md`
- `artifacts/red_team/latest_report.md`
- `template/artifacts/red_team/latest_report.md`
- `docs/red_team_scorecard.generated.md`
- `template/docs/red_team_scorecard.generated.md`

## Proposed Changes

- 新增 artifact byte ceiling helper，讓 `load_text(...)`、`load_json(...)` 與 override log 載入在超過限制時直接 fail，並回報清楚的 size-ceiling 錯誤。
- 在 archive fallback 與 GitHub PR provider response 讀取點加上 replay byte cap，先擋 oversized archive / response，再進行 UTF-8、JSON 或 snapshot 解析。
- 補齊單元測試：覆蓋 oversized text artifact、oversized JSON artifact、oversized archive fallback 與 oversized provider response。
- 在紅隊 runner 新增三個靜態案例：一個驗證 oversized artifact 被拒絕，一個驗證 oversized archive fallback 被拒絕，一個驗證 oversized provider response 被拒絕。
- 更新 runbook 與 README，說明 status guard 現在也會對 artifact 與 replay input 套用 size ceilings。

## Risks

- R1
  - Risk: ceiling 設得過低，導致目前 repo 合法 task artifacts 或既有紅隊 fixture 被誤判為 oversized。
  - Trigger: 現有 TASK-950/951/982 或一般 task artifacts 在不擴張內容的情況下被新的 size cap 擋下。
  - Detection: `pytest` 或 `run_red_team_suite.py --phase all` 出現大量既有案例回歸。
  - Mitigation: 以目前 repo 實際 artifact 體量為基準，選擇保守但明確的 ceiling，並用全量 suite 回歸驗證。
  - Severity: blocking
- R2
  - Risk: 只在 parse 完之後才檢查大小，實際上沒有真正降低 resource-consumption 風險。
  - Trigger: oversized provider response 仍先完整 decode/parse JSON，或 oversized archive 仍先完整讀入解析。
  - Detection: code review 可見 size 檢查放在 `json.loads(...)`、`decode(...)` 或 line-by-line parsing 之後。
  - Mitigation: 在 `stat()`、`read(limit + 1)` 或等價早期邊界上先做 cap 檢查，再進入解析。
  - Severity: blocking
- R3
  - Risk: 新增 red-team case 後，root / `template/` runbook、README 或 generated outputs 未同步，導致 contract drift。
  - Trigger: 只更新 runner，漏掉文件、template 或 checked-in report / scorecard。
  - Detection: `guard_contract_validator.py --root .` 或 reviewer 比對發現 drift。
  - Mitigation: 同批同步 root / `template/` / generated outputs，並重跑 contract guard 與 red-team aggregation。
  - Severity: blocking

## Validation Strategy

- `python -m pytest artifacts/scripts/test_guard_units.py -v`
- `python artifacts/scripts/run_red_team_suite.py --phase static`
- `python artifacts/scripts/run_red_team_suite.py --phase all --output artifacts/red_team/latest_report.md`
- `python artifacts/scripts/aggregate_red_team_scorecard.py --report artifacts/red_team/latest_report.md --output docs/red_team_scorecard.generated.md`
- `python artifacts/scripts/validate_scorecard_deltas.py --scorecard docs/red_team_scorecard.generated.md`
- `python artifacts/scripts/guard_contract_validator.py --root .`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-983`

## Out of Scope

- Publish automation remote / credential boundary
- Override / waiver governance hardening
- Agent dispatch prompt/context reduction

## Ready For Coding
yes
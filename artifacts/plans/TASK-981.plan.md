# Plan: TASK-981

## Metadata
- Task ID: TASK-981
- Artifact Type: plan
- Owner: Claude
- Status: ready
- Last Updated: 2026-04-17T21:34:30+08:00
- PDCA Stage: P

## Scope

這是一個 lightweight 修補任務，目標是讓 red-team suite、runbook 與 checked-in generated artifacts 重新一致。

1. 修正 RT-018，使其測試合法 github-pr diff evidence 下的第二頁 provider file drift，而不是非法 `PR Number`。
2. 對齊 root / `template/` 的 `docs/red_team_runbook.md` 案例矩陣與實際 runner inventory。
3. 重跑 red-team suite，刷新 root / `template/` 的 `latest_report.md` 與 `red_team_scorecard.generated.md`。
4. 產出 TASK-981 的 code / verify / status 收尾 artifacts。

## Files Likely Affected

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

## Proposed Changes

- 讓 RT-018 建立合法 `Repository` / `PR Number` / `Changed Files Snapshot` / `Snapshot SHA256`，並用 page 1 滿 100 筆、page 2 多 1 筆的 provider 回應觸發 github-pr scope drift。
- 更新 runbook 的 static case matrix，讓 RT-018 敘述與 runner 一致，並補上目前已存在的 RT-021/RT-022/RT-023。
- 更新 scorecard aggregation parser，讓它同時支援舊版單一 Exit 欄位與新版 `Expected Exit / Actual Exit` report 格式。
- 以實際 runner 輸出覆寫 `artifacts/red_team/latest_report.md`，再用 aggregation script 重新產生 scorecard，最後同步 `template/` 對應檔案。

## Risks

- R1
  - Risk: RT-018 provider 分頁條件設錯，導致 runner 仍只讀到第一頁，案例變成假通過或測不到第二頁 drift。
  - Trigger: page 1 回應筆數少於 100，或 snapshot/provider file 集合不一致。
  - Detection: `run_red_team_suite.py --phase static` 中 RT-018 不再命中 `github-pr scope check`。
  - Mitigation: 讓 page 1 恰好 100 筆，snapshot 與 provider 回應一致，只在 plan/code 宣告上漏掉 page 2 rogue file。
  - Severity: blocking
- R2
  - Risk: runbook 只修 RT-018，卻仍與實際 case inventory 不一致。
  - Trigger: 遺漏 RT-021/022/023 或保留不存在的案例說明。
  - Detection: 人工比對 `STATIC_CASES` 與 runbook matrix 時仍出現缺漏。
  - Mitigation: 直接以 `STATIC_CASES` 為準更新 runbook matrix，並同步 template。
  - Severity: blocking
- R3
  - Risk: latest_report 與 generated scorecard 只更新 root，template copy 或 parser 相容性遺漏，導致下一次 contract / aggregation 再度失敗。
  - Trigger: `aggregate_red_team_scorecard.py` 仍只支援舊欄位格式，或同步時漏掉 `template/` 對應輸出。
  - Detection: aggregation script 回報 `no report rows found`，或 contract/reviewer 發現 root/template generated outputs 不一致。
  - Mitigation: 讓 parser 同時支援新舊 report schema，並把 root 產出的 latest_report / scorecard 明確複製到 template。
  - Severity: non-blocking

## Validation Strategy

- `python artifacts/scripts/run_red_team_suite.py --phase static`
- `python artifacts/scripts/run_red_team_suite.py --phase all --output artifacts/red_team/latest_report.md`
- `python artifacts/scripts/aggregate_red_team_scorecard.py --report artifacts/red_team/latest_report.md --output docs/red_team_scorecard.generated.md`
- `python artifacts/scripts/validate_scorecard_deltas.py --scorecard docs/red_team_scorecard.generated.md`
- `python artifacts/scripts/guard_contract_validator.py --root .`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-981`

## Out of Scope

- 新增其他尚未實作的 threat-model drills
- 修改紅隊 suite 的評分公式

## Ready For Coding
yes
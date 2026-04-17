# Plan: TASK-982

## Metadata
- Task ID: TASK-982
- Artifact Type: plan
- Owner: Claude
- Status: ready
- Last Updated: 2026-04-17T23:38:00+08:00

## Scope

這是一輪聚焦 FIND-04 的 lightweight 短衝，只做 GitHub PR replay API host allowlist guard 與對應 coverage。

1. 在 `guard_status_validator.py` 為 `github-pr` evidence 的 API Base URL 補上 allowlist 機制，讓預設只接受 `https://api.github.com`，並允許用顯式環境變數放行受信任的 GitHub Enterprise API host。
2. 更新 `test_guard_units.py` root / `template/` copy，覆蓋 default host、拒絕未 allowlist host、接受 allowlisted host，以及 `collect_github_pr_files(...)` 的錯誤訊息。
3. 在 `run_red_team_suite.py` 新增一正一反的靜態案例，並更新 root / `template/` 的 `docs/red_team_runbook.md` 與 README 說明。
4. 重跑紅隊與聚合輸出，完成 TASK-982 的 code / verify / status 收尾 artifacts。

## Files Likely Affected

- `artifacts/tasks/TASK-982.task.md`
- `artifacts/plans/TASK-982.plan.md`
- `artifacts/code/TASK-982.code.md`
- `artifacts/verify/TASK-982.verify.md`
- `artifacts/status/TASK-982.status.json`
- `artifacts/scripts/guard_status_validator.py`
- `template/artifacts/scripts/guard_status_validator.py`
- `artifacts/scripts/test_guard_units.py`
- `template/artifacts/scripts/test_guard_units.py`
- `artifacts/scripts/run_red_team_suite.py`
- `template/artifacts/scripts/run_red_team_suite.py`
- `artifacts/scripts/aggregate_red_team_scorecard.py`
- `template/artifacts/scripts/aggregate_red_team_scorecard.py`
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

- 新增 API host allowlist helper，解析顯式環境變數中的允許 host 清單，並在 `normalize_api_base_url(...)` 只接受 `api.github.com` 或 allowlisted host。
- 將現有接受任意 absolute `http(s)` URL 的 unit tests 改為拒絕未 allowlist host，並新增 allowlist 通過案例與 provider fetch 拒絕案例。
- 在紅隊 runner 新增兩個案例：一個驗證自訂 host 未 allowlist 時被 guard 擋下；另一個驗證 allowlisted enterprise host 可成功完成 provider replay。
- 更新 runbook 與 README，明確說明 `github-pr` evidence 的 API Base URL 預設限制，以及如何以 allowlist 放行 trusted GitHub Enterprise host。
- 保持 scorecard aggregation 對新舊 report schema 的相容性，避免在刷新紅隊輸出時被 `Expected Exit / Actual Exit` 欄位格式差異阻斷。

## Risks

- R1
  - Risk: allowlist 規則過嚴，誤傷既有 `https://api.github.com` 正常路徑或 trailing slash 變體。
  - Trigger: default GitHub.com replay 在 unit tests 或 red-team 既有 RT-018 中失敗。
  - Detection: `normalize_api_base_url("")` 或 `normalize_api_base_url("https://api.github.com/")` 測試失敗；RT-018 不再通過既有 provider fetch 路徑。
  - Mitigation: 保留 `https://api.github.com` 為內建 allowed host，並先在 unit tests 鎖住 default / trailing slash 行為。
  - Severity: blocking
- R2
  - Risk: allowlist 解析過寬，導致惡意 URL 只要字串包含 allowlisted host 即被誤放行。
  - Trigger: 僅以 substring 判斷 host，而非用 URL parse 後的 `netloc` 比對。
  - Detection: 測試可用 `https://api.github.com.attacker.invalid` 之類 host 混淆通過。
  - Mitigation: 只比對 parse 後的實際 hostname / netloc，拒絕 substring-based allow。
  - Severity: blocking
- R3
  - Risk: 新增紅隊案例後只更新 root，漏掉 `template/`、README 或 generated outputs，導致 contract drift。
  - Trigger: contract guard 或 reviewer 發現 runbook / README / template 不一致。
  - Detection: `guard_contract_validator.py --root .` 失敗。
  - Mitigation: 同批同步 root / `template/` / README，並重跑 contract guard 與紅隊聚合輸出。
  - Severity: blocking

## Validation Strategy

- `python -m pytest artifacts/scripts/test_guard_units.py -v`
- `python artifacts/scripts/run_red_team_suite.py --phase static`
- `python artifacts/scripts/run_red_team_suite.py --phase all --output artifacts/red_team/latest_report.md`
- `python artifacts/scripts/aggregate_red_team_scorecard.py --report artifacts/red_team/latest_report.md --output docs/red_team_scorecard.generated.md`
- `python artifacts/scripts/validate_scorecard_deltas.py --scorecard docs/red_team_scorecard.generated.md`
- `python artifacts/scripts/guard_contract_validator.py --root .`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-982`

## Out of Scope

- Artifact size ceiling 與 replay byte cap
- Publish automation remote / credential boundary
- Agent dispatch context minimization

## Ready For Coding
yes
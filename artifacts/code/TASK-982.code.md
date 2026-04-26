# Code Result: TASK-982

## Metadata
- Task ID: TASK-982
- Artifact Type: code
- Owner: Claude Code
- Status: ready
- Last Updated: 2026-04-17T23:38:00+08:00
- PDCA Stage: D

## Files Changed

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

## Summary Of Changes

- 在 root / `template/` 的 `guard_status_validator.py` 新增 GitHub API host allowlist，讓 `github-pr` replay 預設只接受 `https://api.github.com`，自訂 GitHub Enterprise host 則必須透過 `CONSILIUM_ALLOWED_GITHUB_API_HOSTS` 顯式放行。
- 更新 root / `template/` 的 `test_guard_units.py`，將原本接受任意 custom API base URL 的測試改為 fail-closed，並補上 allowlisted host 成功與 `collect_github_pr_files(...)` 在拒絕 host 時不發出遠端請求的 coverage。
- 擴充 root / `template/` 的 `run_red_team_suite.py`：RT-018 改為真正驗證 github-pr provider 第二頁 drift，新增 RT-024 驗證未 allowlist host 被拒絕，新增 RT-025 驗證顯式 allowlist host 可成功完成 replay；同時加入 `temporary_env(...)` 讓 localhost provider drill 可在案例內局部放行。
- 更新 root / `template/` 的 runbook 與 README，補上 `github-pr` replay 的 host 邊界說明；重新產生 `latest_report.md` 與 `red_team_scorecard.generated.md`，並保留 `aggregate_red_team_scorecard.py` 對新舊 report schema 的相容性，讓 47-case 報表刷新流程維持可重放。

## Mapping To Plan

- plan_item: 1.1, status: done, evidence: "Added hostname allowlist enforcement in `normalize_api_base_url(...)`, keeping `api.github.com` as the default and requiring `CONSILIUM_ALLOWED_GITHUB_API_HOSTS` for trusted custom hosts."
- plan_item: 2.1, status: done, evidence: "Updated root/template guard unit tests to reject non-allowlisted hosts, accept allowlisted hosts, and block provider fetches before any network call on rejected hosts."
- plan_item: 3.1, status: done, evidence: "Extended red-team coverage with RT-024 and RT-025 while repairing RT-018 to validate second-page github-pr scope drift under an explicit localhost allowlist."
- plan_item: 4.1, status: done, evidence: "Synced root/template runbook and README, kept scorecard aggregation compatible with the current report schema, regenerated report/scorecard outputs, and added TASK-982 closure artifacts."

## Tests Added Or Updated

- 更新 `artifacts/scripts/test_guard_units.py` 與 `template/artifacts/scripts/test_guard_units.py`，補齊 allowlist default / reject / allow 路徑。
- 更新 `artifacts/scripts/run_red_team_suite.py` 與 `template/artifacts/scripts/run_red_team_suite.py` 的 RT-018、RT-024、RT-025，讓 provider-backed replay 邊界有一正一反 coverage。
- 保持 `artifacts/scripts/aggregate_red_team_scorecard.py` 與 template copy 對舊版 `Exit Code` 與新版 `Expected Exit / Actual Exit` report 表格都可解析，避免刷新報表時再出現 schema drift。

## Known Risks

- 這次短衝只處理 FIND-04 的 host allowlist 邊界；artifact size ceiling、override separation of duties、publish boundary 與 agent dispatch hardening 仍未在本 task 內落地。
- 自訂 enterprise host 採 fail-closed 設計，未設定 `CONSILIUM_ALLOWED_GITHUB_API_HOSTS` 的環境會直接拒絕 replay；這是刻意收斂 trust boundary，而不是相容性回退。


## TAO Trace

Reconstructed from artifact history. This task predates the TAO schema (introduced in TASK-1000 Phase 2).

### Step 1
- Thought Log: (Reconstructed) Reviewed plan Proposed Changes and executed accordingly.
- Action Step: Implemented changes per plan scope.
- Observation: Completed (inferred from verify artifact AC checklist).
- Next-Step Decision: continue

## Blockers

None
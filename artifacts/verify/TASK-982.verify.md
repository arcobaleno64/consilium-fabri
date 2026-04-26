# Verification: TASK-982

## Metadata
- Task ID: TASK-982
- Artifact Type: verify
- Owner: Claude Code
- Status: pass
- Last Updated: 2026-04-17T23:39:00+08:00
- PDCA Stage: C

## Verification Summary
Migrated from legacy verify artifact.

## Acceptance Criteria Checklist
- **criterion**: `normalize_api_base_url(...)` 預設只接受 GitHub.com 與 allowlisted 自訂 host
- **method**: Artifact and command evidence review
- **evidence**: root / `template/` 的 `guard_status_validator.py` 新增 host allowlist helper；空值仍標準化為 `https://api.github.com`，未 allowlist 的自訂 host 會回傳包含 `CONSILIUM_ALLOWED_GITHUB_API_HOSTS` 指引的明確錯誤訊息。
- **result**: verified

- **criterion**: guard unit tests 覆蓋 default / reject / allow 與 provider fetch 拒絕路徑
- **method**: Artifact and command evidence review
- **evidence**: `python -m pytest artifacts/scripts/test_guard_units.py -v` 結果為 `910 passed in 7.39s`。更新後測試涵蓋 default GitHub.com、未 allowlist custom host、allowlisted custom host，以及 `collect_github_pr_files(...)` 在拒絕 host 時不呼叫 `urlopen`。
- **result**: verified

- **criterion**: red-team suite 具備 allowlist 正反案例並更新 runbook
- **method**: Artifact and command evidence review
- **evidence**: static suite 已納入 RT-024 與 RT-025，RT-018 也改為真正驗證 provider 第二頁 drift。`python artifacts/scripts/run_red_team_suite.py --phase static` 與 `python artifacts/scripts/run_red_team_suite.py --phase all --output artifacts/red_team/latest_report.md` 皆退出碼 0；最新報告共 47 個案例、47 個通過、0 失敗。runbook root / `template/` 已同步列出 RT-024 / RT-025。
- **result**: verified

- **criterion**: root / `template/` 的 guard、tests、runbook 與 README 同步完成
- **method**: Artifact and command evidence review
- **evidence**: `guard_status_validator.py`、`test_guard_units.py`、`run_red_team_suite.py`、`aggregate_red_team_scorecard.py`、`docs/red_team_runbook.md`、`README.md`、`README.zh-TW.md` 及對應 template copy 已同步更新。`python artifacts/scripts/guard_contract_validator.py --root .` 回報 `[OK] Contract validation passed`。
- **result**: verified

- **criterion**: 驗證證據包含 unit tests、red-team、contract guard 與 TASK-982 status guard
- **method**: Artifact and command evidence review
- **evidence**: 驗證鏈已完成 `pytest`、static red-team、full red-team report、scorecard aggregation、scorecard delta validation、contract guard，並在補齊 TASK-982 code / verify / status artifacts 後通過 `python artifacts/scripts/guard_status_validator.py --task-id TASK-982`。
- **result**: verified

## Overall Maturity
poc

## Deferred Items
- FIND-02 的 artifact size ceiling / replay byte cap 尚未處理。
- FIND-05 的 override separation of duties 與 FIND-08 的 publish boundary hardening 尚未處理。

## Evidence
- `artifacts/red_team/latest_report.md` 與 `docs/red_team_scorecard.generated.md` 已刷新為 47-case 全綠版本，並同步到 `template/` 對應檔案。
- RT-024 直接驗證未 allowlist host 被 fail-closed；RT-025 驗證顯式 allowlist host 能通過 provider replay；RT-018 則保持 github-pr 第二頁 drift coverage。
- `aggregate_red_team_scorecard.py` 的相容性修補已保留，避免報表欄位格式變更再次讓刷新流程中斷。

## Evidence Refs
- `artifacts/red_team/latest_report.md`
- `docs/red_team_scorecard.generated.md`

## Decision Refs
None

## Build Guarantee
- `python -m pytest artifacts/scripts/test_guard_units.py -v` → `910 passed in 7.39s`
- `python artifacts/scripts/run_red_team_suite.py --phase static` → 退出碼 0
- `python artifacts/scripts/run_red_team_suite.py --phase all --output artifacts/red_team/latest_report.md` → 退出碼 0
- `python artifacts/scripts/aggregate_red_team_scorecard.py --report artifacts/red_team/latest_report.md --output docs/red_team_scorecard.generated.md` → `[OK] scorecard written`
- `python artifacts/scripts/validate_scorecard_deltas.py --scorecard docs/red_team_scorecard.generated.md` → `[OK] Scorecard delta validation passed`
- `python artifacts/scripts/guard_contract_validator.py --root .` → `[OK] Contract validation passed`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-982` → `[OK] Validation passed`


## TAO Trace

Reconstructed from artifact history. This task predates the TAO schema (introduced in TASK-1000 Phase 2).

### Step 1
- Thought Log: (Reconstructed) Reviewed plan Proposed Changes and executed accordingly.
- Action Step: Implemented changes per plan scope.
- Observation: Completed (inferred from verify artifact AC checklist).
- Next-Step Decision: continue

## Pass Fail Result
pass

## Recommendation
None

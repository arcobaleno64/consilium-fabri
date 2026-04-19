# Plan: TASK-985

## Metadata
- Task ID: TASK-985
- Artifact Type: plan
- Owner: Codex CLI
- Status: ready
- Last Updated: 2026-04-19T23:22:43+08:00

## Scope

1. 建立 external legacy verify corpus fixture taxonomy，至少涵蓋 structured checklist、heading block、checkbox list、unparseable fragment。
2. 新增 shared corpus loader，讓 unit tests 與 red-team suite 使用同一份 fixture manifest。
3. 將 migration regression 改為讀取實體 corpus 並做 golden assertions。
4. 新增 external import 的紅隊 static case，驗證 fail-closed downgrade。
5. 補 root / `template/` 同步、full validation 與 `TASK-985` closure artifacts。

## Files Likely Affected

- artifacts/tasks/TASK-985.task.md
- artifacts/plans/TASK-985.plan.md
- artifacts/code/TASK-985.code.md
- artifacts/verify/TASK-985.verify.md
- artifacts/status/TASK-985.status.json
- artifacts/scripts/legacy_verify_corpus.py
- artifacts/scripts/migrate_artifact_schema.py
- artifacts/scripts/workflow_constants.py
- artifacts/scripts/guard_status_validator.py
- artifacts/scripts/guard_contract_validator.py
- artifacts/scripts/build_decision_registry.py
- artifacts/scripts/drills/prompt_regression_cases.json
- .consilium-source-repo
- AGENTS.md
- BOOTSTRAP_PROMPT.md
- CLAUDE.md
- OBSIDIAN.md
- START_HERE.md
- docs/lightweight_mode_rules.md
- docs/subagent_roles.md
- docs/workflow_state_machine.md
- template/artifacts/scripts/legacy_verify_corpus.py
- template/artifacts/scripts/migrate_artifact_schema.py
- template/artifacts/scripts/workflow_constants.py
- template/artifacts/scripts/guard_status_validator.py
- template/artifacts/scripts/guard_contract_validator.py
- template/artifacts/scripts/build_decision_registry.py
- template/artifacts/scripts/drills/prompt_regression_cases.json
- template/AGENTS.md
- template/BOOTSTRAP_PROMPT.md
- template/CLAUDE.md
- template/OBSIDIAN.md
- template/START_HERE.md
- template/docs/lightweight_mode_rules.md
- template/docs/subagent_roles.md
- template/docs/workflow_state_machine.md
- artifacts/scripts/test_guard_units.py
- template/artifacts/scripts/test_guard_units.py
- artifacts/scripts/run_red_team_suite.py
- template/artifacts/scripts/run_red_team_suite.py
- artifacts/test/legacy_verify_corpus/manifest.json
- artifacts/test/legacy_verify_corpus/structured-checklist-complete.verify.md
- artifacts/test/legacy_verify_corpus/heading-block-partial.verify.md
- artifacts/test/legacy_verify_corpus/checkbox-list-mixed.verify.md
- artifacts/test/legacy_verify_corpus/unparseable-fragment.verify.md
- template/artifacts/test/legacy_verify_corpus/manifest.json
- template/artifacts/test/legacy_verify_corpus/structured-checklist-complete.verify.md
- template/artifacts/test/legacy_verify_corpus/heading-block-partial.verify.md
- template/artifacts/test/legacy_verify_corpus/checkbox-list-mixed.verify.md
- template/artifacts/test/legacy_verify_corpus/unparseable-fragment.verify.md
- artifacts/verify/TASK-900.verify.md
- artifacts/verify/TASK-952.verify.md
- artifacts/verify/TASK-953.verify.md
- artifacts/verify/TASK-954.verify.md
- artifacts/verify/TASK-955.verify.md
- artifacts/verify/TASK-956.verify.md
- artifacts/verify/TASK-957.verify.md
- artifacts/verify/TASK-958.verify.md
- artifacts/verify/TASK-960.verify.md
- artifacts/verify/TASK-961.verify.md
- artifacts/verify/TASK-963.verify.md
- artifacts/verify/TASK-980.verify.md
- artifacts/verify/TASK-982.verify.md
- artifacts/verify/TASK-984.verify.md
- docs/red_team_runbook.md
- template/docs/red_team_runbook.md
- docs/artifact_schema.md
- template/docs/artifact_schema.md
- artifacts/red_team/latest_report.md
- template/artifacts/red_team/latest_report.md
- docs/red_team_scorecard.generated.md
- template/docs/red_team_scorecard.generated.md

## Proposed Changes

- 新增 shared helper 載入 legacy verify corpus manifest 與 fixture 內容，避免 tests / red-team 各自維護平行樣本。
- 建立 four-shape external legacy corpus，並將 migrate regression 改為 golden-style assertions，直接鎖定 `strategy`、`confidence`、`manual_review_required`、`Deferred Items` 與 checklist result。
- 在 red-team suite 新增 external import case，證明 unparseable legacy fragment 進入 `external-legacy` 後只能落成 manual-review / deferred。
- shared workflow validators 補 fail-closed coverage hardening：`workflow_constants.py` 對壞 rule tables 回傳 validation errors 而不是 `KeyError`，`guard_status_validator.py` 補回 `reconcile_status_file(..., apply=...)` 相容入口。
- root / `template/` workflow contract 一併收斂：同步 `guard_contract_validator.py`、`build_decision_registry.py`、prompt regression corpus，以及 7 個入口文件與關聯 docs，避免本地依賴 dirty files 才能通過 CI。
- historical root artifacts 一併 reconciliation：把既有 task / decision / improvement / verify / status 檔補到新 schema 最低要求，消除 source-repo strictness 對 legacy warning 的阻擋。
- 重跑 root / `template/` 全量 guard tests、migration dry-run、contract / context / status validators、static / all red-team，並更新 generated report / scorecard。

## Risks

R1
- Risk: corpus fixture 看似實體化，但實際仍只是把既有 synthetic string 原封不動搬到檔案，沒有增加異質性。
- Trigger: 每個 corpus case 都只覆蓋乾淨、理想化格式。
- Detection: fixtures 幾乎沒有缺欄位、髒格式或 ambiguous evidence；red-team case 也無法命中 fallback。
- Mitigation: 每類至少保留一份帶不完整欄位或非理想格式的樣本，尤其是 heading / checkbox / unparseable 類。
- Severity: blocking

R2
- Risk: 為了讓 corpus case 綠燈而放寬 heuristic，讓非結構化 external legacy verify 重新被升成 `pass`。
- Trigger: golden assertions 不檢查 `deferred` / `MANUAL_CHECK_DEFERRED`，或 red-team case 只驗 happy path。
- Detection: checkbox / heading / unparseable case 的 migrated verify 出現 `## Pass Fail Result` = `pass`。
- Mitigation: 對非結構化 corpus 直接鎖定 `deferred`、`MANUAL_CHECK_DEFERRED`、`manual_review_required=true` 與 `Pass Fail Result = fail`。
- Severity: blocking

R3
- Risk: root / `template/` 的 corpus、shared loader 或 red-team matrix 不同步，之後又回到 contract drift。
- Trigger: 只更新 root fixtures 或 runner，漏掉 `template/` 對應檔案與 generated outputs。
- Detection: `guard_contract_validator.py`、`validate_context_stack.py` 或 template full tests 失敗。
- Mitigation: 同步更新 `template/` fixtures / scripts / runbook / generated outputs，並把 template full suite 納入驗證鏈。
- Severity: blocking

R4
- Risk: 補 coverage 時只顧著讓測試綠燈，卻在 shared guard 路徑留下 `KeyError` / API break，導致 validator 在異常輸入下無法 fail-closed。
- Trigger: `workflow_constants.py` 面對缺 profile / adapter rule / policy key 時直接拋例外，或 `guard_status_validator.py` 移除既有 `reconcile_status_file()` 介面。
- Detection: `pytest` 在 `TestWorkflowConstantsCoverageCatchup` / `TestGuardStatusValidatorCoverageCatchup` 失敗，或 guard script 於壞配置輸入直接 crash。
- Mitigation: 對壞 rule tables 改成回傳 validation errors，補回 `reconcile_status_file(..., apply=...)` 相容 wrapper，並以 targeted/full pytest 鎖住行為。
- Severity: blocking

## Validation Strategy

執行以下命令，預期 exit code 0：

- `python -m pytest artifacts/scripts/test_guard_units.py`
- `python -m pytest template/artifacts/scripts/test_guard_units.py`
- `python artifacts/scripts/migrate_artifact_schema.py`
- `python artifacts/scripts/guard_contract_validator.py`
- `python artifacts/scripts/guard_contract_validator.py --check-readme`
- `python artifacts/scripts/validate_context_stack.py`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-984 --artifacts-root artifacts`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-985 --artifacts-root artifacts`
- `python artifacts/scripts/run_red_team_suite.py --phase static --output artifacts/red_team/latest_report.md`
- `python artifacts/scripts/run_red_team_suite.py --phase all --output artifacts/red_team/latest_report.md`
- `python artifacts/scripts/aggregate_red_team_scorecard.py --report artifacts/red_team/latest_report.md --output docs/red_team_scorecard.generated.md`
- `python artifacts/scripts/validate_scorecard_deltas.py --scorecard docs/red_team_scorecard.generated.md`

## Verification Obligations

- corpus fixtures 必須實際存在於 `artifacts/test/legacy_verify_corpus/` 與 template copy。
- unit tests 必須從 corpus 讀樣本，而不是只保留 inline synthetic strings。
- 非結構化 external legacy case 必須維持 `deferred` / `MANUAL_CHECK_DEFERRED` / `Pass Fail Result = fail`。
- red-team external import case 必須命中 fail-closed 行為，而不是只驗證文字輸出存在。
- generated red-team report / scorecard 必須與新增 case inventory 同步。

## Out of Scope

- 真實第三方 legacy repo 批次 ingest
- 新的 project adapter 或 assurance policy
- 其他與 external legacy verify 無關的 threat-model findings

## Ready For Coding
yes

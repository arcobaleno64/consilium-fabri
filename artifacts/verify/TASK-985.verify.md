# Verification: TASK-985

## Metadata
- Task ID: TASK-985
- Artifact Type: verify
- Owner: Codex CLI
- Status: pass
- Last Updated: 2026-04-19T23:29:25+08:00
- PDCA Stage: C

## Verification Summary
本次驗證把 `TASK-984` 留下的 external legacy corpus 風險正式收斂，並補齊 shared workflow validator coverage gate：root / `template/` 現在有共享 external legacy verify corpus，migration regression 與 red-team 直接共用同一份 fixture；heading block 的誤分類、command-style evidence ref 污染、validator fail-closed / reconcile compatibility 缺口，以及 source/downstream workflow contract、decision registry sync、historical root artifact strictness reconciliation（含 plan verification obligations）都已補上，指定 9 個 repo gates 與 coverage 100% 已重新確認。

## Acceptance Criteria Checklist
- **criterion**: root / `template/` 建立 external legacy verify corpus，至少覆蓋 structured checklist、heading block、checkbox list、unparseable fragment 四類
- **method**: Artifact review
- **evidence**: `artifacts/test/legacy_verify_corpus/` 與 `template/artifacts/test/legacy_verify_corpus/` 現在都包含 4 份 fixture 與 shared `manifest.json`。
- **result**: verified

- **criterion**: unit tests 改為讀取 corpus fixtures，並驗證 strategy / confidence / unresolved fields / deferred behavior
- **method**: Full pytest
- **evidence**: `python -m pytest artifacts/scripts/test_guard_units.py artifacts/scripts/test_security_scans.py --cov --cov-config=.coveragerc --cov-report=term-missing --cov-fail-under=100` 通過 `1112 passed` / `100.00%`；`python -m pytest template/artifacts/scripts/test_guard_units.py` 通過 `992 passed`，且新增 coverage 直接檢查 four-shape corpus、command-style evidence ref filtering、validator fail-closed 與 reconcile dry-run 行為。
- **result**: verified

- **criterion**: heading block 不再被 migration 誤判為 high-confidence structured checklist
- **method**: Corpus regression + migration dry-run
- **evidence**: corpus-driven regression 先捕捉到 `heading-block-partial` 被誤升級，修正 `migrate_artifact_schema.py` 後 targeted 與 full pytest 皆綠，且 `external-legacy` heading block 現在會輸出 `heading-block-heuristic` + manual review。
- **result**: verified

- **criterion**: command-style evidence lines 不會再污染 `Evidence Refs`，root tracked migration baseline 恢復可重跑 no-op
- **method**: Targeted regression + migration apply/dry-run
- **evidence**: 新增 `test_evidence_refs_ignore_command_lines`；執行 `python artifacts/scripts/migrate_artifact_schema.py --apply` 收斂 14 份 historical verify 後，再跑 `python artifacts/scripts/migrate_artifact_schema.py` 回報 `changed_files=0`。
- **result**: verified

- **criterion**: red-team suite 新增 external import fail-closed case，證明未知 legacy fragment 不會被誤升成 authoritative verify
- **method**: Static + all-phase red-team
- **evidence**: `RT-030` 已加入 static matrix，`python artifacts/scripts/run_red_team_suite.py --phase static --output artifacts/red_team/latest_report.md` 與 `--phase all` 均退出碼 `0`；report 中 `RT-030` 顯示 `fail-closed external legacy import confirmed`。
- **result**: verified

- **criterion**: root / `template/` contract、prompt regression、decision registry schema、historical root artifact strictness（含 plan verification obligations）、context stack、既有 TASK-984 baseline 與 generated red-team outputs 沒有退步
- **method**: Contract validators + status validator + scorecard regeneration
- **evidence**: `guard_contract_validator.py --root .`、`prompt_regression_validator.py --root .`、全量 `guard_status_validator.py --task-id TASK-*`、`run_red_team_suite.py --phase static`、`validate_context_stack.py --root .`、`repo_health_dashboard.py --root .`、`repo_security_scan.py --root . secrets/static` 全部 exit code `0`；`guard_contract_validator.py` 與 `build_decision_registry.py` 的新 coverage 分支已被 unit tests 命中，historical task / plan / decision / improvement / verify / status artifacts 也已補到不再觸發 source-repo strictness warning，`template/` 對應 scripts / fixtures / docs / entry docs 已同步，`python -m pytest template/artifacts/scripts/test_guard_units.py` 亦通過 `992 passed`。
- **result**: verified

## Overall Maturity
poc

## Deferred Items
- 尚未匯入真實第三方 external legacy verify artifacts；目前 corpus 已涵蓋四類異質 legacy shape，但仍屬 repo-curated sample set。

## Evidence
- `python -m pytest artifacts/scripts/test_guard_units.py artifacts/scripts/test_security_scans.py --cov --cov-config=.coveragerc --cov-report=term-missing --cov-fail-under=100` → `1112 passed`, `100.00%`
- `python -m pytest template/artifacts/scripts/test_guard_units.py` → `992 passed`
- `python artifacts/scripts/guard_contract_validator.py --root .` → `[OK] Contract validation passed`
- `python artifacts/scripts/prompt_regression_validator.py --root .` → `20/20 cases pass`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-*` over 24 status files → all `[OK] Validation passed`
- `python artifacts/scripts/run_red_team_suite.py --phase static` → exit code `0`
- `python artifacts/scripts/validate_context_stack.py --root .` → `PASSED: all checks OK`
- `python artifacts/scripts/repo_health_dashboard.py --root .` → exit code `0`
- `python artifacts/scripts/repo_security_scan.py --root . secrets` → `[OK] No findings detected`
- `python artifacts/scripts/repo_security_scan.py --root . static` → `[OK] No findings detected`

## Evidence Refs
- `artifacts/scripts/legacy_verify_corpus.py`
- `artifacts/scripts/migrate_artifact_schema.py`
- `artifacts/scripts/workflow_constants.py`
- `artifacts/scripts/guard_status_validator.py`
- `artifacts/scripts/guard_contract_validator.py`
- `artifacts/scripts/build_decision_registry.py`
- `artifacts/scripts/drills/prompt_regression_cases.json`
- `artifacts/scripts/test_guard_units.py`
- `artifacts/scripts/run_red_team_suite.py`
- `artifacts/test/legacy_verify_corpus/manifest.json`
- `.consilium-source-repo`
- `AGENTS.md`
- `BOOTSTRAP_PROMPT.md`
- `CLAUDE.md`
- `OBSIDIAN.md`
- `START_HERE.md`
- `docs/artifact_schema.md`
- `docs/lightweight_mode_rules.md`
- `docs/subagent_roles.md`
- `docs/workflow_state_machine.md`
- `docs/red_team_runbook.md`
- `artifacts/red_team/latest_report.md`
- `docs/red_team_scorecard.generated.md`

## Decision Refs
None

## Build Guarantee
- None (no .csproj modified)
- `python -m pytest artifacts/scripts/test_guard_units.py artifacts/scripts/test_security_scans.py --cov --cov-config=.coveragerc --cov-report=term-missing --cov-fail-under=100` → `1112 passed`, `100.00%`
- `python -m pytest template/artifacts/scripts/test_guard_units.py` → `992 passed`
- `python artifacts/scripts/guard_contract_validator.py --root .` → `[OK] Contract validation passed`
- `python artifacts/scripts/prompt_regression_validator.py --root .` → `20/20 cases pass`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-*` over 24 status files → all `[OK] Validation passed`
- `python artifacts/scripts/run_red_team_suite.py --phase static` → exit code `0`
- `python artifacts/scripts/validate_context_stack.py --root .` → `PASSED: all checks OK`
- `python artifacts/scripts/repo_health_dashboard.py --root .` → exit code `0`
- `python artifacts/scripts/repo_security_scan.py --root . secrets` → `[OK] No findings detected`
- `python artifacts/scripts/repo_security_scan.py --root . static` → `[OK] No findings detected`


## TAO Trace

Reconstructed from artifact history. This task predates the TAO schema (introduced in TASK-1000 Phase 2).

### Step 1
- Thought Log: (Reconstructed) Reviewed plan Proposed Changes and executed accordingly.
- Action Step: Implemented changes per plan scope.
- Observation: Completed (inferred from verify artifact AC checklist).
- Next-Step Decision: continue

## Pass Fail Result
pass

## Remaining Gaps
- 尚未匯入真實第三方 external legacy verify artifacts；目前 corpus 已涵蓋四類異質 legacy shape，但仍屬 repo-curated sample set。

## Recommendation
None

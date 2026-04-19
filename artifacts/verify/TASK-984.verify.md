# Verification: TASK-984

## Metadata
- Task ID: TASK-984
- Artifact Type: verify
- Owner: Codex CLI
- Status: pass
- Last Updated: 2026-04-19T23:04:00+08:00

## Verification Summary
本次驗證聚焦在 external legacy verify import boundary：確認 root tracked default 仍維持 strict no-op，external legacy 非結構化輸入會降成 manual-review / deferred，而不是被直接升成 authoritative `pass`；同時確認 root / `template/` 文件入口已同步。

## Acceptance Criteria Checklist
- **criterion**: `migrate_artifact_schema.py` 提供 explicit `input-mode`，並保留 `root-tracked` default
- **method**: Targeted unit tests + repo root dry-run
- **evidence**: `python -m pytest artifacts/scripts/test_guard_units.py -k "ArtifactSchemaMigration or parse_args_accepts_external_legacy_mode"` 通過；`python artifacts/scripts/migrate_artifact_schema.py` 仍回報 `changed_files=0`。
- **result**: verified

- **criterion**: `external-legacy` 模式會把非結構化 legacy verify 降成 manual-review / deferred，並揭露 strategy / confidence / unresolved fields
- **method**: Targeted unit tests
- **evidence**: `test_external_legacy_checkbox_mode_forces_manual_review` 驗證 external legacy checkbox import 會產出 `deferred`、`MANUAL_CHECK_DEFERRED` 與 unresolved-fields warning。
- **result**: verified

- **criterion**: 已具 structured checklist 的 external legacy verify 可保留 high-confidence path
- **method**: Targeted unit tests
- **evidence**: `test_external_legacy_structured_mode_preserves_high_confidence_items` 驗證 external legacy structured checklist 仍保留 `confidence=high` 與 `Pass Fail Result = pass`。
- **result**: verified

- **criterion**: root / `template/` migration tests 已補上 external legacy regression coverage
- **method**: pytest
- **evidence**: `python -m pytest artifacts/scripts/test_guard_units.py -k "legacy or verify or migrate"` 通過 `53 passed`；`python -m pytest template/artifacts/scripts/test_guard_units.py -k "ArtifactSchemaMigration or parse_args_accepts_external_legacy_mode"` 通過 `2 passed`；全量 `python -m pytest artifacts/scripts/test_guard_units.py` 與 `python -m pytest template/artifacts/scripts/test_guard_units.py` 均通過 `987 passed`，表示 root / template 的 guard unit coverage 沒有退步。
- **result**: verified

- **criterion**: root / `template/` docs 與 README 已同步揭露 external legacy import contract
- **method**: Contract validation + context stack validation
- **evidence**: `python artifacts/scripts/guard_contract_validator.py --check-readme` 與 `python artifacts/scripts/validate_context_stack.py` 均通過。
- **result**: verified

- **criterion**: 紅隊 static / all phase 仍維持全綠，且 `RT-012` 已符合現行 verify contract
- **method**: red-team suite
- **evidence**: `python artifacts/scripts/run_red_team_suite.py --phase static` 與 `python artifacts/scripts/run_red_team_suite.py --phase all` 均退出碼 `0`；`RT-012` 現在會用合法 `verified` result 搭配 `resource-constrained-ui` adapter 驗證缺少 `reviewer` 僅發出 warning。
- **result**: verified

## Overall Maturity
poc

## Deferred Items
- 真實外部 legacy corpus 與更細的欄位推斷矩陣仍未建立；目前 regression 以 synthetic fixtures 為主。

## Evidence
- `python -m pytest artifacts/scripts/test_guard_units.py -k "ArtifactSchemaMigration or parse_args_accepts_external_legacy_mode"` → `5 passed`
- `python -m pytest artifacts/scripts/test_guard_units.py -k "legacy or verify or migrate"` → `53 passed`
- `python -m pytest template/artifacts/scripts/test_guard_units.py -k "ArtifactSchemaMigration or parse_args_accepts_external_legacy_mode"` → `2 passed`
- `python -m pytest artifacts/scripts/test_guard_units.py` → `987 passed`
- `python -m pytest template/artifacts/scripts/test_guard_units.py` → `987 passed`
- `python artifacts/scripts/migrate_artifact_schema.py` → `changed_files=0`
- `python artifacts/scripts/guard_contract_validator.py --check-readme` → `[OK] Contract validation passed`
- `python artifacts/scripts/validate_context_stack.py` → `PASSED: all checks OK`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-983 --artifacts-root artifacts` → `[OK] Validation passed`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-984` → `[OK] Validation passed`
- `python artifacts/scripts/run_red_team_suite.py --phase static` → exit code `0`
- `python artifacts/scripts/run_red_team_suite.py --phase all` → exit code `0`

## Evidence Refs
- `README.md`
- `README.zh-TW.md`
- `artifacts/scripts/migrate_artifact_schema.py`
- `artifacts/scripts/test_guard_units.py`
- `docs/artifact_schema.md`
- `docs/orchestration.md`
- `template/artifacts/scripts/test_guard_units.py`

## Decision Refs
None

## Build Guarantee
- None (no .csproj modified)
- `python -m pytest artifacts/scripts/test_guard_units.py -k "ArtifactSchemaMigration or parse_args_accepts_external_legacy_mode"` → `5 passed`
- `python -m pytest artifacts/scripts/test_guard_units.py -k "legacy or verify or migrate"` → `53 passed`
- `python -m pytest template/artifacts/scripts/test_guard_units.py -k "ArtifactSchemaMigration or parse_args_accepts_external_legacy_mode"` → `2 passed`
- `python -m pytest artifacts/scripts/test_guard_units.py` → `987 passed`
- `python -m pytest template/artifacts/scripts/test_guard_units.py` → `987 passed`
- `python artifacts/scripts/migrate_artifact_schema.py` → `changed_files=0`
- `python artifacts/scripts/guard_contract_validator.py --check-readme` → `[OK] Contract validation passed`
- `python artifacts/scripts/validate_context_stack.py` → `PASSED: all checks OK`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-983 --artifacts-root artifacts` → `[OK] Validation passed`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-984` → `[OK] Validation passed`
- `python artifacts/scripts/run_red_team_suite.py --phase static` → exit code `0`
- `python artifacts/scripts/run_red_team_suite.py --phase all` → exit code `0`

## Pass Fail Result
pass

## Remaining Gaps
- 真實外部 legacy corpus 與更細的欄位推斷矩陣仍未建立；目前 regression 以 synthetic fixtures 為主。

## Recommendation
None

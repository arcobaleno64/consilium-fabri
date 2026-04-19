# Plan: TASK-984

## Metadata
- Task ID: TASK-984
- Artifact Type: plan
- Owner: Codex CLI
- Status: ready
- Last Updated: 2026-04-19T23:04:00+08:00

## Scope

1. 在 `migrate_artifact_schema.py` 增加 explicit input mode，將 root tracked normalization 與 external legacy import 分流。
2. 調整 verify migration：external legacy 非結構化輸入一律降級為 manual-review / deferred，並把 strategy / confidence / unresolved fields 寫進 migration output。
3. 在 root / `template/` 測試補上 external legacy import regression coverage。
4. 更新 root / `template/` 的 `docs/` 與 README，明示 external legacy import contract。
5. 建立 `TASK-984` 的 code / verify / status closure artifacts。

## Files Likely Affected

- artifacts/scripts/migrate_artifact_schema.py
- template/artifacts/scripts/migrate_artifact_schema.py
- artifacts/scripts/test_guard_units.py
- template/artifacts/scripts/test_guard_units.py
- docs/artifact_schema.md
- template/docs/artifact_schema.md
- docs/orchestration.md
- template/docs/orchestration.md
- README.md
- README.zh-TW.md
- template/README.md
- template/README.zh-TW.md
- artifacts/tasks/TASK-984.task.md
- artifacts/plans/TASK-984.plan.md
- artifacts/code/TASK-984.code.md
- artifacts/verify/TASK-984.verify.md
- artifacts/status/TASK-984.status.json

## Proposed Changes

- `migrate_artifact_schema.py` 新增 `--input-mode {root-tracked,external-legacy}`，預設維持 `root-tracked`。
- verify migration 增加 strategy / confidence / unresolved fields assessment，並把 external legacy heuristic mapping 降成 manual-review / deferred。
- root / `template/` tests 新增 external legacy checkbox downgrade 與 parse_args coverage；root tests 也補 structured external import high-confidence path。
- `docs/artifact_schema.md`、`docs/orchestration.md` 與 README root / `template/` 補 external legacy import contract 與指令入口。

## Risks

R1
- Risk: mode split 做得不夠硬，導致 external legacy heuristic 又回流成 root tracked 的預設路徑。
- Trigger: `migrate_artifact_schema.py` 預設不是 `root-tracked`，或 `external-legacy` 行為滲入 root dry-run。
- Detection: `python artifacts/scripts/migrate_artifact_schema.py` 在 repo root 不再是 `changed_files=0`。
- Mitigation: 保持 CLI default = `root-tracked`，並用 regression test 鎖住 root dry-run no-op。
- Severity: blocking

R2
- Risk: external legacy heuristic 仍把 checkbox / heading block 直接升成 `pass`，造成靜默誤映射。
- Trigger: 非結構化 legacy verify 在 import 後仍保留 `verified` / `pass`。
- Detection: targeted pytest 看不到 `deferred` / `MANUAL_CHECK_DEFERRED`，或 migrated verify 缺少 unresolved-fields warning。
- Mitigation: external legacy 非結構化輸入一律 downgrade 為 manual-review / deferred，並把 unresolved fields 寫入 output。
- Severity: blocking

R3
- Risk: root / `template/` 文件與 README 沒同步，導致 contract drift 或使用者只看到舊指令入口。
- Trigger: 只更新 root docs/script，漏掉 `template/` 對應檔案或 README 表格。
- Detection: `python artifacts/scripts/guard_contract_validator.py --check-readme` 或 `python artifacts/scripts/validate_context_stack.py` 失敗。
- Mitigation: 同步更新 `template/` 與 README root / `template/`，並把 contract validator 納入驗證鏈。
- Severity: non-blocking

R4
- Risk: closure artifacts 沒有跟著最後一輪 coverage hardening 補齊 schema-required 區段，讓人工作面上誤以為 TASK-984 已完整 closure。
- Trigger: `TASK-984` plan / verify 沒補足 premortem 最低條數或 verify 缺少 `## Remaining Gaps`。
- Detection: 人工 artifact review 發現 plan 只有 R1-R3，或 verify schema 區段不完整。
- Mitigation: 在最終 commit 前補齊 plan / verify 所需區段，並重跑 `python artifacts/scripts/guard_status_validator.py --task-id TASK-984` 確認 closure artifact 仍合法。
- Severity: non-blocking

## Validation Strategy

執行以下命令，預期 exit code 0：

- `python -m pytest artifacts/scripts/test_guard_units.py -k "ArtifactSchemaMigration or parse_args_accepts_external_legacy_mode"`
- `python -m pytest artifacts/scripts/test_guard_units.py -k "legacy or verify or migrate"`
- `python -m pytest template/artifacts/scripts/test_guard_units.py -k "ArtifactSchemaMigration or parse_args_accepts_external_legacy_mode"`
- `python artifacts/scripts/migrate_artifact_schema.py`
- `python artifacts/scripts/guard_contract_validator.py --check-readme`
- `python artifacts/scripts/validate_context_stack.py`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-983 --artifacts-root artifacts`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-984 --artifacts-root artifacts`

## Verification Obligations

- root tracked default path 必須維持 `changed_files=0` dry-run baseline。
- external legacy checkbox import 必須顯示 `deferred` 與 unresolved-fields warning，不得保留直接 `pass`。
- external legacy structured checklist import 必須保留 high-confidence path。
- root / `template/` docs 與 README 必須同步揭露 external legacy import contract。
- `TASK-984.verify.md` 的 evidence 必須足以支持 mode split、downgrade path 與 contract validator 結果。

## Out of Scope

- 建立真實外部 corpus fixture 目錄與批次匯入 CLI
- 調整其他 guard script 的 legacy compatibility 邏輯
- 整理 `template/artifacts/scripts/test_guard_units.py` 既有全量失敗案例

## Ready For Coding
yes

# Code Result: TASK-984

## Metadata
- Task ID: TASK-984
- Artifact Type: code
- Owner: Codex CLI
- Status: ready
- Last Updated: 2026-04-19T14:22:30+08:00

## Files Changed

- `artifacts/tasks/TASK-984.task.md`
- `artifacts/plans/TASK-984.plan.md`
- `artifacts/code/TASK-984.code.md`
- `artifacts/verify/TASK-984.verify.md`
- `artifacts/status/TASK-984.status.json`
- `artifacts/scripts/migrate_artifact_schema.py`
- `template/artifacts/scripts/migrate_artifact_schema.py`
- `artifacts/scripts/test_guard_units.py`
- `template/artifacts/scripts/test_guard_units.py`
- `docs/artifact_schema.md`
- `template/docs/artifact_schema.md`
- `docs/orchestration.md`
- `template/docs/orchestration.md`
- `README.md`
- `README.zh-TW.md`
- `template/README.md`
- `template/README.zh-TW.md`

## Summary Of Changes

- `migrate_artifact_schema.py` 新增 explicit `input-mode`，把 root tracked normalization 與 external legacy import 分流。
- verify migration 新增 assessment/reporting：`strategy`、`confidence`、`unresolved_fields` 與 `manual_review_required`。
- `external-legacy` 模式下，heading block、checkbox 與無法辨識的 legacy verify 一律降成 `deferred` + `MANUAL_CHECK_DEFERRED`，避免直接升成 authoritative `pass`。
- root / `template/` 測試補上 external legacy import regression；root docs / README 與 template 對應檔同步補 external legacy import contract。
- `template/artifacts/scripts/test_guard_units.py` 已和 root 對齊，template 全量 unit tests 不再落後於 root coverage baseline。
- `run_red_team_suite.py` 的 `RT-012` fixture 已更新為符合現行 verify contract，紅隊 static / all phase 重新回到全綠。

## Mapping To Plan

- plan_item: 1.1, status: done, evidence: "Added --input-mode with root-tracked default and explicit external-legacy mode in migrate_artifact_schema.py."
- plan_item: 2.1, status: done, evidence: "External legacy verify migration now emits strategy/confidence/unresolved fields and downgrades non-structured inputs to manual-review / deferred."
- plan_item: 3.1, status: done, evidence: "Added root/template migration regression tests for external legacy mode and parse_args coverage."
- plan_item: 4.1, status: done, evidence: "Updated docs/artifact_schema.md, docs/orchestration.md, README root/template, and README.zh-TW root/template with the external legacy import contract."
- plan_item: 5.1, status: done, evidence: "Added TASK-984 code/verify/status closure artifacts after the validation chain passed."

## Tests Added Or Updated

- `artifacts/scripts/test_guard_units.py`
  - `test_external_legacy_checkbox_mode_forces_manual_review`
  - `test_external_legacy_structured_mode_preserves_high_confidence_items`
  - `test_parse_args_accepts_external_legacy_mode`
- `template/artifacts/scripts/test_guard_units.py`
  - `test_external_legacy_checkbox_mode_forces_manual_review`
  - `test_parse_args_accepts_external_legacy_mode`
- `python -m pytest artifacts/scripts/test_guard_units.py` → `987 passed`
- `python -m pytest template/artifacts/scripts/test_guard_units.py` → `987 passed`
- `python artifacts/scripts/run_red_team_suite.py --phase static` → 全部案例符合預期
- `python artifacts/scripts/run_red_team_suite.py --phase all` → static/live/prompt 全部案例符合預期

## Known Risks

- 這一輪沒有建立真實外部 legacy corpus；目前 coverage 仍以 synthetic fixture 為主。
- external legacy import 的 heuristic 邊界雖已顯式化，但若未來要 ingest 更異質的歷史 verify，仍需要再補一輪 fixture taxonomy 與欄位推斷規則。

## Blockers

None

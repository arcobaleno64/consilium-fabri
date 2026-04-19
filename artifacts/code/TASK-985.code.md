# Code Result: TASK-985

## Metadata
- Task ID: TASK-985
- Artifact Type: code
- Owner: Codex CLI
- Status: ready
- Last Updated: 2026-04-19T23:04:00+08:00

## Files Changed

- `artifacts/tasks/TASK-985.task.md`
- `artifacts/plans/TASK-985.plan.md`
- `artifacts/code/TASK-985.code.md`
- `artifacts/verify/TASK-985.verify.md`
- `artifacts/status/TASK-985.status.json`
- `artifacts/scripts/legacy_verify_corpus.py`
- `artifacts/scripts/migrate_artifact_schema.py`
- `artifacts/scripts/workflow_constants.py`
- `artifacts/scripts/guard_status_validator.py`
- `artifacts/scripts/test_guard_units.py`
- `artifacts/scripts/run_red_team_suite.py`
- `artifacts/test/legacy_verify_corpus/manifest.json`
- `artifacts/test/legacy_verify_corpus/structured-checklist-complete.verify.md`
- `artifacts/test/legacy_verify_corpus/heading-block-partial.verify.md`
- `artifacts/test/legacy_verify_corpus/checkbox-list-mixed.verify.md`
- `artifacts/test/legacy_verify_corpus/unparseable-fragment.verify.md`
- `docs/artifact_schema.md`
- `docs/red_team_runbook.md`
- `artifacts/red_team/latest_report.md`
- `docs/red_team_scorecard.generated.md`
- `artifacts/verify/TASK-900.verify.md`
- `artifacts/verify/TASK-952.verify.md`
- `artifacts/verify/TASK-953.verify.md`
- `artifacts/verify/TASK-954.verify.md`
- `artifacts/verify/TASK-955.verify.md`
- `artifacts/verify/TASK-956.verify.md`
- `artifacts/verify/TASK-957.verify.md`
- `artifacts/verify/TASK-958.verify.md`
- `artifacts/verify/TASK-960.verify.md`
- `artifacts/verify/TASK-961.verify.md`
- `artifacts/verify/TASK-963.verify.md`
- `artifacts/verify/TASK-980.verify.md`
- `artifacts/verify/TASK-982.verify.md`
- `artifacts/verify/TASK-984.verify.md`
- `template/artifacts/scripts/legacy_verify_corpus.py`
- `template/artifacts/scripts/migrate_artifact_schema.py`
- `template/artifacts/scripts/workflow_constants.py`
- `template/artifacts/scripts/guard_status_validator.py`
- `template/artifacts/scripts/test_guard_units.py`
- `template/artifacts/scripts/run_red_team_suite.py`
- `template/artifacts/test/legacy_verify_corpus/manifest.json`
- `template/artifacts/test/legacy_verify_corpus/structured-checklist-complete.verify.md`
- `template/artifacts/test/legacy_verify_corpus/heading-block-partial.verify.md`
- `template/artifacts/test/legacy_verify_corpus/checkbox-list-mixed.verify.md`
- `template/artifacts/test/legacy_verify_corpus/unparseable-fragment.verify.md`
- `template/docs/artifact_schema.md`
- `template/docs/red_team_runbook.md`
- `template/artifacts/red_team/latest_report.md`
- `template/docs/red_team_scorecard.generated.md`

## Summary Of Changes

- 新增 shared corpus helper `legacy_verify_corpus.py`，讓 unit tests 與 red-team suite 共用同一份 external legacy verify manifest 與 fixture 內容。
- 建立 root / `template/` 的 four-shape external legacy verify corpus：`structured-checklist-complete`、`heading-block-partial`、`checkbox-list-mixed`、`unparseable-fragment`。
- 將 migration regression 改為 corpus-driven golden assertions，直接鎖 `strategy`、`confidence`、`manual_review_required`、`unresolved_fields`、`Pass Fail Result` 與 `MANUAL_CHECK_DEFERRED`。
- 在 `migrate_artifact_schema.py` 收緊 structured 判定，只把真正包含 `criterion` / `method` / `evidence` / `result` 的 checklist block 視為 high-confidence structured；heading block 不再被誤升級。
- 在 `migrate_artifact_schema.py` 收緊 `Evidence Refs` 推斷：command-style evidence lines 不再被誤當成 path refs；root tracked verify 若已明示 `Evidence Refs`，migration 不再追加推斷值。
- shared workflow validators 補 fail-closed hardening：`workflow_constants.py` 現在對缺 profile / adapter rule / policy key 會回傳 validation errors；`guard_status_validator.py` 補回 `reconcile_status_file(..., apply=...)` 相容入口與 dry-run diff。
- 新增 red-team static case `RT-030`，以 unparseable external legacy fragment 驗證 external import 仍維持 fail-closed。
- 套用一次 migration 到 root tracked historical verifies，清掉 14 份舊 `Evidence Refs` canonicalization drift，讓 root baseline 回到可重跑 `changed_files=0`。
- 同步 root / `template/` docs、runner、generated report 與 scorecard，避免 corpus / red-team inventory drift。

## Mapping To Plan

- plan_item: 1.1, status: done, evidence: "Added four external legacy verify corpus fixtures in root/template under artifacts/test/legacy_verify_corpus/."
- plan_item: 2.1, status: done, evidence: "Introduced legacy_verify_corpus.py and rewired test_guard_units.py plus run_red_team_suite.py to load the shared manifest."
- plan_item: 3.1, status: done, evidence: "Corpus-driven migration tests now assert strategy/confidence/manual-review/deferred behavior, and uncovered the heading-block misclassification."
- plan_item: 4.1, status: done, evidence: "Added RT-030 to the static suite and updated the red-team runbook plus generated report/scorecard."
- plan_item: 5.1, status: done, evidence: "Re-applied migration to historical verify artifacts so root dry-run returned to changed_files=0; produced TASK-985 closure artifacts."

## Tests Added Or Updated

- `artifacts/scripts/test_guard_units.py`
  - corpus manifest completeness check
  - corpus-driven external legacy migration regression over four fixture shapes
  - command-style evidence ref filtering regression
  - `workflow_constants.py` fail-closed validation error coverage
  - `guard_status_validator.py` decision warning / reconcile dry-run compatibility coverage
  - `RT-030` runner smoke test
- `template/artifacts/scripts/test_guard_units.py`
  - synced with root full suite (`992 passed`)
- `artifacts/scripts/run_red_team_suite.py`
  - new static case `RT-030`

## Known Risks

- 尚未 ingest 真實第三方 external legacy verify artifacts；目前 corpus 已從 inline synthetic 升級成異質 fixture，但仍是 repo-curated sample set。

## Blockers

None

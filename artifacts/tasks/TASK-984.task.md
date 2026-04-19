# Task: TASK-984 External Legacy Verify Import Boundary

## Metadata
- Task ID: TASK-984
- Artifact Type: task
- Owner: Codex CLI
- Status: approved
- Last Updated: 2026-04-19T14:03:53+08:00

## Objective
把 `verify migration` 的 legacy import 路徑改成顯式、保守且可審計：root tracked artifacts 維持 strict no-op，外部 legacy verify 只能透過明確 `external-legacy` 模式匯入，且非結構化輸入不得直接升成 authoritative `pass`。

## Background
- 目前 root repo tracked artifacts 已收斂，`python artifacts/scripts/migrate_artifact_schema.py` dry-run 為 `changed_files=0`。
- 既有 `migrate_artifact_schema.py` 對 legacy verify 仍保留 heading / checkbox heuristic，若未來匯入外部歷史 artifacts，存在把語義不完整輸入誤映射成可用 verify 的風險。
- `docs/orchestration.md` 與 `docs/artifact_schema.md` 已明定 root tracked artifacts 不得依賴 legacy/schema fallback；fallback 只保留給外部或歷史輸入。

## Inputs
- [artifacts/scripts/migrate_artifact_schema.py](artifacts/scripts/migrate_artifact_schema.py)
- [artifacts/scripts/test_guard_units.py](artifacts/scripts/test_guard_units.py)
- [docs/artifact_schema.md](docs/artifact_schema.md)
- [docs/orchestration.md](docs/orchestration.md)
- [README.md](README.md)
- [README.zh-TW.md](README.zh-TW.md)

## Constraints
- root tracked path 必須維持 deterministic normalization；`python artifacts/scripts/migrate_artifact_schema.py` 在 repo root dry-run 仍需 `changed_files=0`。
- external legacy import 必須是顯式 mode，不得默默放寬 root default strictness。
- 非結構化 legacy verify 匯入後只能落成 manual-review / deferred 路徑，不得直接升成 `pass`。
- 變更 `docs/`、README 或 guard script 後，必須同步 `template/` 對應檔案。
- 不整理或回退既有 unrelated worktree 變更。

## Acceptance Criteria
- [ ] AC-1: `migrate_artifact_schema.py` 新增顯式 `input-mode`，至少區分 `root-tracked` 與 `external-legacy`。
- [ ] AC-2: `external-legacy` 模式會為 verify migration 輸出 strategy / confidence / unresolved fields，且非結構化 legacy verify 會降成 manual-review / deferred。
- [ ] AC-3: root tracked 預設 dry-run 仍維持 `changed_files=0`。
- [ ] AC-4: root / `template/` 的 migration tests 已補上 `external-legacy` regression coverage。
- [ ] AC-5: `docs/`、README root / `template/` 已更新 external legacy import contract。

## Dependencies
- Python 3
- 現有 `guard_status_validator.py` structured checklist contract
- 現有 `guard_contract_validator.py` README / template sync 檢查

## Out of Scope
- 新增外部 legacy artifact corpus 目錄
- 擴張更多 heuristic pattern beyond heading / checkbox / structured checklist
- 調整 `guard_status_validator.py` 的 root strictness 基本規則
- 整理 unrelated worktree 變更

## Assurance Level
POC

## Project Adapter
generic

## Current Status Summary
Planned。這一輪只收斂 external legacy verify import boundary：把 mode split、manual-review downgrade、migration reporting、tests 與文件同步一起落地，不處理更大範圍的 legacy corpus 建模。

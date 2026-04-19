# Task: TASK-985 External Legacy Verify Corpus Hardening

## Metadata
- Task ID: TASK-985
- Artifact Type: task
- Owner: Codex CLI
- Status: approved
- Last Updated: 2026-04-19T19:10:00+08:00

## Objective
建立可重跑、可審計的 external legacy verify corpus，將 `TASK-984` 尚未收斂的 synthetic-only 風險降到最低，並把 corpus regression、red-team drill、root / `template/` 同步與 closure evidence 一次補齊。

## Background
- `TASK-984` 已把 external legacy verify import 切成顯式 `external-legacy` 模式，且非結構化輸入會降級成 manual-review / deferred。
- 目前 regression coverage 仍以 inline synthetic fixture 為主，`artifacts/test/` 與 `template/artifacts/test/` 尚未建立真正的 external legacy verify corpus。
- 若未來 ingest 外部歷史 verify artifacts，缺少 corpus 會讓 heuristic 邊界只能靠零散測試維持，風險是覆蓋不足或行為被意外放寬。

## Inputs
- [artifacts/tasks/TASK-984.task.md](artifacts/tasks/TASK-984.task.md)
- [artifacts/plans/TASK-984.plan.md](artifacts/plans/TASK-984.plan.md)
- [artifacts/code/TASK-984.code.md](artifacts/code/TASK-984.code.md)
- [artifacts/verify/TASK-984.verify.md](artifacts/verify/TASK-984.verify.md)
- [artifacts/scripts/migrate_artifact_schema.py](artifacts/scripts/migrate_artifact_schema.py)
- [artifacts/scripts/test_guard_units.py](artifacts/scripts/test_guard_units.py)
- [artifacts/scripts/run_red_team_suite.py](artifacts/scripts/run_red_team_suite.py)
- [docs/red_team_runbook.md](docs/red_team_runbook.md)

## Constraints
- 必須建立實體 corpus fixtures，不得只把既有 inline synthetic strings 換個包裝。
- 非結構化 external legacy verify 仍必須 fail-closed 到 manual-review / deferred，不得為了讓 corpus 綠燈而放寬 heuristic。
- 若修改 workflow docs、guard scripts、red-team runner 或 test corpus，必須同步 `template/` 對應檔案。
- 不整理或回退既有 unrelated dirty worktree 變更。

## Acceptance Criteria
- [ ] AC-1: `artifacts/test/` 與 `template/artifacts/test/` 建立 external legacy verify corpus，至少覆蓋 structured checklist、heading block、checkbox list、unparseable fragment 四類。
- [ ] AC-2: unit tests 改為讀取 corpus fixtures，驗證 strategy / confidence / unresolved fields / deferred behavior，不再只依賴 inline synthetic strings。
- [ ] AC-3: red-team suite 新增至少一個 external legacy import fail-closed drill，證明未知 legacy 片段不會被誤升成 authoritative verify。
- [ ] AC-4: root / `template/` 全量 guard unit tests、migration dry-run、contract / context / status validators 與 red-team phase 仍全綠，覆蓋面沒有退步。
- [ ] AC-5: 新 task 的 code / verify / status closure artifacts 明確記錄 corpus、red-team 與 residual risk 結果。

## Dependencies
- Python 3
- 現有 `TASK-900` sample artifacts
- 現有 `TASK-984` external-legacy migration boundary

## Out of Scope
- 新增更多 heuristic strategy beyond `structured-checklist` / `heading-block-heuristic` / `checkbox-heuristic` / `manual-rewrite-fallback`
- 大量匯入真實外部 repo artifacts
- 調整 `guard_status_validator.py` 的 root strictness 基本規則

## Assurance Level
POC

## Project Adapter
generic

## Current Status Summary
Planned。這一輪只處理 external legacy verify corpus hardening：把 corpus fixtures、shared loader、golden regression、red-team external import drill 與 closure evidence 一起補齊，不擴張到新的 heuristic 設計。

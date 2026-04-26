# Plan: TASK-955

## Metadata

- Task ID: TASK-955
- Artifact Type: plan
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-13T13:55:35+08:00
- PDCA Stage: P

## Scope

- 升級 root 與 `template/` 的 `guard_status_validator.py`，讓 status guard 在 dirty-worktree heuristic 之外，還能依 code artifact 的 `commit-range` diff evidence 重建 historical changed files。
- 收斂 `--allow-scope-drift`：只有存在顯式 decision waiver 時才允許 drift 降級為 warning。
- 更新 root 與 `template/` 的 `run_red_team_suite.py` 與固定 prompt regression cases，將新的 historical diff evidence 與 waiver contract 納入回歸。
- 更新 schema、runbook、backlog 與入口文件，反映新的 replay / waiver 規則與殘餘限制。

## Files Likely Affected

- `artifacts/tasks/TASK-955.task.md`
- `artifacts/decisions/TASK-955.decision.md`
- `artifacts/plans/TASK-955.plan.md`
- `artifacts/code/TASK-955.code.md`
- `artifacts/verify/TASK-955.verify.md`
- `artifacts/status/TASK-955.status.json`
- `artifacts/scripts/guard_status_validator.py`
- `template/artifacts/scripts/guard_status_validator.py`
- `artifacts/scripts/run_red_team_suite.py`
- `template/artifacts/scripts/run_red_team_suite.py`
- `artifacts/scripts/drills/prompt_regression_cases.json`
- `template/artifacts/scripts/drills/prompt_regression_cases.json`
- `docs/artifact_schema.md`
- `template/docs/artifact_schema.md`
- `docs/red_team_runbook.md`
- `template/docs/red_team_runbook.md`
- `docs/red_team_backlog.md`
- `template/docs/red_team_backlog.md`
- `README.md`
- `README.zh-TW.md`
- `OBSIDIAN.md`
- `template/README.md`
- `template/README.zh-TW.md`
- `template/OBSIDIAN.md`

## Proposed Changes

- 在 code artifact schema 加入可選 `## Diff Evidence` 區段，定義 `commit-range` snapshot 的欄位。
- 在 decision artifact schema 加入可選 `## Guard Exception` 區段，定義 `allow-scope-drift` waiver 的結構。
- 在 status guard 增加 clean-task 的 historical diff replay，當 `## Diff Evidence` 提供合法 `commit-range` 時，直接以 git diff 結果比對 plan / code 宣告。
- 修改 `--allow-scope-drift` 行為：若存在 drift 但沒有匹配的 decision waiver，validator 仍應 fail。
- 新增 red-team static cases，覆蓋 historical commit-range drift 與缺少 / 存在 waiver 的 `--allow-scope-drift` 情境。
- 補上固定 prompt regression cases，鎖住 diff evidence contract 與 decision-gated waiver contract。
- 同步更新 runbook、backlog、README 與 Obsidian 入口，說明新的 hardening 邊界。

## Risks

- R1
  - Risk: `commit-range` evidence 指向不存在或不可重放的 refs，導致歷史 task 在 clean worktree 下誤判失敗
  - Trigger: code artifact 記錄了錯誤的 `Base Ref` / `Head Ref`，或 refs 已不在本地 repo
  - Detection: `python artifacts/scripts/guard_status_validator.py --task-id TASK-955 --artifacts-root artifacts` 或 red-team fixture 回報 diff evidence replay 失敗
  - Mitigation: 只有在 `## Diff Evidence` 存在且欄位完整時才啟用 replay；若啟用後 git diff 無法重放，直接以明確錯誤訊息 fail
  - Severity: blocking
- R2
  - Risk: `--allow-scope-drift` 只檢查「有 decision artifact」而不檢查 waiver 範圍，導致任何 decision 都可被濫用成 blanket exception
  - Trigger: validator 對 decision artifact 只做存在性檢查，未驗證 `Exception Type` 與 `Scope Files`
  - Detection: red-team waiver case 在 decision 未列明 drift files 的情況下仍通過
  - Mitigation: 將 waiver 設計成結構化區段，要求 `Exception Type: allow-scope-drift` 並覆蓋 drift files
  - Severity: blocking
- R3
  - Risk: root / `template/` 的 guard、runner、schema、README 與 prompt regression cases 不同步，造成 contract drift
  - Trigger: 只更新 root 或漏改 `template/` / 入口文件 / regression cases
  - Detection: `python artifacts/scripts/guard_contract_validator.py --root .` 或 `python artifacts/scripts/prompt_regression_validator.py --root .`
  - Mitigation: 所有 workflow 檔案與 template、入口文件、prompt regression 同批更新後再驗證
  - Severity: blocking
- R4
  - Risk: historical replay 的 red-team fixture 沒有建立正確 baseline / follow-up commit，導致測例實際上仍在測 dirty worktree 而非 clean historical diff
  - Trigger: temp fixture 少做 commit，或在 replay 前仍保留未提交變更
  - Detection: static suite 報告顯示案例命中的是 git-backed dirty-worktree 訊息，而不是 commit-range replay 訊息
  - Mitigation: fixture 先建立 baseline commit，再建立 follow-up commit，最後在 clean worktree 下執行 validator
  - Severity: blocking

## Validation Strategy

- 執行 `python artifacts/scripts/prompt_regression_validator.py --root .`
- 執行 `python artifacts/scripts/run_red_team_suite.py --phase static`
- 執行 `python artifacts/scripts/guard_contract_validator.py --root .`
- 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --artifacts-root artifacts`
- 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-955 --artifacts-root artifacts`

## Out of Scope

- 直接支援 GitHub / GitLab PR diff API
- 回補既有舊 task 的 diff evidence
- 修改產品程式或外部 repo

## Ready For Coding

yes

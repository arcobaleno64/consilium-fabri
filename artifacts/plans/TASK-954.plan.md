# Plan: TASK-954

## Metadata

- Task ID: TASK-954
- Artifact Type: plan
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-13T13:46:02+08:00
- PDCA Stage: P

## Scope

- 升級 root 與 `template/` 的 `guard_status_validator.py`，在 task 專屬 artifact 檔位於 dirty worktree 時，直接讀 git changed files 並比對 plan / code artifact。
- 更新 root 與 `template/` 的 `run_red_team_suite.py`，新增一個 git-backed scope drift static case。
- 更新 schema、runbook、backlog 與入口文件，反映新的 auto guard 行為與殘餘限制。

## Files Likely Affected

- `artifacts/tasks/TASK-954.task.md`
- `artifacts/plans/TASK-954.plan.md`
- `artifacts/code/TASK-954.code.md`
- `artifacts/verify/TASK-954.verify.md`
- `artifacts/scripts/guard_status_validator.py`
- `template/artifacts/scripts/guard_status_validator.py`
- `artifacts/scripts/run_red_team_suite.py`
- `template/artifacts/scripts/run_red_team_suite.py`
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
- `artifacts/status/TASK-954.status.json`

## Proposed Changes

- 在 status guard 增加 git root 偵測、actual changed files 蒐集與 task-owned dirty worktree 判定。
- 當 git-backed heuristic 可用時，自動比對實際 changed files 與 code artifact / plan artifact 宣告；不符合時預設 fail。
- 新增 `RT-010` 靜態案例，驗證 dirty worktree 中多出未宣告檔案時，status guard 會直接失敗。
- 更新 schema、runbook、backlog、README 與 Obsidian，說明新 guard 與 remaining gap。
- 建立 `TASK-954` 的 code / verify artifact，驗證新 guard 能檢查自己的 workflow 變更。

## Risks

- R1
  - Risk: git-backed guard 在非 git 環境或歷史 clean worktree task 上誤報，導致既有樣本回歸失敗
  - Trigger: 直接對所有 task 強制要求 git changed files，而不檢查 task-owned dirty worktree
  - Detection: `python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --artifacts-root artifacts` 或其他既有樣本開始失敗
  - Mitigation: 只有在偵測到 task 專屬 artifact 檔位於 dirty worktree 時才啟用 git-backed heuristic；否則回退到既有 artifact-based check
  - Severity: blocking
- R2
  - Risk: root 與 `template/` 的 guard / runner / docs 不一致，導致 contract guard fail
  - Trigger: 只更新 root 或只更新 `template/`
  - Detection: `python artifacts/scripts/guard_contract_validator.py --root .`
  - Mitigation: 所有 workflow 變更同批同步到 `template/` 後再驗證
  - Severity: blocking
- R3
  - Risk: red-team case 沒有建立 git baseline，導致所有 fixture 檔都被當成 untracked 變更，測試失真
  - Trigger: temp fixture 直接執行 status guard 而未先 `git init` + baseline commit
  - Detection: `RT-010` 報錯內容充滿所有 fixture 檔案，而不是針對注入的 rogue change
  - Mitigation: 在 temp fixture 先初始化 git repo、建立 baseline commit，再注入未宣告變更
  - Severity: blocking
- R4
  - Risk: plan 未把 `artifacts/status/TASK-954.status.json` 列入影響範圍，收尾時被 guard 視為 scope drift
  - Trigger: `TASK-954.code.md` 列出 status 檔，但 plan 未列在 `## Files Likely Affected`
  - Detection: `python artifacts/scripts/guard_status_validator.py --task-id TASK-954 --artifacts-root artifacts`
  - Mitigation: 在 plan 初始版本就把 status artifact 列入 files list，並在收尾前重跑 status guard
  - Severity: blocking

## Validation Strategy

- 執行 `python artifacts/scripts/run_red_team_suite.py --phase static`
- 執行 `python artifacts/scripts/guard_contract_validator.py --root .`
- 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-954 --artifacts-root artifacts`

## Out of Scope

- prompt regression 擴充
- historical committed diff reconstruction

## Ready For Coding

yes

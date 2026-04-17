# Plan: TASK-957

## Metadata

- Task ID: TASK-957
- Artifact Type: plan
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-13T14:40:02+08:00

## Scope

- 升級 root 與 `template/` 的 `guard_status_validator.py`，加入 GitHub provider-backed PR diff evidence。
- 更新 root 與 `template/` 的 `run_red_team_suite.py`，新增本地 fake provider 的 static drill。
- 更新 root 與 `template/` 的 prompt regression cases、schema、runbook、backlog 與入口文件，反映新的 `github-pr` evidence contract。

## Files Likely Affected

- `artifacts/tasks/TASK-957.task.md`
- `artifacts/research/TASK-957.research.md`
- `artifacts/decisions/TASK-957.decision.md`
- `artifacts/plans/TASK-957.plan.md`
- `artifacts/code/TASK-957.code.md`
- `artifacts/verify/TASK-957.verify.md`
- `artifacts/status/TASK-957.status.json`
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

- 在 `## Diff Evidence` 新增 `Evidence Type: github-pr` 契約，至少定義 `Repository`、`PR Number`、可選 `API Base URL`、`Changed Files Snapshot`、`Snapshot SHA256`。
- 在 status guard 新增 GitHub PR files fetch path，支援 pagination 與 `GITHUB_TOKEN` / `GH_TOKEN` auth，並以 provider file list 驗證 plan/code scope。
- 新增本地 fake provider static case，證明 provider-backed path 可在無外網下重放並攔截 scope drift。
- 擴充 prompt regression 與文件，鎖住新的 GitHub provider-backed evidence contract。

## Risks

- R1
  - Risk: provider-backed evidence 依賴網路 / token，若直接綁到真實 GitHub，static suite 會變成脆弱且不可重跑
  - Trigger: red-team case 直接打真實 `api.github.com`
  - Detection: `python artifacts/scripts/run_red_team_suite.py --phase static` 在離線或 rate-limit 狀態下失敗
  - Mitigation: static suite 使用本地 fake provider server，只在真實 guard path 保留可選的 live provider 呼叫
  - Severity: blocking
- R2
  - Risk: GitHub API pagination 沒處理，導致多頁 PR files 的 scope evidence 不完整
  - Trigger: PR files 超過一頁時 guard 只讀第一頁
  - Detection: provider-backed fixture 或真實 PR 回傳 file count 明顯少於 snapshot
  - Mitigation: 固定以 `per_page=100` 逐頁抓取，直到回傳空頁或不足一頁
  - Severity: blocking
- R3
  - Risk: auth failure / private repo / rate-limit 被默默吞掉，guard 回退成 artifact-only 導致 evidence 邊界失真
  - Trigger: API 403 / 404 / 401 時只記 warning，不直接 fail
  - Detection: provider-backed evidence 設定錯誤時，validator 仍顯示 pass 或只出現模糊 warning
  - Mitigation: provider path 一旦被選用，非成功回應必須直接 fail 並包含 status code / body 摘要
  - Severity: blocking
- R4
  - Risk: root / `template/` 的 schema、runner、README 與 regression cases 不同步，造成 contract drift
  - Trigger: 只更新 root 或漏改 template / 入口 / regression cases
  - Detection: `python artifacts/scripts/guard_contract_validator.py --root .` 或 `python artifacts/scripts/prompt_regression_validator.py --root .`
  - Mitigation: 所有 workflow 檔案與 template、入口文件、prompt regression 同批更新後再驗證
  - Severity: blocking

## Validation Strategy

- 執行 `python artifacts/scripts/prompt_regression_validator.py --root .`
- 執行 `python artifacts/scripts/run_red_team_suite.py --phase static`
- 執行 `python artifacts/scripts/guard_contract_validator.py --root .`
- 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --artifacts-root artifacts`
- 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-956 --artifacts-root artifacts`
- 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-957 --artifacts-root artifacts`

## Out of Scope

- GitLab / Azure / Bitbucket support
- archive fallback / git object retention policy
- 產品程式或 external repo 修改

## Ready For Coding

yes
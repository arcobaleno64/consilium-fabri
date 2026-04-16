# Code Result: TASK-957

## Metadata

- Task ID: TASK-957
- Artifact Type: code
- Owner: Codex
- Status: ready
- Last Updated: 2026-04-13T14:57:33+08:00

## Files Changed

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
- `template/README.md`
- `README.zh-TW.md`
- `template/README.zh-TW.md`
- `OBSIDIAN.md`
- `template/OBSIDIAN.md`

## Summary Of Changes

- 在 root 與 `template/` 的 `guard_status_validator.py` 新增 `Evidence Type: github-pr`，可用 GitHub PR files API 逐頁重建 changed files，並支援可覆寫的 `API Base URL`。
- provider-backed evidence 現在會先驗證 `Changed Files Snapshot` 與 `Snapshot SHA256`，再以 provider response 對照 `## Files Changed` 與 `## Files Likely Affected`；private / rate-limited GitHub 存取可用 `GITHUB_TOKEN` / `GH_TOKEN`。
- 在 root 與 `template/` 的 `run_red_team_suite.py` 新增 `RT-015`，使用本地 fake GitHub provider 驗證第二頁 PR files 也會被抓到，避免 pagination drift 被漏掉。
- 在固定 prompt regression cases 新增 `PR-019`，鎖住 `github-pr` evidence、`API Base URL` 與 token 邊界；同步更新 schema、runbook、backlog、README 與 Obsidian 入口。

## Mapping To Plan

- 對應 plan 的 validator 升級：`guard_status_validator.py` 新增 GitHub provider-backed PR files fetch path、pagination 與 auth/error handling。
- 對應 plan 的 red-team / regression 擴充：`run_red_team_suite.py` 新增 `RT-015`，`prompt_regression_cases.json` 新增 `PR-019`。
- 對應 plan 的 schema / 文件同步：更新 `docs/artifact_schema.md`、`docs/red_team_runbook.md`、`docs/red_team_backlog.md`、README 與 Obsidian 入口文件，說明 `github-pr` contract。

## Tests Added Or Updated

- `python artifacts/scripts/prompt_regression_validator.py --root .`
- `python artifacts/scripts/guard_contract_validator.py --root .`
- `python artifacts/scripts/run_red_team_suite.py --phase static`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --artifacts-root artifacts`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-956 --artifacts-root artifacts`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-957 --artifacts-root artifacts`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-958 --artifacts-root artifacts`

## Known Risks

- provider-backed historical diff evidence 目前只支援 GitHub；GitLab / Azure / Bitbucket 仍屬後續補強。
- GitHub PR files endpoint 仍受 provider auth、rate-limit 與 file-count 上限影響；若沒有 token、provider 異常或超出上限，guard 仍會直接 fail。

## Diff Evidence

None (this task was completed in a dirty worktree and did not record a historical replay snapshot for itself)

## Blockers

None
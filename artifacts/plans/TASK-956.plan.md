# Plan: TASK-956

## Metadata

- Task ID: TASK-956
- Artifact Type: plan
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-13T14:14:56+08:00
- PDCA Stage: P

## Scope

- 升級 root 與 `template/` 的 `guard_status_validator.py`，讓 clean-task `commit-range` diff evidence 支援 immutable commit pinning 與 snapshot checksum 驗證。
- 更新 root 與 `template/` 的 `run_red_team_suite.py`，新增至少一個 evidence corruption / ref drift 類 static case。
- 更新 root 與 `template/` 的 prompt regression cases、schema、runbook、backlog 與入口文件，反映新的 immutable evidence contract。

## Files Likely Affected

- `artifacts/tasks/TASK-956.task.md`
- `artifacts/decisions/TASK-956.decision.md`
- `artifacts/plans/TASK-956.plan.md`
- `artifacts/code/TASK-956.code.md`
- `artifacts/verify/TASK-956.verify.md`
- `artifacts/status/TASK-956.status.json`
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

- 在 `## Diff Evidence` 增加 pinned commit 與 snapshot checksum 欄位，例如 `Base Commit`、`Head Commit`、`Changed Files Snapshot`、`Snapshot SHA256`。
- status guard 對 `commit-range` evidence 改用 pinned commits 做 replay，並比對 snapshot / checksum 與實際 replayed diff 是否一致。
- 若提供 `Base Ref` / `Head Ref`，則 guard 也會檢查它們是否仍對應到 pinned commit，至少產生 warning 以揭露 ref drift。
- 新增 red-team static case，驗證 corrupted snapshot checksum 或 ref drift evidence 會被明確攔下。
- 擴充 prompt regression cases 與文件，鎖住 immutable diff evidence contract。

## Risks

- R1
  - Risk: 新 evidence 欄位要求過嚴，導致既有沒有 `## Diff Evidence` 的樣本或 dirty-worktree task 被誤判失敗
  - Trigger: validator 將 immutable evidence 視為所有 code artifact 的必填欄位
  - Detection: `python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --artifacts-root artifacts` 或 `TASK-955` 開始失敗
  - Mitigation: 只在 code artifact 已選擇 `commit-range` diff evidence 時要求 pinned commit 與 snapshot checksum；無 evidence 或 dirty-worktree path 維持相容
  - Severity: blocking
- R2
  - Risk: snapshot checksum 只驗證 artifact 內部一致性，若 red-team 沒有覆蓋 corruption 情境，實際價值會停留在文件層
  - Trigger: 實作了 checksum，但沒有任何 case 故意改壞 snapshot 或 hash
  - Detection: static suite 沒有對應 evidence corruption / mismatch drill
  - Mitigation: 新增至少一個 static case，故意製造 snapshot mismatch 或 checksum mismatch，確保 guard 直接 fail
  - Severity: blocking
- R3
  - Risk: `Base Ref` / `Head Ref` 與 pinned commit 的一致性檢查只做 best-effort，造成 ref drift 被默默忽略
  - Trigger: code artifact 保留舊 branch ref，但 branch 已移動到不同 commit
  - Detection: static case 或 validator warning 顯示 ref 不再解析到 recorded commit
  - Mitigation: 若 ref 存在就做解析比對，至少產生 warning；若明顯 mismatch 且 evidence 嘗試依 ref replay，則 fail
  - Severity: blocking
- R4
  - Risk: root / `template/` 的 runner、schema、README 與 regression cases 不同步，造成 contract drift
  - Trigger: 只更新 root 或漏改 template / 入口 / regression cases
  - Detection: `python artifacts/scripts/guard_contract_validator.py --root .` 或 `python artifacts/scripts/prompt_regression_validator.py --root .`
  - Mitigation: 所有 workflow 檔案與 template、入口文件、prompt regression 同批更新後再驗證
  - Severity: blocking

## Validation Strategy

- 執行 `python artifacts/scripts/prompt_regression_validator.py --root .`
- 執行 `python artifacts/scripts/run_red_team_suite.py --phase static`
- 執行 `python artifacts/scripts/guard_contract_validator.py --root .`
- 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --artifacts-root artifacts`
- 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-955 --artifacts-root artifacts`
- 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-956 --artifacts-root artifacts`

## Out of Scope

- 接入 remote PR diff API
- 回補既有歷史 task 的 evidence
- 產品程式或 external repo 修改

## Ready For Coding

yes
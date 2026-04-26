# Plan: TASK-958

## Metadata

- Task ID: TASK-958
- Artifact Type: plan
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-13T14:40:02+08:00
- PDCA Stage: P

## Scope

- 升級 root 與 `template/` 的 `guard_status_validator.py`，讓 `commit-range` evidence 在 local git replay 失敗時可改用 archive file fallback。
- 更新 root 與 `template/` 的 `run_red_team_suite.py`，新增 archive fallback / corruption static drills。
- 更新 root 與 `template/` 的 prompt regression cases、schema、runbook、backlog 與入口文件，反映新的 retention / archive policy。

## Files Likely Affected

- `artifacts/tasks/TASK-958.task.md`
- `artifacts/decisions/TASK-958.decision.md`
- `artifacts/plans/TASK-958.plan.md`
- `artifacts/code/TASK-958.code.md`
- `artifacts/verify/TASK-958.verify.md`
- `artifacts/status/TASK-958.status.json`
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

- 在 `## Diff Evidence` 新增 `Archive Path` 與 `Archive SHA256` 欄位，定義 text archive format 與 hash 驗證規則。
- 在 status guard 中，若 `commit-range` local replay 失敗且 archive metadata 完整，改用 archive file 的 file list 做 fallback，並持續驗證 `## Files Changed` / `## Files Likely Affected`。
- 新增 static drills，分別覆蓋 archive fallback 與 archive hash corruption。
- 擴充 prompt regression 與文件，將 object retention / archive policy 明文化。

## Risks

- R1
  - Risk: archive fallback 只做存在性檢查，不驗證 hash 或內容格式，導致損毀 archive 仍被接受
  - Trigger: `Archive Path` 存在但 `Archive SHA256` 錯誤，guard 仍照單全收
  - Detection: red-team corruption drill 在 archive hash 錯誤時仍通過
  - Mitigation: archive metadata 一旦被提供，就必須同時驗證 hash、UTF-8 可讀性、行格式與 snapshot 一致性
  - Severity: blocking
- R2
  - Risk: local git replay 與 archive fallback 的錯誤邊界混亂，導致物件缺失時直接 fail，根本不進 fallback
  - Trigger: commit-range replay 失敗後沒有檢查 archive metadata
  - Detection: archive fallback drill 命中的是 raw git replay failure，而不是 fallback scope check
  - Mitigation: 將 commit-range path 拆成「優先 local replay、失敗時 fallback archive」兩段式流程
  - Severity: blocking
- R3
  - Risk: archive file format 未被文件固定，讓不同 agent 寫出不同排序或換行格式，造成跨環境 hash 漂移
  - Trigger: archive file 一次用 CRLF、一次用未排序 entries
  - Detection: 同一組 files 在不同環境生成不同 archive hash 或 guard 報格式錯誤
  - Mitigation: 文件固定為 UTF-8、normalized relative paths、每行一個 path、排序後、LF 換行
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
- 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-958 --artifacts-root artifacts`

## Out of Scope

- GitHub provider-backed PR diff evidence
- 完整 patch / bundle restore
- 產品程式或 external repo 修改

## Ready For Coding

yes
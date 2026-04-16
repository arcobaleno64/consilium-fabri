# Plan: TASK-953

## Metadata
- Task ID: TASK-953
- Artifact Type: plan
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-13T13:34:01+08:00

## Scope
- 擴充 root 與 `template/` 的 `prompt_regression_cases.json`，新增 4 個 decision-focused 固定測例。
- 更新 root 與 `template/` 的 `run_red_team_suite.py`，將新增案例納入 prompt phase。
- 更新 root 與 `template/` 的 `prompt_regression_validator.py` 說明文字，反映 coverage 已包含關鍵 workflow contracts。
- 更新 runbook 與對外入口文件，說明新的 decision-related coverage。

## Files Likely Affected
- `artifacts/scripts/drills/prompt_regression_cases.json`
- `template/artifacts/scripts/drills/prompt_regression_cases.json`
- `artifacts/scripts/run_red_team_suite.py`
- `template/artifacts/scripts/run_red_team_suite.py`
- `artifacts/scripts/prompt_regression_validator.py`
- `template/artifacts/scripts/prompt_regression_validator.py`
- `docs/red_team_runbook.md`
- `template/docs/red_team_runbook.md`
- `README.md`
- `README.zh-TW.md`
- `OBSIDIAN.md`
- `template/README.md`
- `template/README.zh-TW.md`
- `template/OBSIDIAN.md`
- `artifacts/status/TASK-953.status.json`

## Proposed Changes
- 新增 `PR-012` 到 `PR-015`，分別鎖住 conflict-to-decision routing、decision artifact trigger matrix、decision artifact schema completeness、external failure STOP contract。
- 更新 prompt regression runner 與 validator 說明，使其明確涵蓋 entry prompts 與關鍵 workflow contracts。
- 更新 red-team runbook、README 與 Obsidian 入口，反映新增 coverage 與執行範圍。

## Risks
- R1
  - Risk: 新案例只更新 root，未同步到 `template/`，導致 contract guard fail
  - Trigger: root 與 `template/` 的 cases / runner / docs 出現不一致
  - Detection: `python artifacts/scripts/guard_contract_validator.py --root .`
  - Mitigation: 同批修改 root 與 `template/` 對應檔案，再執行 contract guard
  - Severity: blocking
- R2
  - Risk: 新增 `PR-012+` 後，`run_red_team_suite.py` 未同步註冊，導致 prompt phase coverage 與文件描述脫節
  - Trigger: `prompt_regression_cases.json` 出現新 case id，但 runner 報表沒有對應列
  - Detection: `python artifacts/scripts/run_red_team_suite.py --phase prompt`
  - Mitigation: 同步新增 case function 與 `build_cases()` 條目
  - Severity: blocking
- R3
  - Risk: decision-focused case 引用不存在於現有 contract 的內容，造成 regression false fail
  - Trigger: assertion 使用 prompt / docs 中不存在的字句或邏輯
  - Detection: `python artifacts/scripts/prompt_regression_validator.py --root .`
  - Mitigation: 僅選用 `CLAUDE.md`、`docs/orchestration.md`、`docs/artifact_schema.md` 已明文化的規則做 assertions
  - Severity: non-blocking
- R4
  - Risk: plan 沒有把 status artifact 列入 scope，導致收尾時被 guard 視為 plan/code drift
  - Trigger: `TASK-953.code.md` 列出 `artifacts/status/TASK-953.status.json`，但 plan 未列在 `## Files Likely Affected`
  - Detection: `python artifacts/scripts/guard_status_validator.py --task-id TASK-953 --artifacts-root artifacts`
  - Mitigation: 在 plan 一開始就把 status artifact 納入 files list 與 validation strategy
  - Severity: blocking

## Validation Strategy
- 執行 `python artifacts/scripts/prompt_regression_validator.py --root .`
- 執行 `python artifacts/scripts/run_red_team_suite.py --phase prompt`
- 執行 `python artifacts/scripts/guard_contract_validator.py --root .`
- 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-953 --artifacts-root artifacts`

## Out of Scope
- 直接修改 workflow contract 條文
- 開始 M2 的 diff-to-plan guard implementation

## Ready For Coding
yes
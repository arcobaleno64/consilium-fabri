# Plan: TASK-952

## Metadata
- Task ID: TASK-952
- Artifact Type: plan
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-13T13:07:58+08:00
- PDCA Stage: P

## Scope
- 擴充 root 與 `template/` 的 `prompt_regression_cases.json`，新增 4 個固定測例。
- 更新 root 與 `template/` 的 `run_red_team_suite.py`，讓 prompt phase 會執行新增案例。
- 更新 red-team runbook 與對外入口文件，明確說明新增 coverage。

## Files Likely Affected
- `artifacts/scripts/drills/prompt_regression_cases.json`
- `template/artifacts/scripts/drills/prompt_regression_cases.json`
- `artifacts/scripts/run_red_team_suite.py`
- `template/artifacts/scripts/run_red_team_suite.py`
- `docs/red_team_runbook.md`
- `template/docs/red_team_runbook.md`
- `README.md`
- `README.zh-TW.md`
- `OBSIDIAN.md`
- `template/README.md`
- `template/README.zh-TW.md`
- `template/OBSIDIAN.md`
- `artifacts/status/TASK-952.status.json`

## Proposed Changes
- 新增 `PR-008` 到 `PR-011`，分別鎖住 artifact-only truth、workflow sync completeness、Gemini blocked preconditions、Codex summary discipline。
- 將 prompt phase 內建 runner 擴充到 11 個固定案例。
- 更新 runbook 與入口文件，說明 prompt regression 新 coverage 範圍。

## Risks
- R1
  - Risk: root 與 `template/` 的 prompt regression cases 或 runner 不一致，導致 contract guard fail
  - Trigger: 只更新 root 或只更新 `template/`
  - Detection: `python artifacts/scripts/guard_contract_validator.py --root .`
  - Mitigation: 所有 workflow 變更同批同步到 `template/` 並執行 contract guard
  - Severity: blocking
- R2
  - Risk: 新增案例名稱已寫入 JSON，但 `run_red_team_suite.py` 未同步註冊，造成 prompt phase coverage 與文件不一致
  - Trigger: `prompt_regression_cases.json` 出現 `PR-008+`，但 runner 只執行到 `PR-007`
  - Detection: `python artifacts/scripts/run_red_team_suite.py --phase prompt`
  - Mitigation: 同步新增 case runner function 與 `build_cases()` 條目
  - Severity: blocking
- R3
  - Risk: 新案例描述超出 prompt 既有契約，導致 regression test 變成脆弱或誤報
  - Trigger: assertion 依賴 prompt 中不存在的字句或語意
  - Detection: `python artifacts/scripts/prompt_regression_validator.py --root .`
  - Mitigation: 僅選用目前 `CLAUDE.md`、`GEMINI.md`、`CODEX.md` 已明文化的 hard rules 建 case
  - Severity: non-blocking
- R4
  - Risk: task status 收尾沒有被列入 plan scope，導致 code artifact 與 plan 映射不完整而被 guard 視為 drift
  - Trigger: `TASK-952.code.md` 列出 `artifacts/status/TASK-952.status.json`，但 plan 未把它列在 `## Files Likely Affected`
  - Detection: `python artifacts/scripts/guard_status_validator.py --task-id TASK-952 --artifacts-root artifacts`
  - Mitigation: 將 status artifact 的建立與收尾明確列入 plan scope 與 files list
  - Severity: blocking

## Validation Strategy
- 執行 `python artifacts/scripts/prompt_regression_validator.py --root .`
- 執行 `python artifacts/scripts/run_red_team_suite.py --phase prompt`
- 執行 `python artifacts/scripts/guard_contract_validator.py --root .`
- 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-952 --artifacts-root artifacts`

## Out of Scope
- 變更 prompt contract 本身
- 任何非 prompt-phase 的 red-team runner 行為

## Ready For Coding
yes
# Plan: TASK-900

## Metadata
- Task ID: TASK-900
- Artifact Type: plan
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-11T10:00:00+08:00

## Scope
- 補齊 `TASK-900` 所需的 research / plan / code / verify sample artifacts。
- 確保 smoke task 可同時驗證 artifact guard 與 contract guard。

## Files Likely Affected
- `artifacts/tasks/TASK-900.task.md`
- `artifacts/status/TASK-900.status.json`
- `artifacts/research/TASK-900.research.md`
- `artifacts/plans/TASK-900.plan.md`
- `artifacts/code/TASK-900.code.md`
- `artifacts/verify/TASK-900.verify.md`

## Proposed Changes
- 建立 fact-only research artifact，描述兩支 guard 的邊界。
- 建立 code / verify artifact，將 smoke 驗證流程落地為可讀樣本。
- 更新 `TASK-900.status.json` 到 `done`。

## Risks
- R1
  - Risk: Smoke sample 與實際 bootstrap 規則脫節，導致使用者照文件跑仍失敗
  - Trigger: `BOOTSTRAP_PROMPT.md` 更新了驗證步驟，但 `TASK-900` sample 沒同步
  - Detection: `guard_contract_validator.py` 或 bootstrap 手動重跑失敗
  - Mitigation: 將兩支 guard 都納入 `TASK-900` acceptance criteria 與 verify evidence
  - Severity: blocking
- R2
  - Risk: research sample 違反 fact-only 契約，讓內建樣本自己無法通過新 guard
  - Trigger: 在 research artifact 中加入 Recommendation 或缺少 inline citation
  - Detection: `python artifacts/scripts/guard_status_validator.py --task-id TASK-900`
  - Mitigation: 僅保留事實、來源與 implementation constraints
  - Severity: non-blocking

## Validation Strategy
- 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-900`
- 執行 `python artifacts/scripts/guard_contract_validator.py`

## Out of Scope
- 任意產品程式修改

## Ready For Coding
yes

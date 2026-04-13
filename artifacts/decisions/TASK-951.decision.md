# Decision Log: TASK-951

## Metadata
- Task ID: TASK-951
- Artifact Type: decision
- Owner: Claude
- Status: done
- Last Updated: 2026-04-11T11:10:00+08:00

## Issue
本 live drill 要驗證 blocked 任務不能只靠 decision 或 blocked_reason 恢復，必須先有合法且 `Status: applied` 的 improvement artifact。

## Options Considered
- 只保留 blocked_reason 與 decision，直接假設任務可 resume
- 建立 improvement artifact，但保留 `draft` 或 `approved`
- 停止 resume，直到存在 `Status: applied` 的 improvement artifact，再由 verify evidence 關閉事件

## Chosen Option
停止 resume，直到 improvement artifact 為 `Status: applied`，再由 verify artifact 記錄 blocked / resume 鏈。

## Reasoning
如果只靠 decision 或 blocked_reason 就恢復，會讓 Gate E 失去意義，也無法證明 PDCA 已落地。這個 live drill 的目的就是證明 applied improvement 是 resume 的硬條件，而不是附註。

## Implications
- blocked 與 resume 必須同時出現在 decision、improvement 與 verify evidence 中
- 最終樣本雖然收斂到 `done`，但必須保留完整 Gate E 證據
- `TASK-951` 可直接拿來重跑 status validator

## Follow Up
- 保留 `TASK-951` 作為 blocked / PDCA / resume live drill 樣本
- 若 Gate E 條件再收緊，更新本樣本與 runbook

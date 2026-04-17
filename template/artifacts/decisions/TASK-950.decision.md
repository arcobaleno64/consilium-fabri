# Decision Log: TASK-950

## Metadata
- Task ID: TASK-950
- Artifact Type: decision
- Owner: Claude
- Status: done
- Last Updated: 2026-04-11T11:00:00+08:00

## Issue
本 live drill 模擬兩個角色邊界事件：一是 Gemini research 草稿夾帶 solution design；二是 Codex 提議擴大到未列入 plan 的額外修改。

## Options Considered
- 接受越界內容，直接讓任務往下推進
- 只在對話中口頭修正，不留下 artifact 證據
- 停止推進、記錄 decision，改以 corrected artifacts + verify evidence 收斂

## Chosen Option
停止推進、記錄 decision，並要求最終 artifacts 只保留 fact-only research 與 plan-scoped code 結果。

## Reasoning
若接受越界內容，會讓 research 與 implementation 的責任邊界失真，也無法證明 workflow 真正有能力收斂這類事件。用 decision artifact 固定記錄事件，再由 verify artifact 指向 corrected artifacts，才能證明最終 `done` 狀態不是靠口頭宣告取得。

## Implications
- 最終 research artifact 必須維持 fact-only
- code artifact 只能描述 plan 內的 live drill 產物
- verify evidence 必須同時指向 decision 與 improvement artifact

## Follow Up
- 保留 `TASK-950` 作為 role boundary live drill 樣本
- 若未來新增自動化 diff-to-plan guard，更新 `docs/red_team_backlog.md`

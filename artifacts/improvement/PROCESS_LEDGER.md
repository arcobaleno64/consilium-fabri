# Process Ledger

本檔是冷啟動入口，用來快速回顧最近幾次流程實際做了什麼、哪裡浪費、哪裡容易出錯。

建議閱讀順序：

1. 先看這份 ledger。
2. 再看最近 3 份 `TASK-XXX.improvement.md`。
3. 需要細節時，再回跳對應的 `verify` / `decision` / `status` artifact。

維護規則：

- 每個 task 只寫一行。
- 不貼 raw log，只寫結論與短證據方向。
- `Applied?` 表示對應修正是否已落地為文件、prompt、guard 或 template 變更。

| Date | Task | Outcome | Top Waste | Top Risk | Fix Candidate | Applied? |
|---|---|---|---|---|---|---|
| 2026-04-11 | [TASK-902](TASK-902.improvement.md) | Gate E resume 條件被明文化為 `Status: applied` | improvement 存在但沒有把 applied 視為 hard gate | blocked 任務可能在沒有系統修正時恢復 | 強化 Gate E 規則在 schema / README / Obsidian 的一致性 | yes |
| 2026-04-11 | [TASK-950](TASK-950.improvement.md) | role-boundary live drill 被固定進可重跑流程 | 研究越界與 code-over-plan 只能靠人工串起證據 | 超出 plan 的必要修改仍可能缺乏自動 guard | 將 live drill 與 diff-to-plan 補強列入 runbook / backlog | yes |
| 2026-04-11 | [TASK-951](TASK-951.improvement.md) | blocked resume drill 補齊 PDCA 證據鏈 | 只補 decision 容易被誤當成足夠的 resume 依據 | blocked_reason 與 decision 可能取代 applied improvement | 將 Gate E 演練保留為固定 live drill 樣本 | yes |

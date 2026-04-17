---
applyTo: "**"
---

# 全局指引 — 所有 VS Code 工作區通用

## 核心原則

1. **優先信任文件，不信任記憶**
   - 每次 session 開始，先讀工作區根目錄的入口檔
   - 若存在 `CLAUDE.md`、`docs/orchestration.md`、`.github/copilot-instructions.md`，按此順序讀取

2. **上下文分層**
   - 不要一次載入所有文件
   - 大任務先用 `pack-context.prompt.md` 收斂，再逐步深入

3. **知識庫系統**
   - Repository 知識：`.github/memory-bank/` — 本 repo 的穩定經驗法則
   - 經驗沉澱：`.github/prompts/remember-capture.prompt.md` — 結構化寫入流程
   - 修改前預檢：`.github/prompts/context-review.prompt.md` — 檔案級就緒度分析

4. **任務完成標準**
   - 若需要 artifact，輸出必須符合 schema（見 docs/artifact_schema.md）
   - 若需要程式碼，必須有驗證證據（測試、lint、build log）
   - 若需要文件修改，必須同步相關層（root + template + README）

5. **安全第一**
   - 不要在 prompt 或 memory-bank 寫敏感資訊
   - 任何需要的敏感資訊都應該通過環境變數或安全存儲獲取

6. **執行規則**
   - 可以在目前階段完成後詢問「下一步要做什麼」。
   - 一旦使用者已對下一步提供明確指示，必須將該回答視為正式執行指令，立即繼續完成對應流程，不得再次請求確認。
   - 對於已明確指定的任務，必須持續執行直到該任務所屬的子流程完成後，才可回報結果。
   - 僅在缺少必要資訊且無法合理推定時，才允許提出釐清問題。
   - 不得因禮貌性確認、習慣性追問或不必要的中途回報而中斷執行。
   - 若使用者回覆內容已包含可執行動作、目標或範圍，應直接依該內容續行。

## 禁止項

禁止在 prompt 檔中寫密碼、token、連線字串。
禁止在 memory-bank 寫 API key（改用環境變數或 Vault）。
禁止不經驗證就標記任務完成。

## 工作流觸發

新任務時：讀 `.github/copilot-instructions.md` 加 `CLAUDE.md`。
上下文不足時：用 `pack-context.prompt.md` 或 `.github/memory-bank/*.md`。
任務完成前：確認所有 artifact 符合 schema，驗證證據到位。
經驗沉澱時：用 `remember-capture.prompt.md` 寫入 `.github/memory-bank/`。

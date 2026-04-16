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

3. **記憶體系統**
   - 個人記憶：`/memories/` - 跨 workspace 的長期筆記
   - Session 記憶：`/memories/session/` - 當前對話的臨時記錄
   - Repository 記憶：`/memories/repo/` - 本 repo 的經驗法則

4. **任務完成標準**
   - 若需要 artifact，輸出必須符合 schema（讀 AGENTS.md 的索引表）
   - 若需要代碼，必須有驗證證據（測試、lint、build log）
   - 若需要文件修改，必須同步相關層（root + template + README）

## 禁止項

禁止在 prompt 檔中寫密碼、token、連線字串。  
禁止在 memory 寫 API key（改用環境變數或 Vault）。  
禁止不經驗證就標記任務完成。

## 工作流觸發

新任務時：讀 `.github/copilot-instructions.md` 加 `CLAUDE.md`。  
上下文不足時：用 `pack-context.prompt.md` 或 `memory-bank/*.md`。  
任務完成前：必須執行 `reviewUnstaged` 或 `review` 工具。  
記憶體更新時：使用 `memory` 工具，重點寫進 `/memories/repo/`。

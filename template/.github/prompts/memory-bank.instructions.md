---
applyTo: "**"
---

# Memory Bank — 知識庫管理規範

## 記憶體層級

### `/memories/`（個人跨 workspace 記憶）

用途：工作習慣、常用命令、學習成果  
生命周期：永久  
更新頻率：每個 session 總結後

示例檔案：
- `cli-commands.md` - 常用終端命令
- `debugging-patterns.md` - 除錯心法
- `framework-tips.md` - 框架或語言技巧

### `/memories/session/`（當前 session 記憶）

用途：任務進度、待辦清單、上下文摘要  
生命周期：當前對話結束後自動清空  
更新頻率：每個任務完成後

示例：
- plan.md 本 session 的計畫書
- findings.md 調查結果摘要
- blockers.md 待解決的問題

### `/memories/repo/`（Repository 級經驗）

用途：該 repo 的穩定知識、guard 規則、常見失誤  
生命周期：版本化（與 git 歷史對齐）  
更新頻率：發現新規則或過時時更新

示例檔案：
- `workflow-guards.md` - guard validator 的已知規則
- `build-gotchas.md` - 本 repo 的構建陷阱
- `integration-notes.md` - 與外部系統的集成點

## 寫法規範

簡潔：單行事實或短列表，避免長段落  
引用：每條事實附註來源（檔案名:行號 或 commit hash）  
版本化：若 memory 涉及某個 artifact 或 script，註明版本  
隱私：絕不寫密碼、token、個人資訊

## 何時更新

不要在 session 進行中頻繁更新（會干擾當前工作）  
session 完成後，提煉重點寫入  
發現新的 pattern 或 gotcha 時立即記錄  
月度複查：刪除過時、合併重複、更正錯誤

## 查詢方式

```
memory view /memories/repo/workflow-guards.md
memory view /memories/session/
memory view /memories/
```

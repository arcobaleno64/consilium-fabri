# Memory Bank — 知識庫檔案索引

本目錄存儲本 repository 的穩定知識和經驗法則。

## 檔案清單

| 檔案 | 用途 | 更新頻率 |
|---|---|---|
| `artifact-rules.md` | Artifact schema 的已知規則和例外 | 月度 |
| `workflow-gates.md` | Guard validator 的觸發條件與回避方式 | 雙周 |
| `prompt-patterns.md` | 本 repo 的 prompt 寫作範式 | 月度 |
| `project-facts.md` | 項目特有的技術棧、集成點、部署約定 | 改變時 |

## 寫法規範

簡潔第一：1-2 句事實，避免囉唆  
版本化：若涉及特定腳本版本或 artifact 版本，註明  
引用：指向原始檔案或 commit  
私密性：絕不存儲憑證或敏感資訊

## 使用方式

檢視 repo 級記憶：
memory view /memories/repo/

檢視特定檔案：
memory view /memories/repo/artifact-rules.md

## 維護

每個 session 完成後複查  
發現新規則立即記錄  
季度深度複查（刪除過時、更正錯誤）

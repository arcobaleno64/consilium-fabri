---
applyTo: "**"
---

# Remember Capture — 經驗沉澱流程

## 何時用

任務完成後（Closure 階段），發現可重用的教訓、踩雷、命名規則、操作模式時。
也適用於 blocked 狀態解除後，把排障經驗提煉為長期知識。

不適用於：短期進度（寫入 activeContext.md 或 tasks/）、一次性排障紀錄、臨時性機敏資料。

## 流程

### Step 1 — 分類

判斷這條知識屬於哪個 domain：

| Domain | 目標檔案 | 適用內容 |
|---|---|---|
| artifact-rule | `.github/memory-bank/artifact-rules.md` | Artifact schema 的已知規則、guard 觸發點、例外處理 |
| workflow-gate | `.github/memory-bank/workflow-gates.md` | 狀態轉換條件、gate 回避方式、升級觸發 |
| prompt-pattern | `.github/memory-bank/prompt-patterns.md` | Agent dispatch 範式、輸出格式、常見錯誤 |
| project-fact | `.github/memory-bank/project-facts.md` | 技術棧、集成點、環境變數、構建約定 |
| not-long-term | 不寫入 memory-bank | 短期進度、臨時排障、單次任務細節 |

若分類不確定，標示「需人工確認」並停止寫入。

### Step 2 — 查重

在目標檔案中搜尋關鍵詞，確認無重複。
若已存在相近內容，改為更新既有條目而非新增。

### Step 3 — 膨脹檢查

若目標檔案超過 80 行，先提出整併建議再追加。
整併方向：合併重複、刪除過時、壓縮冗餘描述。

### Step 4 — 撰寫

格式要求：
- 單行事實或短列表（1-2 句）
- 附來源引用：`file:line` 或 `commit hash`
- 若涉及特定版本，註明版本號
- 使用繁體中文（臺灣），技術名詞保留英文

範例：
```
Guard validator 在 plan artifact 缺少 R3 (Detection) 欄位時只 WARN 不 BLOCK，需人工補齊
— artifacts/scripts/guard_status_validator.py:142, TASK-955
```

### Step 5 — 安全檢查

寫入前逐項確認：
- 不含密碼、token、cookie、私鑰
- 不含個資或未公開 URL
- 不含暫時性排障資料（改寫入 session memory）
- 來源引用指向可公開的檔案或 commit

## 輸出格式

```
## Remember Capture

Domain: [artifact-rule | workflow-gate | prompt-pattern | project-fact | not-long-term]
Target: [目標檔案路徑]
Duplicate Check: [無重複 | 更新既有條目 at line X]
Line Count: [目標檔案當前行數] / 80
Action: [追加 | 更新 | 先整併再追加 | 不寫入]

### Content

[實際內容草案]

### Source

[來源引用]
```

## 不寫入的情況

若判定為 not-long-term，輸出原因並建議替代落點：
- 短期進度 → `memory-bank/activeContext.md` 或 `artifacts/tasks/`
- 單次排障 → session memory
- 決策紀錄 → `.decision.md` artifact

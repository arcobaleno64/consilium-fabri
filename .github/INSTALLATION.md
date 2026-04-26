## 最小可行上下文系統 — 完整安裝指南

### 已實施清單

- `.github/copilot-instructions.md`（全局穩定規則）
- `.github/prompts/memory-bank.instructions.md`（記憶體管理規範）
- `.github/prompts/pack-context.prompt.md`（上下文收斂工具）
- `.github/prompts/context-review.prompt.md`（修改前預檢）
- `.github/prompts/remember-capture.prompt.md`（經驗沉澱流程）
- `.github/skills/`（可選任務導向 skill，不作為強制 lifecycle hook）
- `.github/memory-bank/`（5 個參考檔 + README，知識庫）
- `CLAUDE.md` 最佳化（從 2600 行減至 168 行）

---

### 立即執行的步驟

#### Step 1: 重新載入 VS Code

```
Windows: Ctrl+Shift+P，輸入 "Developer: Reload Window"
Mac: Cmd+Shift+P，輸入 "Developer: Reload Window"
```

VS Code 會掃描 `.github/copilot-instructions.md` 並將其載入。

#### Step 2: 測試新指令是否生效

在 Copilot Chat 中嘗試：

```
Q: "read /memories/repo/artifact-rules.md"

預期回應：顯示 artifact 觸發點規則
```

```
Q: "我要開始 TASK-950。請用 pack-context 幫我整理上下文。"

預期回應：生成 Context Pack（含目標、依賴、檢查清單）
```

```
Q: "What are the workflow gates?"

預期回應：引用 .github/memory-bank/workflow-gates.md
```

#### Step 3: 版控提交

```bash
git add .github/
git add CLAUDE.md
git add validate_mvp_context.py

git commit -m "chore: setup MVP context system with layered instructions + memory-bank

- New: .github/copilot-instructions.md (global rules)
- New: .github/prompts/ (4 optional prompt files)
- New: .github/skills/ (optional task-specific skill metadata)
- New: .github/memory-bank/ (5 reference docs)
- Refactor: CLAUDE.md optimized (2600 lines reduced to 168 lines)
- New: validate_mvp_context.py (structure validator)

Reduces instruction bloat by 94% while maintaining all critical rules via cross-references and memory-bank delegation."

git push
```

---

### 使用指南

#### 查詢工作流規則

不要在 CLAUDE.md 翻找 2600 行，改為詢問 Copilot：

```
"顯示 artifact-rules.md 中的 code artifact 要求"
"guard validator 在什麼時候會 block scope-drift?"
"lightweight task 的標準是什麼?"
```

Copilot 將自動從 `.github/memory-bank/` 找到答案。

#### 當你開始大任務

1. 詢問：`"我要做 TASK-XXX。先用 pack-context 幫我整理。"`
2. 根據生成的 Context Pack 執行以下檢查：
   檢查依賴是否滿足  
   確認所有 artifacts 到位  
   識別 premortem 風險  
   整理進入點
3. 繼續執行

#### 任務完成時

完成回報應聚焦於：
- 工作內容摘要
- 已執行的驗證與結果
- 剩餘風險或 TODO

`.github/prompts/` 與 `.github/skills/` 僅作為可選任務能力，不作為強制 completion hook。若需要下一步，由使用者明確指定。

---

### 故障排查

#### Q: Copilot 說「找不到記憶體檔案」

**A**: 確認檔案存在

```bash
ls -la .github/memory-bank/
```

若缺失，重新執行以下命令：
```bash
python validate_mvp_context.py
```

#### Q: `.github/copilot-instructions.md` 不被讀取

**A**: 檢查 VS Code 設定

```json
// settings.json
{
  "copilot.chat.instructionPath": ".github/copilot-instructions.md"
}
```

若仍無效，Fallback 至本地 prompts：
```bash
# 複製到 VS Code 用戶目錄
cp .github/copilot-instructions.md \
  ~/.config/Code/User/prompts/copilot-instructions.md  # Linux/Mac

# Windows: %APPDATA%\Code\User\prompts\
```

### 核心概念複習

| 概念 | 存儲位置 | 用途 |
|---|---|---|
| 全局規則 | .github/copilot-instructions.md | 每個 session 啟動時 |
| Artifact 規則 | .github/memory-bank/artifact-rules.md | 寫任何 artifact 前 |
| Guard 規則 | .github/memory-bank/workflow-gates.md | 進入任何 gate 前 |
| Prompt 範式 | .github/memory-bank/prompt-patterns.md | 派發 agent 前 |
| 技術棧 | .github/memory-bank/project-facts.md | 設定環境變數時 |
| 上下文收斂 | .github/prompts/pack-context.prompt.md | 大任務前 |
| 修改前預檢 | .github/prompts/context-review.prompt.md | 修改前 |
| 經驗沉澱 | .github/prompts/remember-capture.prompt.md | 記錄新規則時 |

---

### 成效檢查

完成 3-5 個任務後，評估：

- [ ] CLAUDE.md 讀取頻率是否下降？
- [ ] 是否有在用 pack-context？
- [ ] 是否在詢問 memory-bank？
- [ ] prompts / skills 是否仍維持 task-specific，而非強制 hook？

若有問題或發現新規則，立即更新 `.github/memory-bank/`（無需改 CLAUDE.md）。

---

### 提問與反饋

建議的改進點：
1. 若 memory-bank 檔案過期 → 更新對應檔案
2. 若 guard 規則有新觸發點 → 補充 workflow-gates.md
3. 若 prompt 失效 → 改進 prompt-patterns.md

所有改進都在 memory-bank 層完成，無需觸動 CLAUDE.md 核心。

---

**總結**：

新系統的優勢是「**模塊化 + 按需載入**」。你不再依賴一份 2600 行的龐大指令檔，取而代之是一份 168 行的核心指南 + 多份專用參考檔。工作流更新可以直接改 memory-bank，無需動核心指令。

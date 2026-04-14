# Bootstrap Prompt — 新專案開局範本

> 將以下內容複製到新的 Claude Code 對話串的第一則訊息。
> 用你的專案資訊替換 `【...】` 區塊後送出。

---

```
我要使用 artifact-first multi-agent workflow 開始一個新專案。

## 1. 專案資訊

- 專案名稱：【填入專案名稱，例如 MyApp】
- 專案根目錄：【填入絕對路徑，例如 C:\Users\me\Projects\MyApp】
- 專案簡述：【一句話描述專案目的】
- 主要語言/框架：【例如 C# / .NET 8 / UWP、Python / FastAPI、TypeScript / Next.js】
- 版控：Git（已初始化 / 尚未初始化）

## 2. 上游 Fork 模式（若無 fork 可刪除此段）

- Upstream repo：【例如 github.com/original-author/repo-name】
- 我的 fork：【例如 github.com/myuser/repo-name】
- GitHub CLI 帳號：【例如 myuser】

## 3. 範本來源

Workflow template 位於：【填入 artifact-harness repo clone 路徑，或直接在專案目錄中 clone】
請從該目錄複製完整架構到專案根目錄，然後：
1. 替換 CLAUDE.md 中的 placeholder（{{PROJECT_NAME}}, {{REPO_NAME}}, {{UPSTREAM_ORG}}）
2. 若無 fork 模式，移除 CLAUDE.md 的 "Repository boundaries" 區段
3. 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-900` 確認 [OK]
4. 執行 `python artifacts/scripts/guard_contract_validator.py` 確認 root / template / Obsidian 未漂移
5. 執行 `python artifacts/scripts/prompt_regression_validator.py --root .` 確認 Prompt regression 測例通過
6. 若要做完整流程壓力測試，可再執行 `python artifacts/scripts/run_red_team_suite.py --phase all`

## 4. Agent 配置

- Orchestrator：Claude Code（你）
- Research agent：Gemini CLI
  - 模型：gemini-3.1-flash-lite-preview（預設），有問題時可升級至 gemini-3-flash-preview，若仍無法解決則動用 gemini-3.1-pro-preview
  - API Key 環境變數：GEMINI_API_KEY
  - 呼叫方式：GEMINI_API_KEY="<key>" gemini -m gemini-3.1-flash-lite-preview --approval-mode=yolo -p "<prompt>"
  - 入口檔：GEMINI.md（品質硬規則已內嵌，不需額外載入）
- Implementation agent：Codex CLI（或 Claude 自行實作，視任務規模）
  - 模型：gpt-5.4（預設），有問題時可降級至 gpt-5.3-codex，若仍無法解決則動用 gpt-5.4-mini
  - 呼叫方式：codex -m gpt-5.4 --approval-mode full-auto -p "<prompt>"
  - 入口檔：CODEX.md

## 5. 工作規範

- 遵循 CLAUDE.md 的所有規則（artifact-first、gate-guarded、premortem）
- 文件按需載入：參考 AGENTS.md 的階段載入矩陣，不要一次讀完所有 docs/
- 每個 task 必須走完 Intake → Research → Planning → Coding → Verification 流程
- Research 外包 Gemini CLI 時，dispatch prompt 必須包含 GEMINI.md 的品質規則
- 進入 coding 前必須完成 premortem 分析（docs/premortem_rules.md）
- 完成後必須有 verify artifact 含 Build Guarantee
- 任何 workflow 規則變更都必須同步更新 `OBSIDIAN.md` 與 `template/OBSIDIAN.md`
- 紅隊演練入口固定為 `docs/red_team_runbook.md`，重跑命令固定為 `python artifacts/scripts/run_red_team_suite.py`
- Prompt regression 固定命令為 `python artifacts/scripts/prompt_regression_validator.py --root .`
- 長期維護 Markdown 以繁體中文（臺灣）為主；命令、路徑、環境變數、schema literal 與 placeholder 保持英文

## 6. 第一個任務

【描述你的第一個任務，例如：】
TASK-001：【任務目標】
- 背景：【為什麼要做這件事】
- 預期產出：【具體要改什麼 / 做什麼】
- 驗收條件：【怎樣算完成】

請先執行 Intake（讀範本、建立 task artifact 和 status artifact），然後按流程推進。
```

---

## 使用說明

### 最小版（無 fork、無 Gemini）

如果專案不需要 fork 模式也不需要 Gemini，可以精簡為：

```
我要使用 artifact-first workflow 開始新專案。

專案：【名稱】，位於 【路徑】，使用 【語言/框架】。

範本來源：【填入 artifact-harness repo clone 路徑，或直接在專案目錄中 clone】
請複製範本到專案、移除 CLAUDE.md 的 fork 區段、驗證 TASK-900，並執行 contract guard。

第一個任務：【描述】
```

### 注意事項

1. **範本路徑**：若 template 已搬移到其他位置，更新路徑即可。
2. **Gemini API Key**：不要寫死在 prompt 裡。建議用環境變數或在 session 中單獨設定。
3. **第一個任務**：建議從一個小任務開始（例如 TASK-001: 確認 build 正常），驗證整個流程跑得通後再做大任務。
4. **Lightweight mode**：極小型任務可在 prompt 中加「此為 lightweight task」，跳過 research 階段。

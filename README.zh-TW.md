<div align="center">

# Consilium Fabri

<p>
  一套面向實務開發的多 Agent AI 協作工作流框架，強調 artifact-first、gate-guarded 與可驗證交付。
</p>

<p>
  <img src="https://img.shields.io/badge/Workflow-Multi--Agent-111111?style=flat-square" alt="Multi-Agent Workflow" />
  <img src="https://img.shields.io/badge/Architecture-Artifact--First-0A66C2?style=flat-square" alt="Artifact First" />
  <img src="https://img.shields.io/badge/Validation-Gate--Guarded-8A2BE2?style=flat-square" alt="Gate Guarded" />
  <img src="https://img.shields.io/badge/Agents-Claude%20Code%20%7C%20Gemini%20CLI%20%7C%20Codex%20CLI-2F855A?style=flat-square" alt="Agents" />
  <img src="https://img.shields.io/badge/Python-Validator-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python Validator" />
</p>

<p>
  讓 AI 開發流程從零散對話，變成可追蹤、可交接、可驗證的工程化交付機制。
</p>

繁體中文 | **[English](README.md)**

</div>

---

## 產品定位

Consilium Fabri 是一套可嵌入專案儲存庫的多 Agent AI 工作流框架，設計目標不是單純「叫模型幫你寫程式」，而是建立一條有邊界、有檢查點、有產物紀錄的開發流程。

它特別適合以下需求：

- 希望在 AI 協作下仍保有工程紀律
- 需要把研究、規劃、實作、驗證拆分成明確階段
- 不希望所有關鍵決策都藏在聊天上下文裡
- 想降低 AI 產出不可追溯、不可審核、不可重現的風險
- 想把多 Agent 協作導入既有專案，而不是另起一套平台

它不是聊天腳本集合，也不是單一代理人的 prompt 範本，而是一個偏工程治理導向的 workflow harness。

---

## 為什麼是這個專案

多 Agent 開發常見的問題很一致：

- 研究結果沒有固定落點，之後無法回查
- 計畫與實作脫鉤，最後誰改了什麼說不清楚
- 驗證只停留在口頭聲明，沒有足夠證據
- Agent 角色重疊，導致任務邊界混亂
- 每次都把整包文件塞進上下文，成本高又不穩定

Consilium Fabri 的核心價值，在於把這些常見失控點收斂成一套有狀態、有產物、有 gate 的工作流。

---

## 核心能力

<table>
  <tr>
    <td width="33%" valign="top">
      <h3>多 Agent 協作</h3>
      <p>透過 Claude Code、Gemini CLI、Codex CLI 的角色分工，讓研究、協調、實作各自聚焦，降低責任漂移與上下文混亂。</p>
    </td>
    <td width="33%" valign="top">
      <h3>Artifact First</h3>
      <p>所有任務以 task、research、plan、code、verify、decision、status 等產物為核心，不依賴隱性對話記憶，提升可追蹤性與可審核性。</p>
    </td>
    <td width="33%" valign="top">
      <h3>Gate 驗證</h3>
      <p>透過 workflow gate 與 validator 控制合法狀態轉換、必要產物與驗證要求，避免任務在未準備完成前直接跳到實作或結案。</p>
    </td>
  </tr>
</table>

---

## 產品特色

### 1. 面向實務開發的角色分工
- Claude Code 作為主協調者與流程驅動核心
- Gemini CLI 負責研究與資訊整理
- Codex CLI 負責實作與交付
- 透過明確責任切分，降低多代理人互相覆蓋的風險

### 2. 嚴格的 gate-guarded workflow
- 任務流程依序經過 Intake、Research、Planning、Coding、Verification、Done
- 各階段都有明確前置條件
- 不允許任意跳過必要步驟
- 有助於建立穩定、可複查的交付節奏

### 3. 可審核的 artifact-first 設計
- 研究結果不是口頭摘要，而是可回查的 research artifact
- 實作前需有 plan artifact
- 驗證後需有 verify artifact
- 決策可寫入 decision artifact
- 狀態以 machine-readable status 管理

### 4. 驗證不是口號，而是機制
- 內建 `guard_status_validator.py`
- 內建 `guard_contract_validator.py`
- 可檢查狀態轉換是否合法
- 可檢查必要產物、metadata 與 research / PDCA 契約
- 可檢查 root / `template/` / Obsidian 入口是否規則漂移
- 可降低「看起來完成，其實沒驗證」的風險

### 5. 更節制的上下文載入策略
- 不要求每個 agent 每次都讀完整套文件
- 依任務階段與角色載入必要內容
- 降低 token 消耗
- 降低 prompt 汙染與不穩定行為

### 6. 文件與時間戳規範
- 長期維護的 Markdown 以繁體中文（臺灣）為主，必要例外再用英文
- 命令、路徑、placeholder、schema literal 與狀態值保留英文
- 紀錄時間與 `Last Updated` 一律使用 `Asia/Taipei`，採 ISO 8601 並帶 `+08:00`
- root 文件、`template/` 文件與 Obsidian 入口必須保持語義一致

### 7. Guard 邊界清楚
- `guard_status_validator.py` 專責 task / artifact / state 驗證
- plan/code scope drift 現在預設為 hard fail（僅在受控例外下使用 `--allow-scope-drift`）
- `guard_contract_validator.py` 專責 workflow 文件、bootstrap、template 與 Obsidian 同步契約
- `CLAUDE.md` / `GEMINI.md` / `CODEX.md` 有變更時，必須同步更新 prompt regression cases
- workflow 規則變更若未同步 README / template / Obsidian，視為未完成

### 8. 內建紅隊演練
- `docs/red_team_runbook.md` 提供靜態攻擊、live drill 與復盤流程
- `docs/red_team_scorecard.md` 提供案例評分矩陣
- `docs/red_team_backlog.md` 記錄演練後續補強項
- `python artifacts/scripts/run_red_team_suite.py --phase all` 可重跑內建紅隊案例與 live drill 樣本
- `python artifacts/scripts/prompt_regression_validator.py --root .` 可執行 `CLAUDE.md`、`GEMINI.md`、`CODEX.md` 的固定 Prompt regression 測例
- `python artifacts/scripts/run_red_team_suite.py --phase prompt` 可透過同一套報表流程執行 Prompt regression

---

## 適用情境

這個專案特別適合以下使用方式：

| 情境 | 說明 |
|---|---|
| 個人 AI 開發框架 | 單人開發者也能用工程化方式管理 AI 協作 |
| 小型團隊協作 | 在不導入大型平台的前提下建立可控流程 |
| 可追蹤的 AI 交付 | 保留研究、規劃、實作、驗證的完整痕跡 |
| 既有專案導入 | 可作為現有 repo 的 workflow layer 使用 |
| 開源專案展示 | 展示你對 AI-assisted engineering 的方法論與實作紀律 |

---

## 工作流總覽

```text
Intake
  |
  v
Research
  |
  v
Planning
  |
  v
Coding
  |
  v
Verification
  |
  v
Done
```

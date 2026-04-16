# Repo 結構與工作流成熟度評估

## 評估範圍

本報告根據目前 repo 內可見結構與代表性文件進行靜態評估，主要依據如下：

- `README.md`、`README.zh-TW.md`
- `AGENTS.md`、`BOOTSTRAP_PROMPT.md`、`OBSIDIAN.md`
- `docs/orchestration.md`
- `docs/artifact_schema.md`
- `docs/workflow_state_machine.md`
- `docs/subagent_roles.md`
- `docs/lightweight_mode_rules.md`
- `docs/subagent_task_templates.md`
- `.github/workflows/workflow-guards.yml`
- `artifacts/scripts/guard_status_validator.py`
- `artifacts/scripts/guard_contract_validator.py`
- `artifacts/red_team/latest_report.md`
- 代表性 task artifacts：`TASK-961` 系列
- 目前 git worktree 狀態與目錄分布

## 一、Repo 結構概覽

此 repo 不是以應用程式原始碼為中心，而是以 workflow framework 與 governance artifacts 為中心。

| 區塊 | 主要內容 | 角色 |
|---|---|---|
| 根目錄 | `README*`、`AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、`CODEX.md`、`BOOTSTRAP_PROMPT.md`、`OBSIDIAN.md` | 專案入口、agent 入口、bootstrap 指引 |
| `docs/` | orchestration、schema、state machine、premortem、red team、lightweight mode | 流程規範與制度文件 |
| `docs/templates/` | `implementer/`、`tester/`、`verifier/`、`reviewer/`、`parallel/`、`blocking/` | subagent 任務模板 |
| `artifacts/` | `tasks/`、`research/`、`plans/`、`code/`、`verify/`、`status/`、`decisions/`、`improvement/`、`scripts/` | 流程執行痕跡與自動化腳本 |
| `.github/` | workflow、agents、repository profile | CI 與 GitHub 展示層 |
| `template/` | 幾乎完整鏡像 root 結構 | 新專案 bootstrap 範本 |
| `.obsidian/` | vault 設定 | 文件工作區整合 |
| `external/`、暫存目錄 | 外部內容與測試/演練殘留 | 非核心但會影響工作樹衛生 |

從結構上看，repo 已明確區分出三個層次：

1. 規則層：`docs/`、`AGENTS.md`、各 agent 入口檔。
2. 執行層：`artifacts/` 與 validator / red-team scripts。
3. 發佈層：`README*`、`.github/`、`template/`、`OBSIDIAN.md`。

這種分層清楚，對「可審核」、「可移植」、「可 bootstrap 到新 repo」很有幫助。

## 二、工作流機制盤點

目前 repo 內的工作流能力不是只有文件宣告，而是已經有相當程度的落地。

| 能力 | 證據 | 評語 |
|---|---|---|
| Artifact-first | `docs/orchestration.md`、`docs/artifact_schema.md`、`artifacts/*` | 核心設計完整，且已有多個實際 task 留痕 |
| 狀態機管理 | `docs/workflow_state_machine.md` | 狀態與轉移規則明確，非法跳轉有明文禁止 |
| 角色分工 | `docs/subagent_roles.md`、`CLAUDE.md`、`GEMINI.md`、`CODEX.md` | 主控、研究、實作責任切分清楚 |
| Gate 驗證 | `guard_status_validator.py` | 不只是 soft guideline，而是可自動檢查 |
| Contract drift 防護 | `guard_contract_validator.py` | root / template / Obsidian / README 同步有機制保護 |
| Prompt regression | `.github/workflows/workflow-guards.yml`、對應 validator | 顯示 repo 已把 prompt 視為可回歸測試的資產 |
| Red-team | `docs/red_team_runbook.md`、`artifacts/red_team/latest_report.md` | 有演練機制，不只停在靜態規則 |
| Lightweight mode | `docs/lightweight_mode_rules.md` | 顯示流程已開始考慮效率與治理平衡 |
| Template discovery | `artifacts/scripts/discover_templates.py`、`docs/templates/` | 顯示系統已從人工引用模板走向可發現化 |

代表性 artifact `TASK-961` 也顯示這套流程確實被實際使用：有 task、research、plan、code、verify、status，且 verify 會逐條對 acceptance criteria 驗收，這表示流程不是紙上制度。

## 三、成熟度評估

本報告以 5 級制評估：

- Level 1: Initial
- Level 2: Repeatable
- Level 3: Defined
- Level 4: Managed
- Level 5: Optimizing

### 3.1 Repo 結構成熟度

| 維度 | 評分 | 判斷 |
|---|---:|---|
| 目錄分層 | 4/5 | 規則、執行、模板、發佈層分離清楚 |
| 文件入口清晰度 | 4/5 | README、AGENTS、BOOTSTRAP、OBSIDIAN 分工明確 |
| 範本化程度 | 5/5 | `template/` 幾乎完整鏡像，可直接作為 scaffold |
| 可發現性 | 4/5 | 關鍵入口集中，但文件量已偏多，需依賴載入矩陣導航 |
| 工作樹衛生 | 2/5 | 暫存目錄、red-team 工作目錄與未忽略檔案讓 worktree 噪音偏高 |

Repo 結構整體評級：**Level 4 / Managed（接近 Level 5）**。

原因是核心結構已高度模組化，且支援 bootstrap 與同步驗證；但工作樹衛生與維運負擔仍未完全收斂。

### 3.2 工作流成熟度

| 維度 | 評分 | 判斷 |
|---|---:|---|
| 流程定義完整度 | 5/5 | Intake 到 Closure、blocked 與 Gate E 都有制度 |
| Artifact schema 完整度 | 5/5 | artifact 類型、欄位、狀態與最低品質要求完整 |
| 自動化驗證 | 4/5 | status guard、contract guard、prompt regression、red-team 均已存在 |
| 實際採用程度 | 4/5 | 已累積多個 TASK artifacts，代表流程被反覆使用 |
| CI 整合廣度 | 3/5 | CI 已接上 guard，但 status guard 目前只檢查少數指定 task |
| 治理閉環能力 | 4/5 | blocked -> improvement -> resume 的 PDCA 概念成熟 |
| 持續優化能力 | 4/5 | 有 red-team/backlog/prompt regression，但尚未看到更全面的 repo health dashboard |

工作流整體評級：**Level 4 / Managed**。

這表示 repo 已超過「有文件規範」的階段，進入「有制度、有驗證、有歷史痕跡、有回歸機制」的成熟狀態；但仍未完全達到 Level 5，因為自動化覆蓋範圍與營運衛生還有明顯提升空間。

## 四、主要優勢

1. **制度完整且分層合理**

`orchestration`、`artifact schema`、`state machine`、`subagent roles` 各自負責不同層次，沒有全部塞進單一大文件。

2. **規範已被程式化**

`guard_status_validator.py` 與 `guard_contract_validator.py` 代表核心規則已從文件走向執行，這是成熟工作流與一般 prompt pack 的主要差異。

3. **Template 與 root 同步有護欄**

`template/` 作為 bootstrap scaffold 很完整，而 contract guard 又能檢查 drift，降低模板老化風險。

4. **重視失敗演練，而不只正向流程**

內建 red-team runbook、scorecard、backlog，表示系統有意識地驗證失敗模式，而非只展示 happy path。

5. **已有真實運作痕跡**

`artifacts/` 下存在多個 task 家族，且不是只有 task/status，還包含 research、plan、code、verify、decision、improvement，顯示流程曾被完整跑過。

## 五、主要風險與缺口

1. **CI 驗證覆蓋仍偏樣板化**

`.github/workflows/workflow-guards.yml` 目前只對 `TASK-900`、`TASK-950`、`TASK-951` 執行 status guard。這能驗證機制存在，但還不是對整個 repo 狀態的通用治理。

2. **工作樹衛生不足**

目前 worktree 有大量未追蹤與已修改檔案，且 `git status` 對 `.tmp-red-team/`、`.codex-red-team/`、暫存目錄出現 permission warning。`.gitignore` 也尚未忽略這些工作流測試或暫存輸出，容易讓 repo 日常操作變吵。

3. **文件存在局部一致性風險**

`BOOTSTRAP_PROMPT.md` 仍以 `GEMINI_API_KEY` 為操作示例，但 `docs/subagent_roles.md` 對 Gemini CLI 的說明已轉為 CLI OAuth 登入模式。這類 onboarding 差異不會立即破壞流程，但會降低新使用者信任感。

4. **Template 完整鏡像的維護成本高**

`template/` 幾乎複製整個 root，對 bootstrap 很有利，但任何流程級修改都需要同步兩份以上內容。雖然已有 contract guard 緩解，維運成本仍然偏高。

5. **治理指標仍以文件與單次驗證為主**

repo 已有 `kpi_sprint2.json`，但尚未看到一個統一的 repo health 視角，例如：哪些 task 缺 verify、哪些 status 過期、哪些 blocked 超時、哪些 template 尚未被使用。這讓成熟度已經到達「Managed」，但尚未完全進入「Optimizing」。

## 六、整體判斷

### 總結評級

- Repo 結構成熟度：**4/5**
- 工作流成熟度：**4/5**
- 綜合評估：**Level 4 / Managed**

### 判斷摘要

這個 repo 已經具備一個成熟 workflow framework 的大部分關鍵特徵：

- 結構清楚
- 規範完整
- 角色邊界明確
- artifacts 可追溯
- validators 可執行
- CI 已接入
- red-team 與 prompt regression 已存在

它的主要短板不是「缺制度」，而是「制度已很完整，但操作層與全面自動化還可再收斂」。

換句話說，這不是早期原型，而是**已具備對外展示與內部實戰價值的中高成熟度 workflow repo**。

## 七、建議優先事項

1. 將 status guard 從固定 task-id 改成自動掃描或 matrix 化，提升 CI 治理覆蓋。
2. 補強 `.gitignore`，納入 red-team sandbox、暫存工作目錄與明確的本地輸出，降低 worktree 噪音。
3. 對齊 `BOOTSTRAP_PROMPT.md` 與 `docs/subagent_roles.md` 的 Gemini/Codex 認證與呼叫指引。
4. 增加一個 repo health summary 腳本，統計 task coverage、stale status、missing verify、blocked aging 等指標。
5. 若 `template/` 長期維持完整鏡像，建議再補一層「同步責任邊界」說明，明確哪些檔案必須 exact sync、哪些允許 placeholder 泛化。

---

## 八、Code Review：代碼品質、安全性與可維護性

### 8.0 總覽

本次 code review 涵蓋 `artifacts/scripts/` 下的所有 Python 與 PowerShell 腳本。

| 腳本 | 行數（約） | 角色 |
|---|---:|---|
| `guard_status_validator.py` | ~1850 | 核心：artifact / state / scope drift / premortem / Gate E 驗證 |
| `guard_contract_validator.py` | ~250 | root ↔ template 同步守護 |
| `run_red_team_suite.py` | ~800+ | 23 static + 2 live + 20 prompt 紅隊演練 |
| `prompt_regression_validator.py` | ~180 | prompt 回歸測試引擎 |
| `build_decision_registry.py` | ~250 | decision artifact → JSON registry |
| `aggregate_red_team_scorecard.py` | ~110 | red-team report → 計分卡 |
| `discover_templates.py` | ~100 | subagent 範本發現 |
| `update_repository_profile.py` | ~90 | `.github/repository-profile.json` 管理 |
| `validate_scorecard_deltas.py` | ~90 | reviewer delta 驗證 |
| `Invoke-CodexAgent.ps1` | ~120 | Codex CLI resilient wrapper |
| `Invoke-GeminiAgent.ps1` | ~120 | Gemini CLI resilient wrapper |
| `load_env.ps1` | ~12 | `.env` 載入 |

### 8.1 代碼品質

#### 優點

1. **結構清晰，職責分離**
   - 每支腳本都有明確的單一職責，沒有 god script。
   - `guard_status_validator.py` 雖然最長（~1850 行），但內部以 `validate_*`、`detect_*`、`parse_*` 系列函式組織，可讀性仍在合理範圍。

2. **型別標註完整**
   - 所有 Python 腳本均使用 `from __future__ import annotations` 與 `typing` 模組。
   - 資料結構以 `@dataclass` 定義，語義清楚。

3. **常數集中管理**
   - 狀態機規則（`LEGAL_TRANSITIONS`、`STATE_REQUIRED_ARTIFACTS`）、artifact marker（`MARKERS`）、premortem 規則等全部以常數表定義在檔案頂部，便於審查與維護。

4. **錯誤處理一致**
   - 統一使用 `GuardError` exception 與 `ValidationResult(errors, warnings)` 模式。
   - CLI exit code 嚴格區分：0 = pass、1 = fail、2 = usage error。

5. **PowerShell wrapper 設計合理**
   - `Invoke-CodexAgent.ps1` 與 `Invoke-GeminiAgent.ps1` 實作了 exponential backoff + model fallback 的多層韌性機制。

#### 可改進項目

| # | 類別 | 位置 | 說明 | 嚴重度 |
|---|---|---|---|---|
| Q1 | 複雜度 | `guard_status_validator.py` | 單檔約 1850 行。函式拆分尚可，但 `validate_artifact_presence()` 與 `detect_historical_diff_scope_drift()` 已偏長（各 ~80 行），可考慮拆成更小的子函式。 | Low |
| Q2 | 重複定義 | `guard_contract_validator.py` + `update_repository_profile.py` | `REQUIRED_TOPICS` 與 `TOPIC_PATTERN` 在兩個檔案中重複定義。如果新增必要 topic，需要同步改兩處。 | Medium |
| Q3 | 重複函式 | `guard_status_validator.py` + `run_red_team_suite.py` | `compute_snapshot_sha256()` 在兩個檔案中都有定義，簽章略有不同（一個接受 `Set[str]`，一個接受 `Sequence[str]`）。 | Low |
| Q4 | 硬編碼 | `run_red_team_suite.py` | `blocked_sample_source()` 硬編碼檢查 `TASK-902` / `TASK-901`，未來新增或移除 sample task 時容易遺漏。 | Low |
| Q5 | 缺少單元測試 | 全局 | 目前只有 red-team suite 作為 integration test。核心函式（`parse_key_value_section`、`extract_file_tokens`、`normalize_path_token` 等）缺少獨立的 unit test。 | Medium |

### 8.2 安全性

#### 優點

1. **GitHub API 呼叫安全**
   - `collect_github_pr_files()` 使用 `urllib.parse.quote()` 做 URL 編碼，避免 injection。
   - token 從環境變數讀取（`GITHUB_TOKEN` / `GH_TOKEN`），不硬編碼。
   - API 版本 header 明確指定，降低不可預期行為。

2. **路徑穿越防護**
   - `resolve_workspace_relative_path()` 明確檢查路徑不得以 `/`、`..` 開頭，且 resolve 後的路徑必須在 repo root 內（`relative_to()` 驗證）。

3. **JSON 解析安全**
   - 所有 `json.loads()` 呼叫都有 `try/except json.JSONDecodeError` 處理。

4. **沒有 shell injection 風險**
   - `subprocess.run()` 均使用 list 形式傳參，不走 `shell=True`。

#### 風險項目

| # | 類別 | 位置 | 說明 | 嚴重度 |
|---|---|---|---|---|
| S1 | 敏感資訊洩漏 | `load_env.ps1` | `.env` 載入後使用 `Write-Host "Loaded: $varName"` 輸出變數名稱。雖然只輸出 key 不輸出 value，但在 CI log 中仍可能洩漏內部環境變數的名稱清單。 | Low |
| S2 | HTTP server 綁定 | `run_red_team_suite.py` | `github_pr_files_server()` 綁定 `127.0.0.1:0`（動態 port），僅用於短暫測試 fixture。安全設計合理，但無 request body size 限制、無超時設定。因為只用於本地測試且生命週期極短，實際風險很低。 | Low |
| S3 | archive 讀取 | `guard_status_validator.py` | `load_archive_snapshot()` 讀取使用者指定路徑的檔案內容。雖有路徑穿越防護（`resolve_workspace_relative_path`），但若 archive 檔案極大，可能造成記憶體壓力。缺少 file size 上限檢查。 | Low |
| S4 | temp 目錄殘留 | `run_red_team_suite.py` | `prepare_temp_root()` 使用 `.codex-red-team/` 且 `finally` 中呼叫 `shutil.rmtree()`，但 Windows 上若檔案被鎖定可能殘留（git status 已可見 permission denied 的 `.codex-red-team/` 和 `.tmp-red-team/`）。 | Low |

### 8.3 可維護性

#### 優點

1. **CLI interface 統一**
   - 所有 main 腳本都使用 `argparse`，參數一致（`--root`、`--task-id`），學習成本低。

2. **Markdown 報告輸出標準化**
   - `run_red_team_suite.py`、`aggregate_red_team_scorecard.py`、`prompt_regression_validator.py` 的輸出都是可機器解析的 markdown 表格。

3. **`discover_templates.py` 支援 JSON 輸出**
   - 方便自動化工具消費，不限於人工閱讀。

4. **版本標記**
   - `guard_status_validator.py` 有 `__version__`，有利於追蹤。

#### 可改進項目

| # | 類別 | 位置 | 說明 | 嚴重度 |
|---|---|---|---|---|
| M1 | .gitignore 缺漏 | `.gitignore` | 缺少 `.codex-red-team/`、`.tmp-red-team/`、`*.override_log.json` 等工作流產出。目前 git status 持續出現 permission denied 警告。 | Medium |
| M2 | PyYAML 依賴 | `discover_templates.py` | 唯一有外部依賴（`yaml`）的腳本，且在 import 失敗時直接 `sys.exit(1)`。其他腳本全部 stdlib only，這個依賴可能在 CI 或新環境上造成意外失敗。 | Low |
| M3 | CI 覆蓋不足 | `.github/workflows/workflow-guards.yml` | Status guard 只跑 TASK-900、TASK-950、TASK-951。repo 已有 17+ 個 task，大部分未納入 CI 驗證。可改為動態掃描 `artifacts/status/*.status.json`。 | Medium |
| M4 | 無 requirements.txt | 全局 | Python 腳本幾乎全部 stdlib only（除了 `discover_templates.py` 的 PyYAML），但沒有 `requirements.txt` 或 `pyproject.toml` 明確聲明。對 CI 和新貢獻者不友善。 | Low |
| M5 | PowerShell 無 -ErrorAction | `Invoke-*.ps1` | try/catch 可捕獲 terminating error，但非 terminating error（如 cmdlet warning）不會被攔截。 | Low |

### 8.4 綜合評分

| 維度 | 評分 | 摘要 |
|---|---:|---|
| 代碼品質 | 4/5 | 結構清晰、型別標註完整、常數管理良好。主要短板是最大檔案偏長、少量重覆定義。 |
| 安全性 | 4.5/5 | 路徑穿越、shell injection、API token 處理均到位。僅 archive size 未設限、temp 殘留等低風險項。 |
| 可維護性 | 3.5/5 | CLI 統一、輸出標準化、版本追蹤齊備。短板在 .gitignore 缺漏、CI 覆蓋不足、缺 unit test。 |
| **綜合** | **4/5** | **生產等級的 workflow toolchain，整體品質高於多數 internal tool 水準。** |

### 8.5 建議行動優先順序

| 優先 | 行動 | 效果 |
|---:|---|---|
| 1 | 補 `.gitignore` 條目：`.codex-red-team/`、`.tmp-red-team/`、`template/.tmp-red-team/` | 立即消除 git status 噪音與 permission denied 警告 |
| 2 | CI status guard 改為 matrix/動態掃描 | 將 CI 治理覆蓋從 3 個 task 擴大到全部 |
| 3 | 從 `guard_contract_validator.py` + `update_repository_profile.py` 提取共用常數或在 contract guard 中 import | 消除 `REQUIRED_TOPICS` 重複定義風險 |
| 4 | 加入 `requirements.txt`（含 PyYAML pin） | 降低新環境部署摩擦 |
| 5 | 為核心解析函式加 unit test | 提供回歸保護，降低重構風險 |

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
| 工作樹衛生 | 4/5 | `.gitignore` 已補齊 red-team sandbox、暫存工作目錄、coverage 與 venv；worktree 噪音大幅降低 |

Repo 結構整體評級：**Level 4 / Managed（接近 Level 5）**。

原因是核心結構已高度模組化，且支援 bootstrap 與同步驗證；但工作樹衛生與維運負擔仍未完全收斂。

### 3.2 工作流成熟度

| 維度 | 評分 | 判斷 |
|---|---:|---|
| 流程定義完整度 | 5/5 | Intake 到 Closure、blocked 與 Gate E 都有制度 |
| Artifact schema 完整度 | 5/5 | artifact 類型、欄位、狀態與最低品質要求完整 |
| 自動化驗證 | 4.5/5 | status guard、contract guard、prompt regression、red-team 均已存在；255 項 unit test 提供回歸保護（coverage ≥45%） |
| 實際採用程度 | 4/5 | 已累積多個 TASK artifacts，代表流程被反覆使用 |
| CI 整合廣度 | 4.5/5 | CI 已接上 guard，status guard 以動態掃描覆蓋全部 task，並納入 unit test、coverage 報告與 repo health dashboard |
| 治理閉環能力 | 4/5 | blocked -> improvement -> resume 的 PDCA 概念成熟 |
| 持續優化能力 | 4.5/5 | 有 red-team/backlog/prompt regression；`repo_health_dashboard.py` 可追蹤 task coverage、stale status、missing verify、blocked aging |

工作流整體評級：**Level 4+ / Managed（接近 Level 5）**。

本次評估相比初版有顯著提升：CI 已從只驗證 3 個指定 task 升級為動態全域掃描，unit test 從零到 255 項，並新增 repo health dashboard 提供全局可觀測性。

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

1. ~~**CI 驗證覆蓋仍偏樣板化**~~ **已解決** — CI status guard 已改為動態掃描 `artifacts/status/TASK-*.status.json`，覆蓋全部 17+ 個 task，並啟用嚴格模式（移除 `--allow-scope-drift`）。

2. ~~**工作樹衛生不足**~~ **已解決** — `.gitignore` 已補齊 `.codex-red-team/`、`.tmp-red-team/`、`.venv/`、`.coverage`、`coverage-report/`、`.pytest_cache/`、`__pycache__/` 等，worktree 噪音大幅降低。

3. ~~**文件存在局部一致性風險**~~ **已解決** — `BOOTSTRAP_PROMPT.md` 已對齊 `docs/subagent_roles.md`：Gemini 認證從 `GEMINI_API_KEY` 改為 OAuth、升級模型名稱已統一（`gemini-3-flash-preview`、`gemini-3.1-pro-preview`）。root 與 template 均已同步。

4. ~~**Template 完整鏡像的維護成本高**~~ **已緩解** — `docs/orchestration.md` §9.6 已定義同步責任邊界（Tier 1–5），明確哪些檔案必須 exact sync、哪些允許 placeholder 泛化、哪些僅 phrase check、哪些需人工判斷、哪些不同步。維運負擔仍存在，但已有明確的歸類依據。

5. ~~**治理指標仍以文件與單次驗證為主**~~ **已解決** — `repo_health_dashboard.py` 提供統一的 repo health 視角：task 覆蓋率、stale status、missing verify、blocked aging、artifact coverage（支援 `--json` 與 `--stale-days` 參數），並已整合至 CI pipeline。

## 六、整體判斷

### 總結評級

- Repo 結構成熟度：**4/5**（工作樹衛生 2→4）
- 工作流成熟度：**4.5/5**（CI 廣度 3→4.5、自動化驗證 4→4.5、持續優化 4→4.5）
- 綜合評估：**Level 4+ / Managed（接近 Level 5 Optimizing）**

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

1. ~~將 status guard 從固定 task-id 改成自動掃描或 matrix 化，提升 CI 治理覆蓋。~~ **已完成** — CI 已改為動態掃描 `artifacts/status/TASK-*.status.json`，並移除 `--allow-scope-drift` 以啟用嚴格模式。
2. ~~補強 `.gitignore`，納入 red-team sandbox、暫存工作目錄與明確的本地輸出，降低 worktree 噪音。~~ **已完成** — 已加入 `.codex-red-team/`、`.tmp-red-team/`、`.venv/`、`.coverage`、`coverage-report/`、`.pytest_cache/` 等。
3. ~~對齊 `BOOTSTRAP_PROMPT.md` 與 `docs/subagent_roles.md` 的 Gemini/Codex 認證與呼叫指引。~~ **已完成** — 認證方式已從 `GEMINI_API_KEY` 對齊至 OAuth，模型名稱已統一。
4. ~~增加一個 repo health summary 腳本，統計 task coverage、stale status、missing verify、blocked aging 等指標。~~ **已完成** — `repo_health_dashboard.py` 已建立並加入 CI pipeline。
5. ~~若 `template/` 長期維持完整鏡像，建議再補一層「同步責任邊界」說明，明確哪些檔案必須 exact sync、哪些允許 placeholder 泛化。~~ **已完成** — `docs/orchestration.md` §9.6 已新增「同步責任邊界」矩陣，分 Tier 1–5 五層定義。

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
| Q2 | ~~重複定義~~ | `guard_contract_validator.py` + `update_repository_profile.py` | ~~`REQUIRED_TOPICS` 與 `TOPIC_PATTERN` 在兩個檔案中重複定義。~~ **已解決** — 已提取共用常數至 `_shared_constants.py`。 | ~~Medium~~ ✅ |
| Q3 | 重複函式 | `guard_status_validator.py` + `run_red_team_suite.py` | `compute_snapshot_sha256()` 在兩個檔案中都有定義，簽章略有不同（一個接受 `Set[str]`，一個接受 `Sequence[str]`）。 | Low |
| Q4 | 硬編碼 | `run_red_team_suite.py` | `blocked_sample_source()` 硬編碼檢查 `TASK-902` / `TASK-901`，未來新增或移除 sample task 時容易遺漏。 | Low |
| Q5 | ~~缺少單元測試~~ | 全局 | ~~目前只有 red-team suite 作為 integration test。~~ **已解決** — `test_guard_units.py` 包含 255 項 unit test，覆蓋核心解析函式、驗證邏輯與邊界條件（coverage ≥45%，CI 強制執行）。 | ~~Medium~~ ✅ |

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
| M1 | ~~.gitignore 缺漏~~ | `.gitignore` | ~~缺少 `.codex-red-team/`、`.tmp-red-team/`、`*.override_log.json` 等工作流產出。~~ **已解決** — `.gitignore` 已補齊所有工作流暫存目錄與 coverage 產出。 | ~~Medium~~ ✅ |
| M2 | PyYAML 依賴 | `discover_templates.py` | 唯一有外部依賴（`yaml`）的腳本，且在 import 失敗時直接 `sys.exit(1)`。其他腳本全部 stdlib only，這個依賴可能在 CI 或新環境上造成意外失敗。 | Low |
| M3 | ~~CI 覆蓋不足~~ | `.github/workflows/workflow-guards.yml` | ~~Status guard 只跑 TASK-900、TASK-950、TASK-951。~~ **已解決** — 已改為動態掃描 `artifacts/status/TASK-*.status.json`，覆蓋全部 task，並移除 `--allow-scope-drift` 啟用嚴格模式。 | ~~Medium~~ ✅ |
| M4 | ~~無 requirements.txt~~ | 全局 | ~~Python 腳本沒有 `requirements.txt`。~~ **已解決** — 已建立 `requirements.txt`（含 PyYAML pin），CI 可自動安裝。 | ~~Low~~ ✅ |
| M5 | PowerShell 無 -ErrorAction | `Invoke-*.ps1` | try/catch 可捕獲 terminating error，但非 terminating error（如 cmdlet warning）不會被攔截。 | Low |

### 8.4 綜合評分

| 維度 | 初版評分 | 更新評分 | 摘要 |
|---|---:|---:|---|
| 代碼品質 | 4/5 | 4.5/5 | Q2（重複定義）已解決、Q5（缺 unit test）已解決（255 項 test）。剩餘 Q1、Q3、Q4 均為 Low。 |
| 安全性 | 4.5/5 | 4.5/5 | 無變動。路徑穿越、shell injection、API token 處理均到位。 |
| 可維護性 | 3.5/5 | 4.5/5 | M1（.gitignore）、M3（CI 覆蓋）、M4（requirements.txt）均已解決。僅 M2（PyYAML）、M5（PowerShell）為 Low。 |
| **綜合** | **4/5** | **4.5/5** | **生產等級的 workflow toolchain，整體品質高於多數 internal tool 水準。本次提升主要來自 unit test（255 項）、CI 全域動態掃描與 repo health dashboard。** |

### 8.5 建議行動優先順序

| 優先 | 行動 | 狀態 | 效果 |
|---:|---|---|---|
| 1 | ~~補 `.gitignore` 條目~~ | ✅ 已完成 | git status 噪音消除 |
| 2 | ~~CI status guard 改為動態掃描~~ | ✅ 已完成 | CI 治理覆蓋 3 → 17+ task |
| 3 | ~~提取共用常數~~ | ✅ 已完成 | `_shared_constants.py` 消除重複定義 |
| 4 | ~~加入 `requirements.txt`~~ | ✅ 已完成 | CI 可自動安裝依賴 |
| 5 | ~~為核心函式加 unit test~~ | ✅ 已完成 | 255 項 test，coverage ≥45% |

### 8.6 剩餘改進項目

| 優先 | 行動 | 效果 |
|---:|---|---|
| 1 | ~~對齊 `BOOTSTRAP_PROMPT.md` 與 `docs/subagent_roles.md` 的 Gemini/Codex 認證指引~~ ✅ 已完成 | 降低新使用者 onboarding 摩擦 |
| 2 | 持續提升 unit test coverage（目前 ≥45%，目標 60%+） | 強化回歸保護 |
| 3 | PowerShell wrapper 加入 `-ErrorAction Stop` | 捕獲非 terminating error |
| 4 | ~~制定 `template/` 同步責任邊界說明~~ ✅ 已完成 | `docs/orchestration.md` §9.6 Tier 1–5 定義 |

---

## 九、修訂紀錄

| 日期 | 版本 | 變更摘要 |
|---|---|---|
| 2025-07-17 | v1.0 | 初版評估：Repo 結構 4/5、工作流 4/5、Code Review 4/5（綜合 Level 4 Managed） |
| 2025-07-17 | v1.1 | 反映 session 改進成果：.gitignore 補齊、CI 動態掃描、共用常數提取、requirements.txt、255 項 unit test、repo health dashboard。工作流 4→4.5、可維護性 3.5→4.5、綜合 4→4.5（Level 4+ 接近 Level 5） |
| 2025-07-17 | v1.2 | 對齊 BOOTSTRAP_PROMPT.md 與 subagent_roles.md 的 Gemini 認證方式（GEMINI_API_KEY → OAuth）；新增 orchestration.md §9.6 同步責任邊界（Tier 1–5）。§5 風險 5/5 已解決或緩解，§7 建議 5/5 已完成 |

# Research: TASK-959

## Metadata
- Task ID: TASK-959
- Artifact Type: research
- Owner: Claude
- Status: ready
- Last Updated: 2026-04-14T23:00:00+08:00

## Research Questions

1. Hermes Agent 的 skill framework 結構為何？（檔案格式、frontmatter schema、載入機制、平台相容性檢查、config 注入）
2. Hermes skill system 與 Consilium Fabri 的 `subagent_task_templates.md` 有哪些結構性差異？
3. Hermes 的哪些概念可移植到 artifact-first workflow，哪些與核心原則衝突？
4. Hermes 的 smart model routing 與 context compression 機制為何？對本架構有何參考價值？

## Confirmed Facts

### CF-1: Skill 檔案格式

每個 skill 是一個目錄，內含必要的 `SKILL.md` 與可選的 supporting files：

```
skills/
├── my-skill/
│   ├── SKILL.md              # 主指令（必要）
│   ├── references/           # 參考文件（*.md）
│   ├── templates/            # 輸出範本（*.md, *.py, *.yaml 等）
│   ├── assets/               # 靜態資源
│   └── scripts/              # 工具腳本（*.py, *.sh）
```

Source: `external/hermes-agent/tools/skills_tool.py` lines 14-26, 960-1026

### CF-2: SKILL.md Frontmatter Schema

YAML frontmatter 定義 skill metadata，關鍵欄位：

| 欄位 | 必要 | 說明 |
|------|------|------|
| `name` | Yes | 最多 64 字元，自動轉為 `/slash-command` |
| `description` | Yes | 最多 1024 字元 |
| `version` | No | 語意版本 |
| `platforms` | No | 限制 OS（`macos`, `linux`, `windows`），未設則全平台 |
| `required_environment_variables` | No | 需要的環境變數（含 prompt、help text） |
| `metadata.hermes.config` | No | 從 config.yaml 注入的設定值 |
| `metadata.hermes.tags` | No | 分類標籤 |
| `metadata.hermes.related_skills` | No | 關聯 skill |
| `setup.collect_secrets` | No | 引導使用者設定 API key |

Source: `external/hermes-agent/tools/skills_tool.py` lines 28-46; `external/hermes-agent/agent/skill_utils.py` lines 52-86

### CF-3: Skill 載入與執行流程

1. **Discovery**: `scan_skill_commands()` 遞迴掃描 `~/.hermes/skills/` + external dirs，找到所有 `SKILL.md`
2. **Filtering**: 檢查 platform 相容性（`skill_matches_platform()`）、disabled 清單（source: `external/hermes-agent/agent/skill_commands.py`).
3. **Normalization**: name → lowercase, 空格/底線轉 `-`, 去無效字元 → `/command-name`（source: `external/hermes-agent/agent/skill_commands.py`).
4. **Lazy caching**: 全域 `_skill_commands` dict，首次存取時掃描，不跨 session 持久化（source: `external/hermes-agent/agent/skill_commands.py`).
5. **Invocation**: 使用者輸入 `/command` → 載入 SKILL.md body → 注入 config 值 → 附上 supporting files 清單 → 作為 system context 注入 agent turn（source: `external/hermes-agent/agent/skill_commands.py`).
6. **Gateway**: 同一流程適用所有平台（Telegram, Discord 等），可按平台停用特定 skill

Source: `external/hermes-agent/agent/skill_commands.py` lines 200-262, 265-269; `external/hermes-agent/cli.py` lines 5568-5580

### CF-4: Configuration Auto-Injection

Skill 可在 frontmatter 宣告 config 需求：

```yaml
metadata:
  hermes:
    config:
      - key: wiki.path
        description: Path to wiki knowledge base
        default: "~/wiki"
        prompt: Wiki directory path
```

Runtime 從 `~/.hermes/config.yaml` 的 `skills.config.<key>` 讀取值，支援 `~` 與 `${VAR}` 展開，注入結果附加在 skill message 尾部：

```
[Skill config (from ~/.hermes/config.yaml):
  wiki.path = /home/user/wiki
]
```

Source: `external/hermes-agent/agent/skill_utils.py` lines 261-317, 377-412; `external/hermes-agent/agent/skill_commands.py` lines 82-118

### CF-5: Platform Compatibility

使用 `sys.platform` 比對 frontmatter `platforms` 欄位，mapping：`macos` → `darwin`, `linux` → `linux`, `windows` → `win32`。未宣告 platforms 的 skill 預設全平台可用。另有 per-platform disabled 機制（config.yaml `skills.platform_disabled.<platform>`）。

Source: `external/hermes-agent/agent/skill_utils.py` lines 92-115, 121-160

### CF-6: Smart Model Routing 機制

`smart_model_routing.py` 使用保守啟發式判斷「簡單」turn：

- 條件：≤160 字元、≤28 words、單行、無 backtick、無 URL、不含 46 個 complexity keywords（debug, implement, refactor, test, plan 等）（source: `external/hermes-agent/agent/smart_model_routing.py`).
- 通過全部條件 → 路由到便宜 model（如 `google/gemini-2.5-flash`）（source: `external/hermes-agent/agent/smart_model_routing.py`).
- 任一條件不符 → 使用 primary model（source: `external/hermes-agent/agent/smart_model_routing.py`).
- Provider 失敗 → 立即 fallback 到 primary model，無 retry

Source: `external/hermes-agent/agent/smart_model_routing.py` lines 11-46, 62-107, 110-196

### CF-7: Context Compression 機制

`context_compressor.py`（821 行）實作多階段壓縮：

1. **Phase 1 — Tool Result Pruning**: 將舊 tool output 替換為 placeholder（無 LLM 呼叫）（source: `external/hermes-agent/agent/context_compressor.py`).
2. **Phase 2 — Boundary Alignment**: 以 token budget 從尾端回推找切割點，硬底線保護 3 條 tail messages（source: `external/hermes-agent/agent/context_compressor.py`).
3. **Phase 3 — Summarization**: 用 auxiliary model（預設 gemini-3-flash-preview 或 claude-haiku-4-5）產生結構化摘要（source: `external/hermes-agent/agent/context_compressor.py`).
4. **Phase 4 — Assembly**: head messages + summary + tail messages（source: `external/hermes-agent/agent/context_compressor.py`).
5. **Phase 5 — Sanitization**: 清理孤立的 tool result pairs

觸發條件：`prompt_tokens >= threshold_tokens`（預設 context window 的 50%）。摘要 token 上限 12,000，佔壓縮內容的 20%。

Source: `external/hermes-agent/agent/context_compressor.py` lines 103-161, 666-820; `external/hermes-agent/agent/context_engine.py` lines 32-185

### CF-8: 結構化摘要模板

壓縮摘要使用固定模板，包含：Goal、Constraints & Preferences、Progress（Done/In Progress/Blocked）、Key Decisions、Resolved Questions、Pending User Asks、Relevant Files、Remaining Work、Critical Context、Tools & Patterns。迭代壓縮時保留前次摘要並更新。

Source: `external/hermes-agent/agent/context_compressor.py` lines 318-483

## Relevant References

| 來源 | 路徑 / URL |
|------|-----------|
| Skill loading 核心 | `external/hermes-agent/agent/skill_commands.py` |
| Skill 工具函式 | `external/hermes-agent/agent/skill_utils.py` |
| Skill view / JSON response | `external/hermes-agent/tools/skills_tool.py` |
| Smart model routing | `external/hermes-agent/agent/smart_model_routing.py` |
| Context compressor | `external/hermes-agent/agent/context_compressor.py` |
| Context engine base | `external/hermes-agent/agent/context_engine.py` |
| Models.dev integration | `external/hermes-agent/agent/models_dev.py` |
| 本專案 subagent templates | `docs/subagent_task_templates.md` |
| 本專案 artifact schema | `docs/artifact_schema.md` |

## Confirmed Facts — Comparison Table (AC-2)

### Hermes Skill System vs Consilium Fabri Subagent Task Templates

| 面向 | Hermes Skill | Consilium Fabri Template |
|------|-------------|------------------------|
| **格式** | 獨立目錄 + `SKILL.md`（YAML frontmatter + markdown body） | 嵌入在單一 `subagent_task_templates.md` 內的 code block |
| **Metadata** | 結構化 YAML（name, description, version, platforms, config, tags） | 無 metadata；Role / Inputs / Task / Rules / Output 純文字 |
| **可執行性** | `/command` 直接觸發，自動注入 config 與 supporting files | 由 orchestrator 手動複製貼上到 subagent prompt |
| **平台感知** | `platforms` 欄位 + per-platform disabled 機制 | 無；所有 template 對所有 agent 可用 |
| **Config 注入** | 自動從 config.yaml 讀取並注入 | 無；所有參數寫死在 template 或由 orchestrator 填入 |
| **Supporting files** | references/, templates/, scripts/, assets/ 自動索引 | 無；所有資訊必須在 template 內或由 orchestrator 手動提供 |
| **版本管理** | `version` 欄位 + 目錄隔離 | 無版本追蹤 |
| **Discovery** | 自動掃描 + lazy cache | 手動引用文件路徑 |
| **品質約束** | 無強制規則；skill 內容自由度高 | 嚴格：每個 template 強制定義 Inputs / Rules / Output / Required sections |
| **Scope 控制** | 無；skill 可自由擴展行為 | 強：Rules 明確禁止 scope creep（"Do NOT modify files outside plan scope"） |
| **Audit trail** | 無；執行結果不持久化 | 強：所有輸出必須寫入 artifact，否則不算完成 |

Source: `docs/subagent_task_templates.md`（完整內容已讀取）; CF-1 至 CF-5 各 Hermes source files

## Confirmed Facts — Portability Assessment (AC-3)

### 可移植的概念

| 概念 | 移植方式 | 與 artifact-first 相容性 |
|------|---------|------------------------|
| **結構化 Metadata** | 為每個 subagent template 加入 YAML frontmatter（name, description, version, tags） | 完全相容：metadata 強化可追蹤性 |
| **獨立目錄結構** | 將 templates 從單一 .md 拆為 `templates/<role>/TEMPLATE.md` + `references/` | 完全相容：不影響 artifact pipeline |
| **Supporting files 索引** | 讓 template 可聲明關聯的 reference docs、example outputs | 完全相容：減少 orchestrator 手動組裝 |
| **Config 注入** | 定義 template variables（如 `{{TASK_ID}}`、`{{PLAN_PATH}}`）自動填充 | 完全相容：已有 placeholder 慣例 |
| **Platform/Agent 感知** | 為 template 標注適用 agent（Claude/Gemini/Codex）與前置條件 | 完全相容：強化派發準確性 |
| **Lazy discovery** | 讓 orchestrator 自動掃描 templates 目錄而非硬編路徑 | 完全相容：減少 AGENTS.md 手動維護 |

### 與 artifact-first 原則衝突的概念

| 概念 | 衝突點 |
|------|--------|
| **Skill 自由執行** | Hermes skill 無 scope 限制，agent 可自由擴展行為；Consilium Fabri 的 Rules 區段明確禁止 scope creep |
| **無 audit trail** | Hermes skill 執行後結果不強制持久化；Consilium Fabri 要求所有輸出寫入 artifact |
| **Memory-based 狀態** | Hermes 依賴對話記憶傳遞 skill context；Consilium Fabri 禁止 memory 作為共享狀態來源 |
| **無品質 gate** | Hermes skill 無驗收機制；Consilium Fabri 的 4 hard gates 不可繞過 |
| **Hot-reload 無版本鎖定** | Hermes skill 可隨時修改生效，無 change tracking；artifact-first 要求所有變更可追蹤 |

## Sources

[1] NousResearch. "tools/skills_tool.py." https://github.com/NousResearch/hermes-agent/blob/main/tools/skills_tool.py (2026-04-15 retrieved)
[2] NousResearch. "agent/skill_utils.py." https://github.com/NousResearch/hermes-agent/blob/main/agent/skill_utils.py (2026-04-15 retrieved)
[3] NousResearch. "agent/smart_model_routing.py." https://github.com/NousResearch/hermes-agent/blob/main/agent/smart_model_routing.py (2026-04-15 retrieved)
[4] NousResearch. "agent/context_compressor.py." https://github.com/NousResearch/hermes-agent/blob/main/agent/context_compressor.py (2026-04-15 retrieved)

## Uncertain Items

- UNVERIFIED: Hermes 的 `reload-mcp` gateway 指令是否確實呼叫 `scan_skill_commands()` — 程式碼中有此指令但未完整追蹤其實作（`gateway/run.py` line 2748-2749，函式體未完整閱讀）
- UNVERIFIED: Hermes 的 context compression 在 gateway 長期運行場景下的實際穩定性 — 僅從程式碼結構推斷，未有生產環境觀測

## Constraints For Implementation

1. **任何 template 結構改動必須保留 artifact-first 核心保證**：每個 subagent 輸出仍必須寫入對應 artifact，不得因 skill 化而跳過 gate。

2. **Template metadata 擴充須同步 root → template/ → Obsidian 三處**：依據 CLAUDE.md template sync protocol，任何 `docs/subagent_task_templates.md` 結構變更皆為 workflow file 修改。

3. **若採用獨立目錄結構，`AGENTS.md` 載入矩陣須同步更新**：目前 templates 為單一文件，拆分後載入路徑改變。

4. **Smart model routing 若引入，不得取消角色分工約束**：Consilium Fabri 的 Claude/Gemini/Codex 分工不僅是 model 選擇，更是責任邊界（orchestrator / researcher / implementer）。路由優化只能在同角色內選擇更適合的 model，不能跨角色。

5. **Context compression 若引入，摘要內容不得取代 artifact**：壓縮摘要僅用於管理 context window，不可作為 agent 間共享狀態的替代。

6. **Follow-up TASK 建議（AC-5）**：

   - **TASK-A**: 將 `subagent_task_templates.md` 拆分為 `templates/<role>/TEMPLATE.md` 目錄結構，加入 YAML frontmatter metadata（name, description, version, applicable_agents, prerequisites），保留現有 Rules/Inputs/Output 強制區段
   - **TASK-B**: 為 orchestrator 加入 template auto-discovery 機制，取代 AGENTS.md 中的硬編路徑引用
   - **TASK-C**: 評估在 Codex 派發階段引入 model routing（同角色內選擇 model），需先確認 Codex CLI 是否支援 model 切換

# Consilium Fabri

繁體中文 | **[English](README.md)**

> *Consilium Fabri* — 拉丁文，意為「工匠議會」。
> 三個臭皮匠，勝過一個諸葛亮。

經實戰淬鍊的 **多 Agent AI 開發工作流範本**，支援 Claude Code（協調者）、Gemini CLI（研究員）、Codex CLI（實作者）的 gate-guarded、artifact-first 協作架構。

## 快速開始

### 1. Clone 並複製到你的專案

```bash
git clone https://github.com/arcobaleno64/consilium-fabri.git
cp -r consilium-fabri/ /path/to/your/project/
```

### 2. 替換 Placeholder

範本使用 `{{PLACEHOLDER}}` 語法。替換 `CLAUDE.md` 中的以下變數：

| Placeholder | 說明 | 範例 |
|---|---|---|
| `{{PROJECT_NAME}}` | 你的專案名稱 | `MyApp` |
| `{{REPO_NAME}}` | 上游 repo 名稱（若使用 fork 模式） | `my-upstream-repo` |
| `{{UPSTREAM_ORG}}` | 上游 GitHub org/user（若使用 fork 模式） | `original-author` |

```bash
sed -i 's/{{PROJECT_NAME}}/MyApp/g; s/{{REPO_NAME}}/my-upstream-repo/g; s/{{UPSTREAM_ORG}}/original-author/g' CLAUDE.md
```

如果你的專案不使用 fork 模式，可直接移除 `CLAUDE.md` 中的「Repository boundaries」區段。

### 3. 驗證安裝

```bash
python artifacts/scripts/guard_status_validator.py --task-id TASK-900
# 預期輸出：[OK] Validation passed
```

### 4. 設定 Hooks（選用）

```bash
cp .claude/settings.json.example .claude/settings.json
```

## 檔案結構

```
├── CLAUDE.md                          # Claude Code 入口（自動載入）
├── GEMINI.md                          # Gemini CLI 入口（透過 prompt 傳入）
├── CODEX.md                           # Codex CLI 入口（透過 prompt 傳入）
├── AGENTS.md                          # 主索引 + 階段載入矩陣
├── BOOTSTRAP_PROMPT.md                # 開新專案的提示詞範本
├── docs/                              # 參考文件（按需載入）
│   ├── orchestration.md               # 系統提示：目標、原則、階段、閘門
│   ├── artifact_schema.md             # 8 種 artifact 類型的 schema 定義
│   ├── subagent_roles.md              # 7 個 agent 角色定義
│   ├── workflow_state_machine.md      # 8 個狀態 + 合法轉移
│   ├── premortem_rules.md             # 風險分析格式 + 品質規則
│   ├── subagent_task_templates.md     # 外包 prompt 範本
│   └── lightweight_mode_rules.md      # 精簡模式規則
├── artifacts/
│   ├── tasks/                         # 任務定義 (TASK-XXX.task.md)
│   ├── status/                        # 機讀狀態 (TASK-XXX.status.json)
│   ├── research/                      # 研究發現 (TASK-XXX.research.md)
│   ├── plans/                         # 實作計畫 (TASK-XXX.plan.md)
│   ├── code/                          # 程式變更記錄 (TASK-XXX.code.md)
│   ├── verify/                        # 驗證結果 (TASK-XXX.verify.md)
│   ├── decisions/                     # 決策記錄 (TASK-XXX-DEC-XXX.md)
│   └── scripts/
│       └── guard_status_validator.py  # 閘門驗證器（純 Python stdlib）
├── .claude/
│   └── settings.json.example         # Hook 範例（通知、自動格式化）
└── README.md
```

## Token 節省策略

每個 agent 只載入自己的入口檔，參考文件按階段按需載入：

| Agent | 入口檔 | ~Tokens | 策略 |
|---|---|---|---|
| Claude Code | `CLAUDE.md` | 800 | 依 `AGENTS.md` 矩陣按階段載入 `docs/` |
| Gemini CLI | `GEMINI.md` | 1,500 | 關鍵規則已內嵌（無檔案系統存取） |
| Codex CLI | `CODEX.md` | 1,300 | 關鍵規則已內嵌 |

相比一次載入全部文件（~16K tokens），**節省 81–92%**。

## 工作流程

每個任務遵循嚴格的閘門管控流水線：

```
收件 → 研究 → 規劃 → 實作 → 驗證 → 完成
  │      │      │      │      │
 Gate A  Gate B Gate C Gate D  ✓
```

| 閘門 | 條件 |
|---|---|
| **A — 研究** | 必須有 task artifact |
| **B — 規劃** | 必須有 research artifact |
| **C — 實作** | Plan 的 `Ready For Coding: yes` + premortem 品質檢查 |
| **D — 驗證** | 必須有 code artifact + verify 中的 `## Build Guarantee` |

`guard_status_validator.py` 以程式化方式強制所有閘門。

## Agent 角色

| Agent | 角色 | 可寫程式？ |
|---|---|---|
| **Claude Code** | 協調者 — 派發任務、撰寫 artifact | 僅 artifact 文件 |
| **Gemini CLI** | 研究員 — 產出已驗證的發現與約束 | 否 |
| **Codex CLI** | 實作者 — 依計畫撰寫生產程式碼 | 是 |

## 核心概念

### 事前驗屍（Premortem）
進入實作前，plan 的 `## Risks` 必須包含結構化風險條目（R1, R2, ...），每條含 Risk、Trigger、Detection、Mitigation、Severity。驗證器會硬擋品質不足的 premortem。

### 建置保證（Build Guarantee）
每個 verify artifact 必須證明被修改的建置單元確實被建置過。防止「測試通過但建置壞掉」的假陽性。

### 負面測試（Negative Testing）
故意破壞某些東西來證明流水線能抓到它 — 一種輕量版的 workflow artifact 突變測試。

## 客製化

| 項目 | 修改位置 |
|---|---|
| 建置工具 | `docs/artifact_schema.md` §5.6 |
| 狀態轉移 | `guard_status_validator.py` → `LEGAL_TRANSITIONS` |
| 必要標記 | `guard_status_validator.py` → `MARKERS` |
| Agent 品質規則 | `docs/subagent_roles.md` §4.5 |

## 未來規劃

- [ ] Copier 整合（支援範本生命週期管理）
- [ ] CI/CD 流水線範本（GitHub Actions / Azure DevOps）
- [ ] MCP server 整合範例
- [ ] 互動式 bootstrap wizard

## 授權

[MIT](LICENSE)

---

*萃取自實戰經驗（TASK-002 至 TASK-008）。從假陽性驗證事件、agent 角色漂移、upstream PR 無效化等教訓中，淬鍊出每一條約束規則。*

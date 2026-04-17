# 驗證指令

## 指令速查表

| 指令 | 用途 |
|---|---|
| `python artifacts/scripts/guard_status_validator.py --task-id TASK-XXX` | 驗證任務狀態、產物與 scope drift |
| `python artifacts/scripts/guard_status_validator.py --task-id TASK-XXX --auto-classify` | 自動判定任務為 lightweight 或 full-gate |
| `python artifacts/scripts/guard_contract_validator.py` | 驗證 root ↔ template ↔ Obsidian 同步 |
| `python artifacts/scripts/guard_contract_validator.py --check-readme` | 驗證 README 結構合規性 |
| `python artifacts/scripts/prompt_regression_validator.py --root .` | 執行 prompt regression 測例 |
| `python artifacts/scripts/run_red_team_suite.py --phase all` | 執行完整紅隊演練 |
| `python artifacts/scripts/run_red_team_suite.py --phase prompt` | 透過報表流程執行 prompt regression |
| `python artifacts/scripts/repo_health_dashboard.py` | 產生儲存庫健康儀表板 |
| `python artifacts/scripts/build_decision_registry.py --root .` | 重建決策登錄冊 |
| `python artifacts/scripts/update_repository_profile.py` | 更新 GitHub 儲存庫 profile |

## Guard Status Validator

`guard_status_validator.py` 負責驗證：

- 任務狀態轉換是否合法
- 必要 artifacts 是否存在且 metadata 完整
- Scope drift 檢測（Files Changed ⊆ Files Likely Affected）
- Build Guarantee 是否到位

### Scope Drift 處理

- **預設行為**: scope drift 視為 hard fail
- **Dirty worktree**: 直接比對實際 git changed files
- **Clean task**: 可用 `commit-range` evidence 重放 historical diff
- **Git objects 遺失**: 改用 `archive fallback`（Archive Path / Archive SHA256）
- **GitHub PR**: 透過 GitHub PR files API 重建 changed files
- **`--allow-scope-drift`**: 僅在附顯式 decision waiver 時可用，且只能降級真正的 drift

## Guard Contract Validator

`guard_contract_validator.py` 負責驗證：

- root ↔ template 檔案同步（5 層 Tier 分級）
- Obsidian 入口同步
- README 結構合規性（`--check-readme` 模式）
- Prompt regression cases 與 agent 入口檔一致性
- Bootstrap 規則

### 同步 Tier 分級

| Tier | 策略 | 內容 |
|---|---|---|
| Tier 1 | Exact Sync | AGENTS.md、BOOTSTRAP_PROMPT.md、docs/*.md、guard scripts |
| Tier 2 | Placeholder-Generalized | CLAUDE.md |
| Tier 3 | Phrase-Checked | OBSIDIAN.md、README 系列 |
| Tier 4 | Manual Sync | .gitignore、requirements.txt、workflows |
| Tier 5 | Project-Specific | artifacts/tasks、decisions、.env |

## 紅隊演練

- **Runbook**: `docs/red_team_runbook.md`
- **評分矩陣**: `docs/red_team_scorecard.md`
- **補強清單**: `docs/red_team_backlog.md`
- **重跑指令**: `python artifacts/scripts/run_red_team_suite.py --phase all`

## Prompt Regression

固定測例位於 `artifacts/scripts/drills/prompt_regression_cases.json`，涵蓋：

- artifact-only truth/completion
- workflow sync completeness
- Gemini blocked preconditions
- Codex summary discipline
- conflict-to-decision routing
- decision schema integrity
- external failure STOP
- decision-gated scope waiver
- historical diff evidence contract
- pinned diff evidence integrity
- GitHub provider-backed diff evidence
- archive retention fallback contract

# Obsidian 入口筆記

本檔是此 vault 的 Markdown 文件入口，提供文件語言規範、閱讀順序與同步範圍摘要。完整 workflow 規則仍以 `AGENTS.md`、`CLAUDE.md` 與 `docs/` 內文件為準；任何 workflow 規則變更若未同步本檔，視為未完成。

## 文件語言規範

- 長期維護的 workflow、template 與入口類 Markdown 文件以繁體中文（臺灣）為主。
- 專有名詞、檔名、CLI 指令、環境變數、placeholder、schema literal、狀態值保留英文原字。
- 不得更動會被 agent、validator、腳本依賴的精確字串，例如 `## Metadata`、`Task ID`、`Artifact Type`、`Owner`、`Status`、`Last Updated`。
- 所有紀錄時間、`Last Updated` 與相關時間戳一律使用 `Asia/Taipei`，採 ISO 8601 並帶 `+08:00`。
- root、`template/` 與 Obsidian 入口文件必須保持語義一致；若 template 因 placeholder 泛化而字面不同，仍需維持同一套規則。

## 建議閱讀順序

1. `AGENTS.md`
2. `CLAUDE.md`
3. `docs/orchestration.md`
4. `docs/artifact_schema.md`
5. `BOOTSTRAP_PROMPT.md`
6. `docs/red_team_runbook.md`

## 同步範圍

- 需同步：入口檔、`docs/*.md`、README、Obsidian 入口、`artifacts/scripts/guard_status_validator.py`、`artifacts/scripts/guard_contract_validator.py`、`artifacts/scripts/run_red_team_suite.py`、template 對應文件。
- 不追溯改寫：`artifacts/` 內歷史任務記錄、`template/experiments/` 產出、外部 repo 與備份目錄中的 Markdown。

## Workflow 摘要

- Research artifact 是 fact-only 契約，不得包含 `Recommendation` 或 solution 設計。
- `blocked` 任務恢復前，必須先有 `Status: applied` 的 improvement artifact。
- plan/code scope drift 預設由 status guard 視為 fail；僅在受控例外下使用 `--allow-scope-drift`。
- `CLAUDE.md` / `GEMINI.md` / `CODEX.md` 有變更時，必須同步更新 `artifacts/scripts/drills/prompt_regression_cases.json`。
- workflow 規則變更後，必須同步更新 root、`template/` 與 Obsidian 入口，並通過 contract guard。
- 紅隊演練入口是 `docs/red_team_runbook.md`，重跑命令是 `python artifacts/scripts/run_red_team_suite.py`。
- Prompt regression 固定入口是 `python artifacts/scripts/prompt_regression_validator.py --root .`，固定測例在 `artifacts/scripts/drills/prompt_regression_cases.json`。

## GitHub / Template 對應

- GitHub 對外入口：`README.md`、`README.zh-TW.md`
- Template 對應：`template/AGENTS.md`、`template/CLAUDE.md`、`template/GEMINI.md`、`template/CODEX.md`、`template/BOOTSTRAP_PROMPT.md`
- Obsidian 對應：`template/OBSIDIAN.md`

# Obsidian 入口筆記

本檔是此 vault 的 Markdown 文件入口，提供文件語言規範、閱讀順序與同步範圍摘要。完整 workflow 規則仍以 `AGENTS.md`、`CLAUDE.md` 與 `docs/` 內文件為準。

## 文件語言規範

- 長期維護的 workflow、template 與入口類 Markdown 文件以繁體中文（臺灣）為主。
- 專有名詞、檔名、CLI 指令、環境變數、placeholder、schema literal、狀態值保留英文原字。
- 不得更動會被 agent、validator、腳本依賴的精確字串，例如 `## Metadata`、`Task ID`、`Artifact Type`、`Owner`、`Status`、`Last Updated`。
- 所有紀錄時間、`Last Updated` 與相關時間戳一律使用 `Asia/Taipei`，採 ISO 8601 並帶 `+08:00`。
- root 與 `template/` 對應文件必須保持語義一致；若 template 因 placeholder 泛化而字面不同，仍需維持同一套規則。

## 建議閱讀順序

1. `AGENTS.md`
2. `CLAUDE.md`
3. `docs/orchestration.md`
4. `docs/artifact_schema.md`
5. `BOOTSTRAP_PROMPT.md`

## 同步範圍

- 需同步：入口檔、`docs/*.md`、README、Obsidian 入口、template 對應文件。
- 不追溯改寫：`artifacts/` 內歷史任務記錄、`template/experiments/` 產出、外部 repo 與備份目錄中的 Markdown。

## GitHub / Template 對應

- GitHub 對外入口：`README.md`、`README.zh-TW.md`
- Template 對應：`template/AGENTS.md`、`template/CLAUDE.md`、`template/GEMINI.md`、`template/CODEX.md`、`template/BOOTSTRAP_PROMPT.md`
- Obsidian 對應：`template/OBSIDIAN.md`

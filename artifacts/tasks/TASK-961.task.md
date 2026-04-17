# Task: TASK-961

## Metadata
- Task ID: TASK-961
- Artifact Type: task
- Owner: Claude
- Status: drafted
- Last Updated: 2026-04-14T23:15:00+08:00

## Objective

為 orchestrator（Claude Code）加入 template auto-discovery 機制，使其能自動掃描 `docs/templates/` 目錄，解析各 TEMPLATE.md 的 YAML frontmatter，並根據 `applicable_agents` 與當前階段自動選擇可用 template，取代 AGENTS.md 中的硬編路徑引用。

## Background

- TASK-959 research 確認 Hermes 的 lazy discovery（`scan_skill_commands()` 遞迴掃描 + frontmatter 解析 + platform filtering）可安全移植。
- TASK-960 將 templates 拆分為獨立目錄結構並加入 YAML frontmatter，為本任務提供結構基礎。
- 目前 orchestrator 派發 subagent 時，需手動引用 `docs/subagent_task_templates.md` 並複製貼上對應區段。Auto-discovery 可減少手動組裝，降低品質漂移風險。

## Inputs

- TASK-960 產出的 `docs/templates/<role>/TEMPLATE.md` 結構（依賴 TASK-960 完成）
- `docs/subagent_roles.md` — 角色定義與派發時機
- `AGENTS.md` — 現有載入矩陣
- `artifacts/research/TASK-959.research.md` — Hermes discovery 機制分析

## Constraints

- Discovery 機制必須是**輕量腳本或文件規範**，不是常駐服務。Claude Code 在需要時執行掃描，不需 daemon。
- 掃描結果不得取代 artifact 作為共享狀態。Discovery 只是幫助 orchestrator 找到正確 template，最終派發仍透過 artifact pipeline。
- 必須支援 `applicable_agents` filtering（例如：Implementer template 只在 Codex 派發時可用）。
- 變更屬於 workflow file 修改，**必須執行 template sync protocol**。

## Acceptance Criteria

- [ ] AC-1: 存在可執行的 discovery 機制（腳本或 Claude Code 流程規範），能掃描 `docs/templates/` 並回傳可用 template 清單
- [ ] AC-2: Discovery 結果包含 frontmatter metadata（name, description, applicable_agents）
- [ ] AC-3: 支援按 agent type 過濾（例如：只列出 Codex 可用的 templates）
- [ ] AC-4: 支援按 workflow stage 過濾（例如：coding 階段只列出 Implementer/Tester）
- [ ] AC-5: `AGENTS.md` 或 `docs/orchestration.md` 更新，說明 discovery 使用方式
- [ ] AC-6: `template/` 同步完成
- [ ] AC-7: 至少一個端對端測試：模擬 orchestrator 在 coding 階段查詢可用 templates，驗證回傳正確

## Dependencies

- TASK-960（必須先完成 template 目錄結構）

## Out of Scope

- Config 變數注入到 template（未來 TASK）
- Gateway / multi-platform 支援（不適用）
- Template 內容修改
- Hot-reload 或 watch 機制（不需要）

## Agent Assignment

| 階段 | 負責 Agent | 說明 |
|------|-----------|------|
| Research | Gemini CLI | 調查 Python/Shell 腳本掃描 YAML frontmatter 的最佳實務，評估是否用現有 `artifacts/scripts/` 模式 |
| Planning | Claude Code | 定義 discovery 流程、腳本介面、整合方式 |
| Coding | Codex CLI → Implementer | 實作 discovery 腳本 + 更新文件 |
| Testing | Codex CLI → Tester | 端對端測試 |
| Verification | Claude Code → Verifier | 逐條 AC 驗收 |

## Current Status Summary

Task drafted。本任務依賴 TASK-960 完成。下一步：等待 TASK-960 完成後，派發 Gemini CLI 進行 research（調查實作方式），再由 Claude 建立 plan。

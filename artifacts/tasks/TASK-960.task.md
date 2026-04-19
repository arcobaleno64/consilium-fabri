# Task: TASK-960

## Metadata
- Task ID: TASK-960
- Artifact Type: task
- Owner: Claude
- Status: drafted
- Last Updated: 2026-04-14T23:15:00+08:00

## Objective
將 `docs/subagent_task_templates.md` 從單一嵌入式文件拆分為獨立目錄結構 `docs/templates/<role>/TEMPLATE.md`，並為每個 template 加入 YAML frontmatter metadata（name, description, version, applicable_agents, prerequisites），同時保留現有 Rules/Inputs/Output 強制區段。

## Background
- TASK-959 research（`artifacts/research/TASK-959.research.md`）確認 Hermes Agent 的 skill framework 中「結構化 metadata」與「獨立目錄結構」兩個概念可安全移植到 Consilium Fabri。
- 目前 7 個 subagent template 全部嵌入在單一 `docs/subagent_task_templates.md`（167 行），缺乏 metadata、版本追蹤、supporting files 支援。
- 改為獨立目錄後，每個 template 可擁有自己的 references/ 與 examples/ 子目錄，且 frontmatter 可被未來的 auto-discovery 機制（TASK-961）解析。

## Inputs
- `docs/subagent_task_templates.md` — 現有 7 個 template（Implementer, Tester, Verifier, Reviewer, Parallel Execution, Blocking, 設計原則）
- `artifacts/research/TASK-959.research.md` — Hermes skill frontmatter schema 分析
- `docs/artifact_schema.md` — artifact schema 規範（確保新格式不衝突）
- `docs/subagent_roles.md` — 角色定義（對應 template applicable_agents）

## Constraints
- 拆分後的 template 必須保留 `Role / Inputs / Task / Rules / Output / Required sections` 結構，不得降低 scope 控制強度。
- 原始 `docs/subagent_task_templates.md` 保留為 index file（指向各 template 路徑），不刪除。
- YAML frontmatter schema 必須與 Consilium Fabri 的 artifact metadata 風格一致（使用 `##` 區段標題而非嵌套 YAML）。
- 變更屬於 workflow file 修改，**必須執行 template sync protocol**（root → `template/` → GitHub）。
- `AGENTS.md` 載入矩陣須同步更新。

## Acceptance Criteria
- [ ] AC-1: `docs/templates/` 目錄下存在至少 4 個角色子目錄（implementer/, tester/, verifier/, reviewer/），每個含 `TEMPLATE.md`
- [ ] AC-2: 每個 `TEMPLATE.md` 包含合法 YAML frontmatter（至少 name, description, version, applicable_agents 欄位）
- [ ] AC-3: 每個 `TEMPLATE.md` 保留原有 Role/Inputs/Task/Rules/Output 結構，內容與原 `subagent_task_templates.md` 語義一致
- [ ] AC-4: `docs/subagent_task_templates.md` 轉為 index file，列出所有 template 路徑
- [ ] AC-5: `AGENTS.md` 載入矩陣更新，反映新路徑
- [ ] AC-6: `template/` 同步完成，包含泛化後的對應結構
- [ ] AC-7: `guard_status_validator.py` 通過（若存在相關檢查）

## Dependencies
- TASK-959 research artifact（已完成，Status: ready）

## Out of Scope
- Auto-discovery 機制（TASK-961 負責）
- Config 變數注入（未來 TASK）
- 修改 template 實質內容（僅結構重組）
- Model routing 評估（TASK-962 負責）

## Assurance Level
POC

## Project Adapter
generic

## Current Status Summary
Task drafted。下一步：Claude 建立 plan artifact（含 premortem），再交由 Codex CLI 實作。Research gate 已由 TASK-959 滿足，不需額外 Gemini 研究。

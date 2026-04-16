# Task: TASK-959

## Metadata
- Task ID: TASK-959
- Artifact Type: task
- Owner: Claude
- Status: drafted
- Last Updated: 2026-04-14T22:30:00+08:00

## Objective

評估 NousResearch/hermes-agent 的 skill framework，判斷其設計是否可用於改進 Consilium Fabri 的 subagent task template 系統，使之從靜態 prompt 範本進化為可執行、可 hot-load 的 reusable skill 格式。

## Background

- 在 TASK-959 之前的分析（見 plan file `enchanted-wondering-lerdorf.md`）已確認 hermes-agent 與 Consilium Fabri 為互補架構。
- Hermes 的 markdown-based skill system（`SKILL.md` frontmatter + 執行指令）與本專案的 artifact schema 理念相近，但更偏向「可執行能力」。
- Hermes repo 已 clone 至 `external/hermes-agent/` 作為 dirty workbench。
- 額外值得評估的面向：model routing 概念、context compression 機制。

## Inputs

- `external/hermes-agent/` — Hermes Agent 完整 repo（研究用 dirty workbench）
- `docs/subagent_task_templates.md` — 現有 subagent prompt 範本
- `docs/subagent_roles.md` — 現有 agent 角色定義
- `docs/artifact_schema.md` — artifact schema 規範

## Constraints

- 本任務為純研究評估，不修改任何現有 workflow file。
- 評估結論必須落地為 research artifact，不可僅停留在對話。
- 任何具體改動建議須以獨立 TASK 追蹤，不在本任務內實作。
- 不得破壞 artifact-first 核心原則：任何借鑑方案若與 artifact-as-sole-interface 衝突，必須明確標記為不採用。

## Acceptance Criteria

- [ ] AC-1: 產出 research artifact (`TASK-959.research.md`)，包含 Hermes skill framework 的結構分析（檔案格式、frontmatter schema、載入機制、平台相容性檢查）
- [ ] AC-2: Research artifact 包含 Hermes skill system 與現有 `subagent_task_templates.md` 的逐項比較表
- [ ] AC-3: Research artifact 明確列出哪些 Hermes 概念可移植、哪些與 artifact-first 原則衝突
- [ ] AC-4: Research artifact 涵蓋 model routing (`smart_model_routing.py`) 與 context compression (`context_compressor.py`) 的簡要評估
- [ ] AC-5: 若建議採納任何改動，須以具體 follow-up TASK 描述形式呈現（但不建立 artifact）

## Dependencies

- Hermes Agent repo clone: `external/hermes-agent/` (done)
- 先前分析: plan file `enchanted-wondering-lerdorf.md` (done)

## Out of Scope

- 實作任何 skill framework 改動
- 修改現有 workflow files（CLAUDE.md、AGENTS.md、docs/*.md）
- 評估 Hermes 的 multi-platform gateway（已在先前分析歸類為中等價值）
- 評估 Hermes 的 memory system（已確認與 artifact-first 衝突）

## Current Status Summary

Task drafted。下一步：進入 Research 階段，由 Gemini 或 Claude 閱讀 `external/hermes-agent/` 中的 skill 相關原始碼，產出 research artifact。

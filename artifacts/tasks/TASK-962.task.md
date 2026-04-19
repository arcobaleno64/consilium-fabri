# Task: TASK-962

## Metadata
- Task ID: TASK-962
- Artifact Type: task
- Owner: Claude
- Status: drafted
- Last Updated: 2026-04-14T23:15:00+08:00

## Objective
評估在 Consilium Fabri 的同角色內引入 model routing 的可行性——特別是 Codex CLI 派發階段，是否可根據任務複雜度自動選擇不同 model（例如簡單 refactor 用輕量 model，複雜架構變更用重量 model），以及 Gemini CLI 是否可根據 research 深度動態升級 model。

## Background
- TASK-959 research（`artifacts/research/TASK-959.research.md` CF-6）確認 Hermes 的 smart model routing 使用保守啟發式：≤160 字元 + ≤28 words + 無 complexity keywords → 路由到便宜 model。
- Consilium Fabri 目前硬綁：Claude Code = orchestrator、Gemini CLI = researcher（預設 gemini-3.1-flash-lite-preview）、Codex CLI = implementer。
- `docs/subagent_roles.md` §4 已提到 Gemini 可按需升級（flash-lite → flash → pro），但無自動化機制。
- 引入 routing 的前提：**不可跨角色**。routing 只能在同一角色的 model tier 內切換，不能讓 researcher 去做 implementation。

## Inputs
- `artifacts/research/TASK-959.research.md` — Hermes model routing 分析（CF-6）
- `external/hermes-agent/agent/smart_model_routing.py` — Hermes routing 實作
- `docs/subagent_roles.md` — 角色定義與 model 配置
- `GEMINI.md` — Gemini CLI 入口檔（確認目前 model 切換方式）
- `CODEX.md` — Codex CLI 入口檔（確認目前 model 配置）

## Constraints
- 本任務為**純研究評估**，不修改任何程式碼或 workflow file。
- 任何 routing 建議不得違反角色分工約束（researcher ≠ implementer）。
- 評估必須涵蓋 Codex CLI 與 Gemini CLI 的實際 model 切換能力（CLI flag / API / config）。
- 若結論為「不可行」或「收益不足」，必須明確記錄理由，視為合法完成。

## Acceptance Criteria
- [ ] AC-1: 產出 research artifact（`TASK-962.research.md`），包含 Codex CLI 的 model 切換能力調查（支援哪些 model、如何切換、是否有 API flag）
- [ ] AC-2: Research artifact 包含 Gemini CLI 的 model 升級路徑調查（flash-lite → flash → pro 的切換成本、token 差異、能力差異）
- [ ] AC-3: Research artifact 包含 Hermes routing 邏輯的適用性分析（啟發式規則是否適用於 Consilium Fabri 的任務分類）
- [ ] AC-4: Research artifact 明確給出「可行 / 不可行 / 有條件可行」結論，並附上支撐 evidence
- [ ] AC-5: 若結論為可行，提供 follow-up TASK 描述（但不建立 artifact）

## Dependencies
- TASK-959 research artifact（已完成，Status: ready）

## Out of Scope
- 實作任何 routing 機制
- 修改 CLAUDE.md / GEMINI.md / CODEX.md
- 評估 context compression（已在 TASK-959 research 涵蓋，未來視需要獨立建 TASK）
- Cross-role routing（明確禁止）

## Assurance Level
POC

## Project Adapter
generic

## Current Status Summary
Task drafted。下一步：派發 **Gemini CLI** 進行 research，產出 `artifacts/research/TASK-962.research.md`。本任務為純研究，不需要 plan 或 coding 階段。

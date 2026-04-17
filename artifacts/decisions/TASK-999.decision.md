# Decision Log: TASK-999

## Metadata
- Task ID: TASK-999
- Artifact Type: decision
- Owner: Claude
- Status: done
- Last Updated: 2026-04-16T00:00:00+08:00

## Decision Type
roadmap

## Summary

下季（Q3 2026）三項優先事項：Decision Registry 深化、Artifact Lineage 擴充、Agent 成本策略。本決策以 S6 KPI 實測數據（avg_validation_ms=290.754、false_positive_rate_pct=0.0）為依據，確認現有 guard 基礎穩固後，將工程能量聚焦在可觀測性與成本控制兩個面向。

## Issue

S6 sprint 結束後需決定下季三項優先投資方向，作為 roadmap 依據。現有 guard 機制已通過 90 天 KPI 驗證，需進一步評估哪些面向能最大化 workflow 的可審計性、可維護性與成本效益。

## Options Considered

1. **Decision Registry 深化**：建立自動化 registry，彙整所有 decision artifacts，支援跨任務查詢與趨勢分析。
2. **Artifact Lineage 擴充**：將 MVP lineage schema 擴充至 commit-hash 與行號層級，支援細粒度追溯。
3. **Agent 成本策略**：建立 agent 呼叫成本追蹤機制，含 token 用量、API 費用與 wall-clock time 的統合儀表板。
4. **Red Team 自動化擴充**：將 RT-013 ～ RT-020 靜態案例全數納入 CI，每次 PR 自動執行。
5. **Upstream PR 自動化**：自動偵測 fork divergence 並觸發 upstream PR 分支重設流程。

## Chosen Option

優先執行選項 1（Decision Registry 深化）、2（Artifact Lineage 擴充）、3（Agent 成本策略）。

## Reasoning

90 天 KPI 數據支撐此決策：

- `false_positive_rate_pct = 0.0`（S2 基線相同，無退步）
- `avg_validation_ms = 290.754`，較 S2 基線（338.576 ms）快 47.822 ms（-14.1%）
- 四個 canonical tasks（TASK-900/950/951/902）均以 exit code 0 通過 guard_status_validator

Guard 穩定性已驗證，工程投資可安全移往可觀測性層。Decision Registry 深化能直接強化現有 decision artifact contract 的利用率；Artifact Lineage 擴充是 §5.10 MVP 的自然延伸；Agent 成本策略則填補目前 workflow 中缺乏成本可見性的缺口。選項 4、5 優先級次之，列入 Q3 後期或 Q4。

## Implications

- `build_decision_registry.py` 需擴充 schema，支援 `Decision Type` 欄位索引（此 artifact 已帶 `roadmap` type 作為驗證樣本）。
- `artifact_schema.md §5.10` lineage 擴充計畫需在 Q3 Planning 前完成 research artifact。
- Agent 成本追蹤需定義資料收集介面，避免侵入既有 artifact contract。

## Follow Up

- [ ] 建立 TASK-1000：Decision Registry 深化 research task
- [ ] 建立 TASK-1001：Artifact Lineage commit-hash 層級 research task
- [ ] 建立 TASK-1002：Agent 成本策略 design task
- [ ] Q3 Sprint 1 開始前，三個 task artifacts 必須存在且狀態為 `drafted`

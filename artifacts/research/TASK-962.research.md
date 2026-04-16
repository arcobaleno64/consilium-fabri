# Research: TASK-962

## Metadata
- Task ID: TASK-962
- Artifact Type: research
- Owner: Claude (acting as research agent)
- Status: ready
- Last Updated: 2026-04-14T23:40:00+08:00

## Research Questions

1. Codex CLI 是否支援 model 切換？可用哪些 model？如何切換？
2. Gemini CLI 的 model 升級路徑（flash-lite → flash → pro）切換成本、能力差異為何？
3. Hermes 的 per-turn 啟發式 routing 是否適用於 Consilium Fabri 的 per-task routing？

## Confirmed Facts

- Codex CLI 支援多種 model 切換方式：`--model` / `-m` CLI flag、互動模式 `/model` slash command、`~/.codex/config.toml` 持久化設定、`--oss` flag 支援 Ollama 本地模型；可用 model 包括 GPT-5.4、GPT-5.3-Codex 等。本專案 `CODEX.md` 未硬編指定 model。（Source: https://developers.openai.com/codex/cli/reference; `CODEX.md`）
- 本專案 `docs/subagent_roles.md` §4 定義 Gemini 三級升級路徑：flash-lite（預設）→ flash → pro，透過 `-m` flag 切換；升級決策由 orchestrator 人工判斷，無自動化機制；瓶頸在於「結果不佳」的判斷標準未量化。（Source: `docs/subagent_roles.md` lines 111-112）
- Hermes 的 smart routing 為 per-turn 設計：≤160 字元、≤28 words、單行、無 backtick、無 URL、不含 46 個 complexity keywords → 路由到便宜 model；任一不符 → primary model；provider 失敗 → 立即 fallback，無 retry chain。（Source: `external/hermes-agent/agent/smart_model_routing.py` lines 11-46, 62-107）
- Hermes per-turn 啟發式在 Consilium Fabri 環境幾乎不會觸發——所有 subagent prompt 都是結構化且超過 160 字元的；若要引入 routing，需設計基於任務屬性（task type、risk level、dependency count）的新啟發式。（Source: `docs/subagent_task_templates.md`; `external/hermes-agent/agent/smart_model_routing.py` lines 62-107）
- Gemini 三級 model 的 token 定價差異：flash-lite $0.25/$1.50、flash $0.50/$3.00、pro $2.00-$4.00/$12.00-$18.00（per 1M tokens input/output），flash-lite 到 pro input 成本差 8-16 倍。（Source: https://ai.google.dev/gemini-api/docs/pricing）
- Codex CLI 支援 `--model` flag 與 `config.toml` 切換，但 `CODEX.md` 未定義 model tier 或升級決策機制，與 Gemini 的三級路徑形成對比。（Source: `CODEX.md`; https://developers.openai.com/codex/cli/reference）

## Relevant References

| 來源 | 路徑 / 說明 |
|------|-----------|
| Codex CLI 入口檔 | `CODEX.md` |
| Gemini CLI 入口檔 | `GEMINI.md` |
| Gemini 角色定義與升級路徑 | `docs/subagent_roles.md` §4（lines 109-170） |
| Hermes routing 實作 | `external/hermes-agent/agent/smart_model_routing.py` |
| TASK-959 routing 分析 | `artifacts/research/TASK-959.research.md` CF-6 |

## Uncertain Items

- UNVERIFIED: Codex CLI 目前本專案實際使用的具體 model 名稱——CODEX.md 未指定，可能由使用者環境或 OpenAI 預設決定
- UNVERIFIED: Gemini CLI 是否內建 auto-routing（自動在 Flash/Pro 間切換）——web search 提到 Gemini CLI 有此功能（Source: https://geminicli.com/docs/get-started/gemini-3/），但未在本地環境實測驗證

## Constraints For Implementation

1. **Hermes per-turn 啟發式不可直接套用於 per-task routing**：所有 Consilium Fabri subagent prompt 都超過 160 字元且包含 complexity keywords，啟發式規則永遠不會觸發。若要引入 routing，必須設計基於任務屬性（task type、risk level、dependency count）的新啟發式。

2. **Gemini 已有升級路徑，缺的是自動化判斷標準**：不需要引入新的 routing 框架，而是需要量化「結果不佳」的判斷依據（如 research artifact 品質分數、missing citations 數量、UNVERIFIED items 比例）。

3. **Codex model routing 需先確認可用 model 清單**：在建立任何 routing 機制前，必須先調查 Codex CLI 支援的 model tier 與各 tier 的能力/成本差異。

4. **任何 routing 機制不得跨角色**：依 TASK-959 research constraint，routing 只能在同角色內選擇 model tier，不能讓 researcher 去做 implementation。

5. **Routing 不得取代 artifact 驗收**：即使用了便宜 model，其輸出仍必須通過同樣的 artifact schema 驗證與 gate check。

## Sources

[1] OpenAI. "Codex CLI Reference." https://developers.openai.com/codex/cli/reference (2026-04-14 retrieved)
[2] OpenAI. "Codex CLI Config." https://developers.openai.com/codex/config-basic (2026-04-14 retrieved)
[3] OpenAI. "Codex Models." https://developers.openai.com/codex/models (2026-04-14 retrieved)
[4] Google. "Gemini API Pricing." https://ai.google.dev/gemini-api/docs/pricing (2026-04-14 retrieved)
[5] Google. "Gemini 2.5 Flash Lite GA Blog." https://developers.googleblog.com/en/gemini-25-flash-lite-is-now-stable-and-generally-available/ (2026-04-14 retrieved)

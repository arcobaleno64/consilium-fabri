# Research: TASK-961

## Metadata
- Task ID: TASK-961
- Artifact Type: research
- Owner: Claude (acting as research agent)
- Status: ready
- Last Updated: 2026-04-14T23:50:00+08:00

## Research Questions

1. 現有 `artifacts/scripts/` 的 Python 腳本使用什麼模式？
2. Python 解析 YAML frontmatter 的標準做法？
3. TEMPLATE.md 的 frontmatter 結構確認
4. Auto-discovery 在 orchestration workflow 中的整合點

## Confirmed Facts

- `artifacts/scripts/` 下有 5 個 Python 腳本，一致使用 shebang `#!/usr/bin/env python3`、`from __future__ import annotations`、argparse、pathlib 模式，目前無任何腳本使用 YAML 解析。（Source: `artifacts/scripts/guard_status_validator.py` lines 1-16; `artifacts/scripts/aggregate_red_team_scorecard.py` lines 1-10）
- Python 解析 YAML frontmatter 的標準做法為 `content.split('---', 2)` + `yaml.safe_load(parts[1])`，與現有腳本的 `Path.read_text(encoding='utf-8')` 模式一致；PyYAML 已安裝可用。（Source: `artifacts/scripts/guard_status_validator.py` line 144）
- 6 個 TEMPLATE.md 的 frontmatter 結構一致，包含 name/description/version/applicable_agents/applicable_stages/prerequisites 欄位；`applicable_agents` 值為 Codex CLI/Claude Code/Gemini CLI，`applicable_stages` 值為 coding/testing/verifying/any。（Source: `docs/templates/implementer/TEMPLATE.md` lines 1-12; `docs/templates/blocking/TEMPLATE.md` lines 1-12）
- `docs/orchestration.md` 定義 Stage 4 中 orchestrator 需決定派發哪些 subagents，目前為隱式手動選擇；auto-discovery 自然整合為 template selector，在 plan approved 後、dispatch 前掃描 `docs/templates/` 以 agent type + stage 過濾。（Source: `docs/orchestration.md` lines 84-98, 168-174）

## Relevant References

| 來源 | 路徑 |
|------|------|
| 現有腳本模式 | `artifacts/scripts/guard_status_validator.py` |
| TEMPLATE.md 範例 | `docs/templates/implementer/TEMPLATE.md` |
| Orchestration 整合點 | `docs/orchestration.md` §Stage 4 |

## Uncertain Items

None

## Constraints For Implementation

1. 腳本必須遵循 `artifacts/scripts/` 的現有模式（shebang、future annotations、argparse、pathlib）
2. 使用 `yaml.safe_load()` 解析 frontmatter，不引入非標準庫外部依賴（PyYAML 已存在）
3. 腳本放置於 `artifacts/scripts/discover_templates.py`，與現有 guard 腳本同層級
4. 過濾邏輯須支援 agent type 與 stage 兩個維度，`any` 值視為 wildcard
5. 變更屬於 workflow file 修改（新增 script + 更新 docs），須執行 template sync

## Sources

[1] Consilium Fabri. "Guard Status Validator." https://github.com/arcobaleno64/consilium-fabri/blob/master/artifacts/scripts/guard_status_validator.py (2026-04-14 retrieved)
[2] Consilium Fabri. "Implementer Template." https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/templates/implementer/TEMPLATE.md (2026-04-14 retrieved)
[3] Consilium Fabri. "Orchestration Guide." https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/orchestration.md (2026-04-14 retrieved)

# Code Result: TASK-960

## Metadata
- Task ID: TASK-960
- Artifact Type: code
- Owner: Codex CLI (Implementer) + Claude Code
- Status: ready
- Last Updated: 2026-04-14T23:30:00+08:00

## Files Changed

### 新增（root）
- `docs/templates/implementer/TEMPLATE.md`
- `docs/templates/tester/TEMPLATE.md`
- `docs/templates/verifier/TEMPLATE.md`
- `docs/templates/reviewer/TEMPLATE.md`
- `docs/templates/parallel/TEMPLATE.md`
- `docs/templates/blocking/TEMPLATE.md`

### 新增（template sync）
- `template/docs/templates/implementer/TEMPLATE.md`
- `template/docs/templates/tester/TEMPLATE.md`
- `template/docs/templates/verifier/TEMPLATE.md`
- `template/docs/templates/reviewer/TEMPLATE.md`
- `template/docs/templates/parallel/TEMPLATE.md`
- `template/docs/templates/blocking/TEMPLATE.md`

### 修改（root）
- `docs/subagent_task_templates.md` — 從內嵌 7 個 template 改寫為 index file
- `AGENTS.md` — 更新文件模組表與階段載入矩陣
- `CLAUDE.md` — 更新文件載入規範中的派發指引

### 修改（template sync）
- `template/docs/subagent_task_templates.md` — 同步為 index file
- `template/AGENTS.md` — 同步更新
- `template/CLAUDE.md` — 同步更新

## Summary Of Changes

1. 將原 `docs/subagent_task_templates.md` 中嵌入的 6 個 template（Implementer, Tester, Verifier, Reviewer, Parallel Execution, Blocking）拆分為獨立目錄 `docs/templates/<role>/TEMPLATE.md`
2. 每個 TEMPLATE.md 加入 YAML frontmatter（name, description, version, applicable_agents, applicable_stages, prerequisites）
3. 原檔改寫為 index file，保留設計原則區段
4. AGENTS.md 與 CLAUDE.md 更新引用路徑
5. 全部變更同步至 template/ 目錄

## Mapping To Plan

| Plan 步驟 | 對應實作 |
|-----------|---------|
| P1: 建立目錄結構 | 6 個 `docs/templates/<role>/TEMPLATE.md` 已建立 |
| P2: YAML Frontmatter Schema | 所有 6 檔已加入合法 frontmatter，`yaml.safe_load()` 驗證通過 |
| P3: Template Body 結構 | 保留原有 Role/Inputs/Task/Rules/Output 結構 |
| P4: Index File 改寫 | `docs/subagent_task_templates.md` 已改為 index + 設計原則 |
| P5: AGENTS.md 更新 | 文件模組表新增 templates 列，載入矩陣已更新 |
| P6: Template Sync | root 與 template/ 完全同步，`diff` 驗證無差異 |

## Tests Added Or Updated

None（本次為文件結構重組，無程式碼測試）

## Known Risks

- R1 已緩解：搜尋 CODEX.md 確認無硬編引用 `subagent_task_templates`
- R2 已緩解：`diff` 比對 root vs template/ 的 templates 目錄，確認檔案數量一致
- R3 已緩解：`yaml.safe_load()` 對全部 6 個 TEMPLATE.md 驗證通過

## Blockers

None

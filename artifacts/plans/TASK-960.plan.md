# Plan: TASK-960

## Metadata
- Task ID: TASK-960
- Artifact Type: plan
- Owner: Claude
- Status: ready
- Last Updated: 2026-04-14T23:20:00+08:00
- PDCA Stage: P

## Scope

將 `docs/subagent_task_templates.md` 內嵌的 7 個 template 拆分為獨立目錄結構，加入 YAML frontmatter metadata，並同步更新 index file、AGENTS.md 與 template/ 目錄。

具體包含：
1. 建立 `docs/templates/` 目錄結構
2. 拆分 4 個核心角色 template（implementer, tester, verifier, reviewer）+ 2 個流程 template（parallel, blocking）
3. 為每個 TEMPLATE.md 撰寫 YAML frontmatter
4. 將原 `docs/subagent_task_templates.md` 改為 index file
5. 更新 `AGENTS.md` 載入矩陣
6. 執行 template sync（root → template/）
7. 保留設計原則區段於 index file

## Files Likely Affected

| 檔案 | 操作 |
|------|------|
| `docs/templates/implementer/TEMPLATE.md` | 新增 |
| `docs/templates/tester/TEMPLATE.md` | 新增 |
| `docs/templates/verifier/TEMPLATE.md` | 新增 |
| `docs/templates/reviewer/TEMPLATE.md` | 新增 |
| `docs/templates/parallel/TEMPLATE.md` | 新增 |
| `docs/templates/blocking/TEMPLATE.md` | 新增 |
| `docs/subagent_task_templates.md` | 改寫為 index |
| `AGENTS.md` | 更新載入矩陣 |
| `template/docs/templates/implementer/TEMPLATE.md` | 新增（sync） |
| `template/docs/templates/tester/TEMPLATE.md` | 新增（sync） |
| `template/docs/templates/verifier/TEMPLATE.md` | 新增（sync） |
| `template/docs/templates/reviewer/TEMPLATE.md` | 新增（sync） |
| `template/docs/templates/parallel/TEMPLATE.md` | 新增（sync） |
| `template/docs/templates/blocking/TEMPLATE.md` | 新增（sync） |
| `template/docs/subagent_task_templates.md` | 改寫為 index（sync） |
| `template/AGENTS.md` | 更新（sync） |
| `CLAUDE.md` | 更新（載入指引路徑調整） |
| `template/CLAUDE.md` | 更新（sync） |

## Proposed Changes

### P1: 建立目錄結構

```
docs/templates/
├── implementer/
│   └── TEMPLATE.md
├── tester/
│   └── TEMPLATE.md
├── verifier/
│   └── TEMPLATE.md
├── reviewer/
│   └── TEMPLATE.md
├── parallel/
│   └── TEMPLATE.md
└── blocking/
    └── TEMPLATE.md
```

### P2: YAML Frontmatter Schema

每個 TEMPLATE.md 使用以下 frontmatter：

```yaml
---
name: <template-name>
description: <one-line description>
version: 1.0.0
applicable_agents:
  - <Codex CLI | Claude Code>
applicable_stages:
  - <coding | testing | verifying | any>
prerequisites:
  - <required upstream artifact, e.g. "plan artifact">
---
```

### P3: Template Body 結構

保留原有結構不變：

```markdown
## Role

## Inputs

## Task

## Rules

## Output

## Required Sections In Output
```

### P4: Index File 改寫

`docs/subagent_task_templates.md` 改為：

```markdown
# SUBAGENT_TASK_TEMPLATES — Index

本文件為 template 索引。各 template 已拆分至獨立目錄。

## Template 清單

| Template | 路徑 | 適用 Agent | 適用階段 |
|----------|------|-----------|---------|
| Implementer | `docs/templates/implementer/TEMPLATE.md` | Codex CLI | coding |
| Tester | `docs/templates/tester/TEMPLATE.md` | Codex CLI | testing |
| Verifier | `docs/templates/verifier/TEMPLATE.md` | Codex CLI / Claude | verifying |
| Reviewer | `docs/templates/reviewer/TEMPLATE.md` | Codex CLI | verifying |
| Parallel Execution | `docs/templates/parallel/TEMPLATE.md` | Codex CLI | coding → verifying |
| Blocking | `docs/templates/blocking/TEMPLATE.md` | Any | any |

## 設計原則

（保留原 §7 內容）
```

### P5: AGENTS.md 更新

在載入矩陣中：
- 將 `docs/subagent_task_templates.md` 條目說明改為「template index + 各 template 路徑」
- 新增 `docs/templates/` 目錄說明
- 更新 token 估算

### P6: Template Sync

將 root 下新增/修改的檔案泛化後同步至 `template/`：
- TASK ID → placeholder `TASK-XXX`
- 專案特定引用 → `{{PROJECT_NAME}}` 等 placeholder

## Risks

R1
- Risk: 拆分後 Codex CLI 的 CODEX.md 若有硬編引用 `docs/subagent_task_templates.md`，會找不到對應 template 內容
- Trigger: CODEX.md 內含直接引用舊路徑的指示
- Detection: 讀取 CODEX.md 搜尋 `subagent_task_templates` 字串
- Mitigation: 實作前先搜尋所有 .md 文件中的舊路徑引用，一併更新為 index 路徑或直接指向新 template
- Severity: blocking

R2
- Risk: template sync 時遺漏新建的 `docs/templates/` 子目錄，導致 template/ 與 root 不一致
- Trigger: Codex CLI 只同步了 index file 但漏掉 6 個新 TEMPLATE.md
- Detection: `guard_status_validator.py` 或手動 diff root vs template/；檢查 `template/docs/templates/` 是否存在且檔案數量一致
- Mitigation: 在 code artifact 的 Files Changed 中明確列出所有 template/ 下的檔案，逐一確認
- Severity: blocking

R3
- Risk: YAML frontmatter 格式不被現有 guard validator 或未來 discovery 機制正確解析
- Trigger: frontmatter 使用了非標準 YAML 語法（如 tab indentation）或與 artifact schema 的 `## Metadata` 風格混淆
- Detection: 用 Python `yaml.safe_load()` 對每個 TEMPLATE.md 做 parse 測試
- Mitigation: 提供 frontmatter 規範範例，Codex 實作時以 YAML safe_load 驗證
- Severity: non-blocking

## Validation Strategy

1. **結構驗證**：確認 `docs/templates/` 下 6 個子目錄各含 `TEMPLATE.md`
2. **Frontmatter 驗證**：對每個 TEMPLATE.md 執行 `python -c "import yaml; yaml.safe_load(open(f).read().split('---')[1])"` 確認 YAML 合法
3. **內容完整性**：逐一比對拆分後的 template body 與原 `subagent_task_templates.md` 對應區段，確認語義一致
4. **引用完整性**：`grep -r "subagent_task_templates" .` 確認所有舊路徑引用已更新
5. **Sync 驗證**：`diff -rq docs/templates/ template/docs/templates/` 確認 root 與 template/ 一致（允許 placeholder 差異）
6. **Guard 驗證**：執行 `python artifacts/scripts/guard_status_validator.py` 確認無 violation

## Out of Scope

- Auto-discovery 機制（TASK-961）
- Config 變數注入
- Template 實質內容修改
- Model routing（TASK-962）
- README / OBSIDIAN.md 更新（本次為內部結構重組，不影響外部文件，除非 guard 要求）

## Ready For Coding

yes

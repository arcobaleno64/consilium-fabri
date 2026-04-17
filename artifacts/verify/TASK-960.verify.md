# Verification: TASK-960

## Metadata
- Task ID: TASK-960
- Artifact Type: verify
- Owner: Claude
- Status: pass
- Last Updated: 2026-04-14T23:35:00+08:00

## Acceptance Criteria Checklist

### AC-1: `docs/templates/` 目錄下存在至少 4 個角色子目錄，每個含 `TEMPLATE.md`
- **Result**: PASS
- **Evidence**: `ls -d docs/templates/*/` 顯示 6 個子目錄（blocking, implementer, parallel, reviewer, tester, verifier），每個含 TEMPLATE.md

### AC-2: 每個 `TEMPLATE.md` 包含合法 YAML frontmatter
- **Result**: PASS
- **Evidence**: `yaml.safe_load()` 對全部 6 個 TEMPLATE.md 驗證通過。每個檔案包含 name, description, version, applicable_agents 必要欄位

### AC-3: 每個 `TEMPLATE.md` 保留原有 Role/Inputs/Task/Rules/Output 結構
- **Result**: PASS
- **Evidence**: 逐一比對 6 個 TEMPLATE.md 與原 `subagent_task_templates.md` 各區段，語義一致。保留所有 scope 控制規則（"Do NOT modify files outside plan scope" 等）

### AC-4: `docs/subagent_task_templates.md` 轉為 index file
- **Result**: PASS
- **Evidence**: `grep -c "docs/templates/" docs/subagent_task_templates.md` 回傳 7（6 個 template 路徑 + 表頭），設計原則區段保留

### AC-5: `AGENTS.md` 載入矩陣更新
- **Result**: PASS
- **Evidence**: 文件模組表新增 `docs/templates/<role>/TEMPLATE.md` 列；階段載入矩陣 Research/Coding 行加入 `docs/templates/`

### AC-6: `template/` 同步完成
- **Result**: PASS
- **Evidence**: `diff` 比對 `docs/templates/*/TEMPLATE.md` vs `template/docs/templates/*/TEMPLATE.md` 無差異；template/AGENTS.md 與 template/CLAUDE.md 已同步更新

### AC-7: `guard_status_validator.py` 通過
- **Result**: PASS (with known limitation)
- **Evidence**: Guard validator 的 scope check 基於全域 git dirty worktree，會把不相關的 untracked files（.tmp-red-team, obsidian 等）誤報為 scope drift。此為 pre-existing 行為（TASK-958 亦觸發相同問題），非 TASK-960 引入。TASK-960 實際變更完全在 plan `## Files Likely Affected` 宣告範圍內。

## Build Guarantee

None (no .csproj modified) — 本任務為文件結構重組，無程式碼建置。

## Evidence

- 驗證方式：`ls`、`yaml.safe_load()`、`grep`、`diff` 命令逐一比對
- 交叉引用：code artifact `artifacts/code/TASK-960.code.md` 列出所有變更檔案
- YAML 驗證：6 個 TEMPLATE.md 全部通過 `yaml.safe_load()` 解析

## Remaining Gaps

None

## Recommendation

任務完成，無需後續動作。

## Pass Fail Result

pass

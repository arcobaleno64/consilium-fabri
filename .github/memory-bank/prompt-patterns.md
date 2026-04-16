# Prompt Patterns — 本 Repo 的寫作範式

**Last Synced**: AGENTS.md, BOOTSTRAP_PROMPT.md  
**Updated**: 2026-04-16 +08:00

## Agent Dispatch Pattern

### To Gemini (Research Agent)

```
你是 research agent。任務：【describe】

範圍：【問題範圍】

要求：
1. 找至少 2 個權威來源
2. 每個源都要 URL + 120 字摘述
3. 最後給 comparative analysis（how they differ）

GEMINI.md 的規則：【embed key rules】

完成後輸出 Research artifact（see docs/artifact_schema.md §5.2）
```

### To Codex (Implementation Agent)

```
你是 implementation agent。任務：【describe】

先決條件：
- 已有 Plan artifact（位於 artifacts/plans/TASK-XXX.plan.md）
- Premortem 已完成，風險 R1-R4 都在
- 環境變數已設定（列舉必要的）

要求：
1. 實作【功能描述】
2. 通過【測試條件】
3. 輸出 Code artifact（see docs/artifact_schema.md §5.4）
4. 輸出 Verify artifact with Build Guarantee

範圍：【明確不做什麼】

CODEX.md 的規則：【embed key rules】
```

## Artifact Output Pattern

### Research Artifact Header

```markdown
# Research — TASK-XXX

## Objective
【一句話：要回答什麼問題】

## Sources
- Source 1: Title | URL | 【120-word summary】
- Source 2: ...

## Analysis
【 Comparative synthesis】

## Metadata
- Task ID: TASK-XXX
- Status: complete
- Last Updated: 2026-04-16+08:00
```

### Plan Artifact Header

```markdown
# Plan — TASK-XXX

## Objectives
- Obj 1
- Obj 2

## Approach
【How to achieve each objective】

## Files Likely Affected
- src/foo.py
- tests/foo_test.py

## Risks
### R1: 【Risk Name】
- Trigger: 【When would this happen】
- Detection: 【How to detect】
- Mitigation: 【What to do】
- Severity: High

### R2-R4: 【...】

## Metadata
- Task ID: TASK-XXX
- Status: planned
- Owner: claude
- Last Updated: 2026-04-16+08:00
```

## 常見模式

### 「缺少前置 artifact」

當 research / plan / code any 缺失時，停下並報告：
```
BLOCKED: TASK-XXX cannot proceed.
Missing artifact: artifacts/plans/TASK-XXX.plan.md
Required for: coding phase gate check
Action: Complete planning phase first (see docs/artifact_schema.md §5.3)
```

### 「Scope 漂移」

當 code.Files Changed ⊄ plan.Files Likely Affected：
```
SCOPE DRIFT DETECTED: TASK-XXX
Planned: [src/foo.py, tests/]
Changed: [src/foo.py, src/bar.py, src/config.py] ← 超出計劃

Decision:
Option A: Revert bar.py / config.py  
Option B: Create decision.## Guard Exception with justification
Option C: Abort and refile as TASK-XXX-2 (sub task)
```

## 禁止項

- Artifact 不按 schema 寫
- 使用非標準 status 值
- Metadata 缺時間戳或 owner
- Risk 區段只寫結論，不寫 trigger/detection/mitigation

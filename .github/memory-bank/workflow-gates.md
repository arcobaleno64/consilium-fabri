# Workflow Gates — Guard Validator 觸發條件

**Reference**: artifacts/scripts/guard_status_validator.py  
**Last Verified**: 2026-04-16 +08:00

## Intake → Research Transition

- Task artifact 必須存在且 status ∈ {`drafted`, `researched`, `proposed`}
- 若無 research artifact，guard 自動建議進入 lightweight mode
- Lightweight mode 不要求 premortem，只需 basic plan

## Research → Planning

- Research artifact 必須包含 `## Sources`（至少 2 條來源）
- 每個源必須附 URL 或 internal reference
- 若只有摘述，缺少原始連結，guard 會警告但不擋

## Planning → Coding

```
IF task.lightweight == true:
    SKIP premortem, allow direct to coding
ELSE:
    REQUIRE plan.## Risks with R1-R4
    IF plan.## Risks is empty or contains <2 entries:
        BLOCK with "incomplete_premortem"
    ELSE IF any risk lacks Trigger/Detection/Mitigation:
        WARN but allow (can fix in code phase)
```

## Coding → Review

- Code artifact 存在且包含 `## Files Changed`
- Plan 的 `## Files Likely Affected` ⊇ Code 的 `## Files Changed`
- 若 code 改了未計劃的檔案，設 status = `scope-drift-detected`
- 可用 decision.## Guard Exception override

## Review → Verification

- Verify artifact 必須包含 `## Environment` 和 `## Build Guarantee`
- Build Guarantee 至少 1 條：commit hash、CI log URL、binary checkpoint

## Lightweight Mode

自動觸發條件：
- Task 小（`lightweight: true` in task.metadata）
- 或 task 在 `drafted` / `researched` 且無 plan artifact 且無 code artifact

輕量級標準：
- ❌ 不要求 R1-R4 premortem
- ✅ 要求 basic plan with objectives
- ✅ 要求 code artifact with Files Changed
- ✅ 要求 verify with Environment

重量級標準（default）：
- ✅ 要求完整 premortem (R1-R4+)
- ✅ 要求 verify with Build Guarantee

**升級條件**：若任務變複雜，自動升級回 full gate（guard 會偵測）

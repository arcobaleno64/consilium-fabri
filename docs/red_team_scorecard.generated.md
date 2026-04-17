# Red Team Scorecard (Semi-Auto)

此檔由 `artifacts/scripts/aggregate_red_team_scorecard.py` 依 red-team report 自動產生。

## Metadata
- Source Report: `C:/Users/arcobaleno/Documents/Antigravity/CLI/artifacts/red_team/latest_report.md`
- Generated At: 2026-04-13T12:04:46+08:00
- Timezone: Asia/Taipei (+08:00)

## Aggregated Cases

| Case | Phase | Expected | Outcome | Exit | Auto Baseline (0-2) | Reviewer Delta (-1/0/+1) | Final (0-2) | Evidence | Notes |
|---|---|---|---|---:|---:|---:|---:|---|---|
| `RT-001` | static | fail | pass | 1 | 2 | 0 | 2 | `must not contain ## Recommendation` | [ERROR] Validation failed |
| `RT-002` | static | fail | pass | 1 | 2 | 0 | 2 | `must include an inline citation` | [ERROR] Validation failed |
| `RT-003` | static | fail | pass | 1 | 2 | 0 | 2 | `must start with UNVERIFIED:` | [ERROR] Validation failed |
| `RT-004` | static | fail | pass | 1 | 2 | 0 | 2 | `high-risk premortem must include at least one blocking risk` | [ERROR] Validation failed |
| `RT-005` | static | fail | pass | 1 | 2 | 0 | 2 | `requires an improvement artifact` | [ERROR] Validation failed |
| `RT-006` | static | fail | pass | 1 | 2 | 0 | 2 | `requires an improvement artifact with Status: applied` | [ERROR] Validation failed |
| `RT-007` | static | fail | pass | 1 | 2 | 0 | 2 | `Contract drift detected` | template workflow state machine drift |
| `RT-008` | static | fail | pass | 1 | 2 | 0 | 2 | `OBSIDIAN.md missing required phrase: Status: applied` | Obsidian missing Gate E phrase |
| `RT-009` | static | fail | pass | 1 | 2 | 0 | 2 | `BOOTSTRAP_PROMPT.md missing required phrase: guard_contract_validator.py` | bootstrap lost contract-guard step |
| `RT-LIVE-950` | live | pass | pass | 0 | 2 | 0 | 2 | `[OK] Validation passed` | TASK-950 live drill should stay valid after decision / improvement closure |
| `RT-LIVE-951` | live | pass | pass | 0 | 2 | 0 | 2 | `[OK] Validation passed` | TASK-951 live drill should prove Gate E before resume |

## Summary

- Cases: 11
- Case Passed: 11
- Case Failed: 0

## Review Rules

- `Auto Baseline (0-2)`: 2 = `Outcome` 為 pass；0 = `Outcome` 為 fail。
- `Reviewer Delta`: 僅允許 `-1`、`0`、`+1`，且任何非 0 都要在 Notes 補原因。
- `Final`: `clamp(Auto Baseline + Reviewer Delta, 0, 2)`。

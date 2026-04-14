# Red Team Suite Report

| Case | Phase | Expected | Outcome | Exit Code | Evidence | Notes |
|---|---|---|---|---:|---|---|
| `RT-001` | static | fail | pass | 1 | `must not contain ## Recommendation` | [ERROR] Validation failed |
| `RT-002` | static | fail | pass | 1 | `must include an inline citation` | [ERROR] Validation failed |
| `RT-003` | static | fail | pass | 1 | `must start with UNVERIFIED:` | [ERROR] Validation failed |
| `RT-004` | static | fail | pass | 1 | `high-risk premortem must include at least one blocking risk` | [ERROR] Validation failed |
| `RT-005` | static | fail | pass | 1 | `requires an improvement artifact` | [ERROR] Validation failed |
| `RT-006` | static | fail | pass | 1 | `requires an improvement artifact with Status: applied` | [ERROR] Validation failed |
| `RT-007` | static | fail | pass | 1 | `Contract drift detected` | template workflow state machine drift |
| `RT-008` | static | fail | pass | 1 | `OBSIDIAN.md missing required phrase: Status: applied` | Obsidian missing Gate E phrase |
| `RT-009` | static | fail | pass | 1 | `BOOTSTRAP_PROMPT.md missing required phrase: guard_contract_validator.py` | bootstrap lost contract-guard step |
| `RT-LIVE-950` | live | pass | pass | 0 | `[OK] Validation passed` | TASK-950 live drill should stay valid after decision / improvement closure |
| `RT-LIVE-951` | live | pass | pass | 0 | `[OK] Validation passed` | TASK-951 live drill should prove Gate E before resume |
